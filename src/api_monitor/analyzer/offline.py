"""Offline batch analyzer using sentence-transformers MiniLM (Plan A MVP)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from api_monitor.analyzer.families import (
    FAMILIES,
    FAMILY_REFERENCE_TEXTS,
    infer_expected_family,
)
from api_monitor.analyzer.lexicon import collect_lexicon_evidence
from api_monitor.models import AnalysisReport, AnalysisRow, FamilyScore, ResponseRecord

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class OfflineAnalyzer:
    """Encode responses and compare against per-family reference centroids."""

    def __init__(self, *, min_text_length: int = 32, drift_threshold: float = 0.15):
        self.min_text_length = min_text_length
        self.drift_threshold = drift_threshold
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

    def analyze_records(self, records: list[ResponseRecord]) -> AnalysisReport:
        eligible = [
            r
            for r in records
            if len((r.response_text or "").strip()) >= self.min_text_length
        ]
        alerts: list[AnalysisRow] = []
        summary: dict[str, int] = {}

        for record in eligible:
            score = self.classify_text(record.response_text)
            expected = infer_expected_family(record.model_requested)
            summary[score.family] = summary.get(score.family, 0) + 1

            drift = 0.0
            if expected and expected in score.all_scores:
                drift = max(0.0, score.all_scores[expected] - score.confidence)
                drift = abs(drift)

            mismatch = (
                expected is not None
                and expected != "unknown"
                and score.family != expected
                and score.confidence - score.all_scores.get(expected, 0.0)
                > self.drift_threshold
            )

            meta_evidence: list[str] = []
            fp = record.metadata.get("system_fingerprint")
            if fp is None and record.model_requested and "gpt" in (
                record.model_requested or ""
            ).lower():
                meta_evidence.append("system_fingerprint 字段缺失")
            elif isinstance(fp, str) and record.metadata.get("model"):
                meta_evidence.append(
                    f"响应 model 字段: {record.metadata.get('model')}"
                )

            evidence = collect_lexicon_evidence(
                record.response_text,
                expected=expected,
                predicted=score.family,
            ) + meta_evidence

            risk = "low"
            if mismatch:
                risk = "high"
            elif drift > self.drift_threshold:
                risk = "medium"

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
                        evidence=evidence,
                    )
                )

        return AnalysisReport(
            total_records=len(records),
            analyzed_records=len(eligible),
            alerts=alerts,
            summary_by_family=summary,
        )

    def analyze_batch(self, texts: list[str]) -> list[FamilyScore]:
        return [self.classify_text(t) for t in texts]
