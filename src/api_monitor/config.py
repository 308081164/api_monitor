"""Runtime configuration for API Monitor (Plan A: transparent proxy)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(key: str, default: str | None = None) -> str | None:
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return value.strip()


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    host: str = "127.0.0.1"
    port: int = 8080
    upstream_base_url: str = ""
    db_path: Path = Path("responses.db")
    min_text_length: int = 32
    drift_threshold: float = 0.15

    @classmethod
    def from_env(cls) -> Settings:
        db = _env("SENTINEL_DB_PATH", "responses.db")
        upstream = _env("SENTINEL_UPSTREAM_URL", "") or _env("OPENAI_BASE_URL", "")
        port_raw = _env("SENTINEL_PORT", "8080")
        min_len_raw = _env("SENTINEL_MIN_TEXT_LENGTH", "32")
        drift_raw = _env("SENTINEL_DRIFT_THRESHOLD", "0.15")
        return cls(
            host=_env("SENTINEL_HOST", "127.0.0.1") or "127.0.0.1",
            port=int(port_raw) if port_raw else 8080,
            upstream_base_url=(upstream or "").rstrip("/"),
            db_path=Path(db or "responses.db"),
            min_text_length=int(min_len_raw) if min_len_raw else 32,
            drift_threshold=float(drift_raw) if drift_raw else 0.15,
        )


def default_data_dir() -> Path:
    base = _env("SENTINEL_DATA_DIR")
    if base:
        return Path(base)
    return Path.home() / ".api-monitor"
