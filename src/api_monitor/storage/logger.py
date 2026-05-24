"""SQLite response logger — zero-compute recording during proxy use."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from api_monitor.models import ResponseRecord, TimingInfo


class ResponseLogger:
    """Append-only SQLite store for intercepted API responses."""

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
                CREATE TABLE IF NOT EXISTS responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    method TEXT NOT NULL,
                    path TEXT NOT NULL,
                    upstream_url TEXT NOT NULL,
                    model_requested TEXT,
                    response_text TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    timing TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_responses_ts ON responses(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_responses_model ON responses(model_requested)"
            )
            conn.commit()

    def log(
        self,
        *,
        method: str,
        path: str,
        upstream_url: str,
        model_requested: str | None,
        response_text: str,
        metadata: dict[str, Any] | None = None,
        timing: dict[str, Any] | None = None,
    ) -> int:
        ts = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO responses
                (timestamp, method, path, upstream_url, model_requested,
                 response_text, metadata, timing)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    method,
                    path,
                    upstream_url,
                    model_requested,
                    response_text,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    json.dumps(timing or {}, ensure_ascii=False),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM responses").fetchone()
            return int(row["c"])

    def fetch_recent(self, *, limit: int = 50) -> list[ResponseRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, timestamp, method, path, upstream_url, model_requested,
                       response_text, metadata, timing
                FROM responses ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_record(r) for r in reversed(rows)]

    def fetch_since(
        self, *, limit: int | None = None, min_id: int = 0
    ) -> list[ResponseRecord]:
        sql = """
            SELECT id, timestamp, method, path, upstream_url, model_requested,
                   response_text, metadata, timing
            FROM responses
            WHERE id > ?
            ORDER BY id ASC
        """
        params: list[Any] = [min_id]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [self._row_to_record(r) for r in rows]

    def fetch_all(self, *, limit: int | None = None) -> list[ResponseRecord]:
        return self.fetch_since(limit=limit, min_id=0)

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> ResponseRecord:
        timing_raw = json.loads(row["timing"] or "{}")
        return ResponseRecord(
            id=int(row["id"]),
            timestamp=str(row["timestamp"]),
            method=str(row["method"]),
            path=str(row["path"]),
            upstream_url=str(row["upstream_url"]),
            model_requested=row["model_requested"],
            response_text=str(row["response_text"] or ""),
            metadata=json.loads(row["metadata"] or "{}"),
            timing=TimingInfo(
                ttft_ms=timing_raw.get("ttft_ms"),
                total_ms=timing_raw.get("total_ms"),
                itts_ms=list(timing_raw.get("itts_ms") or []),
                token_chunks=timing_raw.get("token_chunks"),
            ),
        )
