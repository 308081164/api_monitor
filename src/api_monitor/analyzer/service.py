"""Factory helpers for analyzer from settings."""

from __future__ import annotations

from api_monitor.analyzer.offline import OfflineAnalyzer
from api_monitor.config import Settings


def analyzer_from_settings(settings: Settings, *, db_path: str | None = None) -> OfflineAnalyzer:
    return OfflineAnalyzer(
        min_text_length=settings.min_text_length,
        drift_threshold=settings.drift_threshold,
        baseline_min_samples=settings.baseline_min_samples,
        timing_pvalue_threshold=settings.timing_pvalue_threshold,
        logprobs_pvalue_threshold=settings.logprobs_pvalue_threshold,
        baseline_ema_alpha=settings.baseline_ema_alpha,
        baseline_auto_update=settings.baseline_auto_update,
        alert_smoothing_window=settings.alert_smoothing_window,
        db_path=db_path or str(settings.db_path),
    )
