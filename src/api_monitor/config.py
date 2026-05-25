"""Runtime configuration for API Monitor (Plan A: transparent proxy)."""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path


def _env(key: str, default: str | None = None) -> str | None:
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _bool_env(key: str, default: bool = True) -> bool:
    raw = _env(key, "true" if default else "false")
    return (raw or "false").lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    host: str = "127.0.0.1"
    port: int = 8080
    upstream_base_url: str = ""
    db_path: Path = Path("responses.db")
    min_text_length: int = 32
    drift_threshold: float = 0.15
    baseline_min_samples: int = 20
    timing_pvalue_threshold: float = 0.05
    enable_dashboard: bool = True
    baseline_ema_alpha: float = 0.08
    baseline_auto_update: bool = True
    alert_smoothing_window: int = 3
    logprobs_pvalue_threshold: float = 0.01
    enable_cors: bool = True

    def with_overrides(self, **kwargs: object) -> Settings:
        data = {f.name: getattr(self, f.name) for f in fields(self)}
        data.update(kwargs)
        return Settings(**data)

    @classmethod
    def from_env(cls) -> Settings:
        db = _env("SENTINEL_DB_PATH", "responses.db")
        upstream = _env("SENTINEL_UPSTREAM_URL", "") or _env("OPENAI_BASE_URL", "")
        port_raw = _env("SENTINEL_PORT", "8080")
        min_len_raw = _env("SENTINEL_MIN_TEXT_LENGTH", "32")
        drift_raw = _env("SENTINEL_DRIFT_THRESHOLD", "0.15")
        baseline_raw = _env("SENTINEL_BASELINE_MIN_SAMPLES", "20")
        timing_p_raw = _env("SENTINEL_TIMING_PVALUE", "0.05")
        ema_raw = _env("SENTINEL_BASELINE_EMA_ALPHA", "0.08")
        smooth_raw = _env("SENTINEL_ALERT_SMOOTHING_WINDOW", "3")
        logprob_p_raw = _env("SENTINEL_LOGPROBS_PVALUE", "0.01")
        return cls(
            host=_env("SENTINEL_HOST", "127.0.0.1") or "127.0.0.1",
            port=int(port_raw) if port_raw else 8080,
            upstream_base_url=(upstream or "").rstrip("/"),
            db_path=Path(db or "responses.db"),
            min_text_length=int(min_len_raw) if min_len_raw else 32,
            drift_threshold=float(drift_raw) if drift_raw else 0.15,
            baseline_min_samples=int(baseline_raw) if baseline_raw else 20,
            timing_pvalue_threshold=float(timing_p_raw) if timing_p_raw else 0.05,
            enable_dashboard=_bool_env("SENTINEL_ENABLE_DASHBOARD", True),
            baseline_ema_alpha=float(ema_raw) if ema_raw else 0.08,
            baseline_auto_update=_bool_env("SENTINEL_BASELINE_AUTO_UPDATE", True),
            alert_smoothing_window=int(smooth_raw) if smooth_raw else 3,
            logprobs_pvalue_threshold=float(logprob_p_raw) if logprob_p_raw else 0.01,
            enable_cors=_bool_env("SENTINEL_ENABLE_CORS", True),
        )


def default_data_dir() -> Path:
    base = _env("SENTINEL_DATA_DIR")
    if base:
        return Path(base)
    return Path.home() / ".api-monitor"
