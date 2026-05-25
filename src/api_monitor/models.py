"""Shared data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LogprobsStats:
    avg_logprob: float
    mean_entropy: float
    token_count: int


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

    @property
    def logprobs_stats(self) -> LogprobsStats | None:
        raw = self.metadata.get("logprobs_stats")
        if not isinstance(raw, dict):
            return None
        try:
            return LogprobsStats(
                avg_logprob=float(raw["avg_logprob"]),
                mean_entropy=float(raw["mean_entropy"]),
                token_count=int(raw["token_count"]),
            )
        except (KeyError, TypeError, ValueError):
            return None


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
    avg_logprob: float | None = None
    logprob_entropy_mean: float | None = None
    logprob_std: float | None = None
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
    raw_risk_level: str | None = None
    evidence: list[str] = field(default_factory=list)
    timing_pvalue: float | None = None
    logprobs_pvalue: float | None = None
    dynamic_threshold: float | None = None
    fusion_score: float | None = None


@dataclass
class AnalysisReport:
    total_records: int
    analyzed_records: int
    alerts: list[AnalysisRow] = field(default_factory=list)
    summary_by_family: dict[str, int] = field(default_factory=dict)
    baselines: dict[str, BaselineProfile] = field(default_factory=dict)
    baselines_updated: int = 0
    alerts_suppressed_by_smoothing: int = 0
