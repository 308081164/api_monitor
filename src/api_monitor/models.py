"""Shared data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimingInfo:
    ttft_ms: float | None = None
    total_ms: float | None = None
    itts_ms: list[float] = field(default_factory=list)
    token_chunks: int | None = None


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
class BaselineProfile:
    model_key: str
    sample_count: int
    text_drift_mean: float = 0.0
    text_drift_std: float = 0.05
    ttft_mean_ms: float | None = None
    ttft_std_ms: float | None = None
    itt_mean_ms: float | None = None
    itt_std_ms: float | None = None
    metadata_fingerprints: list[str] = field(default_factory=list)
    dynamic_threshold: float = 0.15


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
    timing_pvalue: float | None = None
    dynamic_threshold: float | None = None
    fusion_score: float | None = None


@dataclass
class AnalysisReport:
    total_records: int
    analyzed_records: int
    alerts: list[AnalysisRow] = field(default_factory=list)
    summary_by_family: dict[str, int] = field(default_factory=dict)
    baselines: dict[str, BaselineProfile] = field(default_factory=dict)
