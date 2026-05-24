"""Offline batch analyzer — Phase 2/3 with EMA baselines, smoothing, logprobs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from api_monitor.analyzer.baseline_builder import build_baselines, _model_key
from api_monitor.analyzer.baseline_updater import update_baseline_from_record
from api_monitor.analyzer.drift import (
    metadata_changed,
    timing_drift_pvalue,
)
from api_monitor.analyzer.families import (
    FAMILY_REFERENCE_TEXTS,
    infer_expected_family,
)
from api_monitor.analyzer.fusion import fusion_risk_level
from api_monitor.analyzer.lexicon import collect_lexicon_evidence
from api_monitor.analyzer.logprobs import logprobs_drift_pvalue
from api_monitor.analyzer.smoothing import AlertSmoother
from api_monitor.models import AnalysisReport, AnalysisRow, BaselineProfile, FamilyScore, ResponseRecord
from api_monitor.storage.baseline import BaselineStore

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class OfflineAnalyzer:
    """Encode responses, fuse signals, smooth alerts, auto-update baselines."""

    def __init__(
        self,
        *,
        min_text_length: int = 32,
        drift_threshold: float = 0.15,
        baseline_min_samples: int = 20,
        timing_pvalue_threshold: float = 0.05,
        logprobs_pvalue_threshold: float = 0.01,
        baseline_ema_alpha: float = 0.08,
        baseline_auto_update: bool = True,
        alert_smoothing_window: int = 3,
        db_path: str | None = None,
    ):
        self.min_text_length = min_text_length
        self.drift_threshold = drift_threshold
        self.baseline_min_samples = baseline_min_samples
        self.timing_pvalue_threshold = timing_pvalue_threshold
        self.logprobs_pvalue_threshold = logprobs_pvalue_threshold
        self.baseline_ema_alpha = baseline_ema_alpha
        self.baseline_auto_update = baseline_auto_update
        self.alert_smoothing_window = alert_smoothing_window
        self.db_path = db_path
        self._model: SentenceTransformer | None = None
        self._centroids: dict[str, np.ndarray] | None = None

    def _load_model(self) -> SentenceTransformer:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "分析功能需要安装可选依赖: pip install 'api-monitor[analyze]'"
                ) from exc
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    def _ensure_centroids(self) -> dict[str, np.ndarray]:
        if self._centroids is not None:
            return self._centroids
        model = self._load_model()
        centroids: dict[str, np.ndarray] = {}
        for family, texts in FAMILY_REFERENCE_TEXTS.items():
            emb = model.encode(texts, normalize_embeddings=True)
            centroids[family] = np.mean(emb, axis=0)
        self._centroids = centroids
        return centroids

    def classify_text(self, text: str) -> FamilyScore:
        model = self._load_model()
        centroids = self._ensure_centroids()
        emb = model.encode([text], normalize_embeddings=True)[0]
        scores: dict[str, float] = {}
        for family, centroid in centroids.items():
            scores[family] = float(np.dot(emb, centroid))
        predicted = max(scores, key=scores.get)
        return FamilyScore(
            family=predicted,
            confidence=scores[predicted],
            all_scores=scores,
        )

    def _baseline_store(self) -> BaselineStore | None:
        return BaselineStore(self.db_path) if self.db_path else None

    def _load_or_build_baselines(
        self, records: list[ResponseRecord], drift_scores: dict[int, float]
    ) -> dict[str, BaselineProfile]:
        store = self._baseline_store()
        built = build_baselines(
            records,
            min_samples=self.baseline_min_samples,
            default_threshold=self.drift_threshold,
            drift_scores=drift_scores,
        )
        if store:
            stored = store.list_all()
            merged = dict(stored)
            merged.update(built)
            for key, profile in built.items():
                store.upsert(profile)
            return merged
        return built

    def refresh_baselines(self, records: list[ResponseRecord]) -> dict[str, BaselineProfile]:
        """Rebuild baselines from all records (CLI baseline-refresh)."""
        eligible = [
            r
            for r in records
            if len((r.response_text or "").strip()) >= self.min_text_length
        ]
        drift_scores: dict[int, float] = {}
        for record in eligible:
            score = self.classify_text(record.response_text)
            expected = infer_expected_family(record.model_requested)
            drift = 0.0
            if expected and expected in score.all_scores:
                drift = abs(score.confidence - score.all_scores.get(expected, 0.0))
            drift_scores[record.id] = drift
        baselines = self._load_or_build_baselines(records, drift_scores)
        return baselines

    def analyze_records(self, records: list[ResponseRecord]) -> AnalysisReport:
        eligible = [
            r
            for r in records
            if len((r.response_text or "").strip()) >= self.min_text_length
        ]

        drift_scores: dict[int, float] = {}
        for record in eligible:
            score = self.classify_text(record.response_text)
            expected = infer_expected_family(record.model_requested)
            drift = 0.0
            if expected and expected in score.all_scores:
                drift = abs(score.confidence - score.all_scores.get(expected, 0.0))
            drift_scores[record.id] = drift

        baselines = self._load_or_build_baselines(records, drift_scores)
        smoother = AlertSmoother(window=self.alert_smoothing_window)
        store = self._baseline_store()

        alerts: list[AnalysisRow] = []
        summary: dict[str, int] = {}
        suppressed = 0
        baselines_updated = 0

        sorted_eligible = sorted(eligible, key=lambda r: (r.timestamp, r.id))

        for record in sorted_eligible:
            score = self.classify_text(record.response_text)
            expected = infer_expected_family(record.model_requested)
            summary[score.family] = summary.get(score.family, 0) + 1

            drift = drift_scores.get(record.id, 0.0)
            model_key = _model_key(record)
            baseline = baselines.get(model_key)
            dyn_threshold = (
                baseline.dynamic_threshold if baseline else self.drift_threshold
            )

            family_margin = 0.0
            if expected and expected in score.all_scores:
                family_margin = score.confidence - score.all_scores[expected]

            mismatch = (
                expected is not None
                and expected != "unknown"
                and score.family != expected
                and family_margin > dyn_threshold
            )

            meta_evidence = metadata_changed(record, baseline) if baseline else []
            metadata_anomaly = bool(meta_evidence)

            timing_p: float | None = None
            if baseline:
                timing_p = timing_drift_pvalue(record.timing, baseline)
                if timing_p is not None and timing_p < self.timing_pvalue_threshold:
                    meta_evidence.append(
                        f"时序模式偏移 (ITT/TTFT KS检验 p={timing_p:.4f})"
                    )

            logprobs_p: float | None = None
            has_logprobs_drift = False
            if baseline:
                logprobs_p = logprobs_drift_pvalue(record.logprobs_stats, baseline)
                if (
                    logprobs_p is not None
                    and logprobs_p < self.logprobs_pvalue_threshold
                ):
                    has_logprobs_drift = True
                    meta_evidence.append(
                        f"Logprobs 分布偏移 (p={logprobs_p:.4f}, 阈值 {self.logprobs_pvalue_threshold})"
                    )

            if not meta_evidence:
                fp = record.metadata.get("system_fingerprint")
                if (
                    fp is None
                    and record.model_requested
                    and "gpt" in record.model_requested.lower()
                ):
                    meta_evidence.append("system_fingerprint 字段缺失")

            evidence = collect_lexicon_evidence(
                record.response_text,
                expected=expected,
                predicted=score.family,
            ) + meta_evidence

            raw_risk, fusion_score = fusion_risk_level(
                family_mismatch=mismatch,
                family_margin=family_margin,
                text_drift=drift,
                dynamic_threshold=dyn_threshold,
                metadata_anomaly=metadata_anomaly,
                timing_pvalue=timing_p,
                timing_pvalue_threshold=self.timing_pvalue_threshold,
                has_logprobs_drift=has_logprobs_drift,
            )

            risk = smoother.smooth(model_key, raw_risk)
            if raw_risk in {"high", "medium"} and risk == "low":
                suppressed += 1

            if self.baseline_auto_update and raw_risk == "low" and baseline:
                baselines[model_key] = update_baseline_from_record(
                    baseline,
                    record,
                    drift_score=drift,
                    alpha=self.baseline_ema_alpha,
                )
                if store:
                    store.upsert(baselines[model_key])
                baselines_updated += 1

            if risk in {"high", "medium"}:
                alerts.append(
                    AnalysisRow(
                        record_id=record.id,
                        timestamp=record.timestamp,
                        model_requested=record.model_requested,
                        expected_family=expected,
                        predicted_family=score.family,
                        confidence=round(score.confidence, 4),
                        drift_score=round(drift, 4),
                        risk_level=risk,
                        raw_risk_level=raw_risk,
                        evidence=evidence,
                        timing_pvalue=round(timing_p, 4) if timing_p is not None else None,
                        logprobs_pvalue=round(logprobs_p, 4)
                        if logprobs_p is not None
                        else None,
                        dynamic_threshold=round(dyn_threshold, 4),
                        fusion_score=fusion_score,
                    )
                )

        return AnalysisReport(
            total_records=len(records),
            analyzed_records=len(eligible),
            alerts=alerts,
            summary_by_family=summary,
            baselines=baselines,
            baselines_updated=baselines_updated,
            alerts_suppressed_by_smoothing=suppressed,
        )

    def analyze_batch(self, texts: list[str]) -> list[FamilyScore]:
        return [self.classify_text(t) for t in texts]
