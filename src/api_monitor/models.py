"""Shared data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimingInfo:
    ttft_ms: float | None = None
    total_ms: float | None = None


@dataclass
class ResponseRecord:
    id: int
    timestamp: str
    method: str
    path: str
    upstream_url: str
    model_requested: str | None
    response_text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timing: TimingInfo = field(default_factory=TimingInfo)


@dataclass
class FamilyScore:
    family: str
    confidence: float
    all_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class AnalysisRow:
    record_id: int
    timestamp: str
    model_requested: str | None
    expected_family: str | None
    predicted_family: str
    confidence: float
    drift_score: float
    risk_level: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class AnalysisReport:
    total_records: int
    analyzed_records: int
    alerts: list[AnalysisRow] = field(default_factory=list)
    summary_by_family: dict[str, int] = field(default_factory=dict)
