"""Factory helpers for analyzer from settings."""

from __future__ import annotations

from api_monitor.analyzer.offline import OfflineAnalyzer
from api_monitor.config import Settings
from api_monitor.storage.user_settings import UserSettingsStore, settings_path_for_db


def analyzer_from_settings(
    settings: Settings,
    *,
    db_path: str | None = None,
    load_user_prefs: bool = True,
) -> OfflineAnalyzer:
    effective = settings
    if load_user_prefs:
        store = UserSettingsStore(settings_path_for_db(settings.db_path))
        effective = settings.merge_user_settings(store.load())

    return OfflineAnalyzer(
        min_text_length=effective.min_text_length,
        drift_threshold=effective.drift_threshold,
        baseline_min_samples=effective.baseline_min_samples,
        timing_pvalue_threshold=effective.timing_pvalue_threshold,
        logprobs_pvalue_threshold=effective.logprobs_pvalue_threshold,
        baseline_ema_alpha=effective.baseline_ema_alpha,
        baseline_auto_update=effective.baseline_auto_update,
        alert_smoothing_window=effective.alert_smoothing_window,
        analysis_mode=effective.analysis_mode,
        relay_upstream_url=effective.upstream_base_url,
        reference_upstream_url=effective.reference_upstream_url,
        db_path=db_path or str(effective.db_path),
    )
