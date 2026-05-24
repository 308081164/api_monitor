"""Ingest API for browser extension (Plan B) and external clients."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from api_monitor.proxy.extract import extract_logprobs_stats, extract_metadata, extract_response_text
from api_monitor.storage.logger import ResponseLogger


class IngestPayload(BaseModel):
    url: str
    method: str = "POST"
    model_requested: str | None = None
    response_body: str = Field(..., description="Raw JSON response body")
    timing: dict[str, Any] | None = None
    source: str = "extension"


def ingest_record(logger: ResponseLogger, payload: IngestPayload) -> int:
    body = payload.response_body.encode("utf-8")
    text = extract_response_text(body)
    if not text.strip():
        raise ValueError("empty_response_text")

    meta = extract_metadata(body)
    lp = extract_logprobs_stats(body)
    if lp:
        meta["logprobs_stats"] = lp

    return logger.log(
        method=payload.method,
        path=payload.url,
        upstream_url=payload.url,
        model_requested=payload.model_requested,
        response_text=text,
        metadata={**meta, "ingest_source": payload.source},
        timing=payload.timing or {},
    )
