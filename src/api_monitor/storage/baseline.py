"""Baseline profiles per requested model — auto-built from early samples."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from api_monitor.models import BaselineProfile


class BaselineStore:
    """Persist rolling baseline statistics keyed by model_requested."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS baselines (
                    model_key TEXT PRIMARY KEY,
                    sample_count INTEGER NOT NULL,
                    text_drift_mean REAL NOT NULL,
                    text_drift_std REAL NOT NULL,
                    ttft_mean_ms REAL,
                    ttft_std_ms REAL,
                    itt_mean_ms REAL,
                    itt_std_ms REAL,
                    metadata_fingerprints TEXT NOT NULL DEFAULT '[]',
                    dynamic_threshold REAL NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def get(self, model_key: str) -> BaselineProfile | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM baselines WHERE model_key = ?", (model_key,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_profile(row)

    def list_all(self) -> dict[str, BaselineProfile]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM baselines ORDER BY model_key").fetchall()
        return {str(r["model_key"]): self._row_to_profile(r) for r in rows}

    def upsert(self, profile: BaselineProfile) -> None:
        from datetime import datetime, timezone

        ts = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO baselines (
                    model_key, sample_count, text_drift_mean, text_drift_std,
                    ttft_mean_ms, ttft_std_ms, itt_mean_ms, itt_std_ms,
                    metadata_fingerprints, dynamic_threshold, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_key) DO UPDATE SET
                    sample_count=excluded.sample_count,
                    text_drift_mean=excluded.text_drift_mean,
                    text_drift_std=excluded.text_drift_std,
                    ttft_mean_ms=excluded.ttft_mean_ms,
                    ttft_std_ms=excluded.ttft_std_ms,
                    itt_mean_ms=excluded.itt_mean_ms,
                    itt_std_ms=excluded.itt_std_ms,
                    metadata_fingerprints=excluded.metadata_fingerprints,
                    dynamic_threshold=excluded.dynamic_threshold,
                    updated_at=excluded.updated_at
                """,
                (
                    profile.model_key,
                    profile.sample_count,
                    profile.text_drift_mean,
                    profile.text_drift_std,
                    profile.ttft_mean_ms,
                    profile.ttft_std_ms,
                    profile.itt_mean_ms,
                    profile.itt_std_ms,
                    json.dumps(profile.metadata_fingerprints, ensure_ascii=False),
                    profile.dynamic_threshold,
                    ts,
                ),
            )
            conn.commit()

    @staticmethod
    def _row_to_profile(row: sqlite3.Row) -> BaselineProfile:
        return BaselineProfile(
            model_key=str(row["model_key"]),
            sample_count=int(row["sample_count"]),
            text_drift_mean=float(row["text_drift_mean"]),
            text_drift_std=float(row["text_drift_std"]),
            ttft_mean_ms=row["ttft_mean_ms"],
            ttft_std_ms=row["ttft_std_ms"],
            itt_mean_ms=row["itt_mean_ms"],
            itt_std_ms=row["itt_std_ms"],
            metadata_fingerprints=json.loads(row["metadata_fingerprints"] or "[]"),
            dynamic_threshold=float(row["dynamic_threshold"]),
        )
