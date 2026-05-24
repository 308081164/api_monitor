"""Auto-build per-model baselines from historical records."""

from __future__ import annotations

from collections import defaultdict

from api_monitor.analyzer.drift import _mean, _std, dynamic_text_threshold
from api_monitor.analyzer.families import infer_expected_family
from api_monitor.models import BaselineProfile, ResponseRecord


def _model_key(record: ResponseRecord) -> str:
    return record.model_requested or "__unknown__"


def build_baselines(
    records: list[ResponseRecord],
    *,
    min_samples: int = 20,
    default_threshold: float = 0.15,
    drift_scores: dict[int, float] | None = None,
) -> dict[str, BaselineProfile]:
    """Build baseline profiles from the earliest samples per model."""
    grouped: dict[str, list[ResponseRecord]] = defaultdict(list)
    for record in records:
        grouped[_model_key(record)].append(record)

    profiles: dict[str, BaselineProfile] = {}
    for model_key, group in grouped.items():
        if len(group) < min_samples:
            continue
        bootstrap = group[:min_samples]
        drifts = []
        if drift_scores:
            drifts = [drift_scores.get(r.id, 0.0) for r in bootstrap]
        else:
            drifts = [0.0] * len(bootstrap)

        ttfts = [r.timing.ttft_ms for r in bootstrap if r.timing.ttft_ms is not None]
        all_itts: list[float] = []
        for r in bootstrap:
            all_itts.extend(r.timing.itts_ms)

        logprobs = [r.logprobs_stats for r in bootstrap if r.logprobs_stats]
        avg_lps = [lp.avg_logprob for lp in logprobs]
        entropies = [lp.mean_entropy for lp in logprobs]

        fps: list[str] = []
        for r in bootstrap:
            fp = r.metadata.get("system_fingerprint")
            if fp is not None:
                fps.append(str(fp))

        drift_mean = _mean(drifts)
        drift_std = max(_std(drifts, drift_mean), 0.02)
        partial = BaselineProfile(
            model_key=model_key,
            sample_count=len(bootstrap),
            text_drift_mean=drift_mean,
            text_drift_std=drift_std,
            ttft_mean_ms=_mean(ttfts) if ttfts else None,
            ttft_std_ms=_std(ttfts) if ttfts else None,
            itt_mean_ms=_mean(all_itts) if all_itts else None,
            itt_std_ms=_std(all_itts) if all_itts else None,
            avg_logprob=_mean(avg_lps) if avg_lps else None,
            logprob_entropy_mean=_mean(entropies) if entropies else None,
            logprob_std=_std(avg_lps) if len(avg_lps) > 1 else None,
            metadata_fingerprints=list(dict.fromkeys(fps)),
            dynamic_threshold=0.15,
        )
        profile = BaselineProfile(
            model_key=partial.model_key,
            sample_count=partial.sample_count,
            text_drift_mean=partial.text_drift_mean,
            text_drift_std=partial.text_drift_std,
            ttft_mean_ms=partial.ttft_mean_ms,
            ttft_std_ms=partial.ttft_std_ms,
            itt_mean_ms=partial.itt_mean_ms,
            itt_std_ms=partial.itt_std_ms,
            avg_logprob=partial.avg_logprob,
            logprob_entropy_mean=partial.logprob_entropy_mean,
            logprob_std=partial.logprob_std,
            metadata_fingerprints=partial.metadata_fingerprints,
            dynamic_threshold=dynamic_text_threshold(partial, floor=default_threshold),
        )

        if model_key == "__unknown__" and not fps:
            continue
        if infer_expected_family(model_key) == "unknown" and not fps and not ttfts:
            continue
        profiles[model_key] = profile

    return profiles
