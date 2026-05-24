"""Multi-signal fusion decision engine (Phase 2)."""

from __future__ import annotations

from api_monitor.models import BaselineProfile

# Weights from technical planning doc
WEIGHT_FAMILY = 0.35
WEIGHT_TEXT_DRIFT = 0.25
WEIGHT_METADATA = 0.20
WEIGHT_TIMING = 0.10
WEIGHT_LOGPROBS = 0.10


def fusion_risk_level(
    *,
    family_mismatch: bool,
    family_margin: float,
    text_drift: float,
    dynamic_threshold: float,
    metadata_anomaly: bool,
    timing_pvalue: float | None,
    timing_pvalue_threshold: float,
    has_logprobs_drift: bool = False,
) -> tuple[str, float]:
    """Return (risk_level, fusion_score 0-1)."""
    score = 0.0

    if family_mismatch:
        score += WEIGHT_FAMILY * min(1.0, max(0.0, family_margin / dynamic_threshold))

    if text_drift > dynamic_threshold:
        ratio = min(1.0, text_drift / (dynamic_threshold * 2))
        score += WEIGHT_TEXT_DRIFT * ratio

    if metadata_anomaly:
        score += WEIGHT_METADATA

    if timing_pvalue is not None and timing_pvalue < timing_pvalue_threshold:
        score += WEIGHT_TIMING * (1.0 - timing_pvalue / timing_pvalue_threshold)

    if has_logprobs_drift:
        score += WEIGHT_LOGPROBS

    if score >= 0.55:
        return "high", round(score, 4)
    if score >= 0.30:
        return "medium", round(score, 4)
    return "low", round(score, 4)
