"""Timing and metadata drift detection with statistical tests."""

from __future__ import annotations

import math
from typing import Sequence

from api_monitor.models import BaselineProfile, ResponseRecord, TimingInfo


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: Sequence[float], mean: float | None = None) -> float:
    if len(values) < 2:
        return 0.0
    mu = mean if mean is not None else _mean(values)
    var = sum((v - mu) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def ks_statistic(sample_a: Sequence[float], sample_b: Sequence[float]) -> tuple[float, float]:
    """Two-sample KS test (stdlib-only approximation of p-value)."""
    if len(sample_a) < 2 or len(sample_b) < 2:
        return 0.0, 1.0

    a = sorted(sample_a)
    b = sorted(sample_b)
    na, nb = len(a), len(b)
    ia = ib = 0
    d = 0.0
    while ia < na and ib < nb:
        if a[ia] <= b[ib]:
            ia += 1
        else:
            ib += 1
        fa = ia / na
        fb = ib / nb
        d = max(d, abs(fa - fb))
    while ia < na:
        ia += 1
        d = max(d, abs(ia / na - ib / nb))
    while ib < nb:
        ib += 1
        d = max(d, abs(ia / na - ib / nb))

    n_eff = (na * nb) / (na + nb)
    # Kolmogorov asymptotic p-value
    if n_eff <= 0:
        return d, 1.0
    lam = (math.sqrt(n_eff) + 0.12 + 0.11 / math.sqrt(n_eff)) * d
    p = 0.0
    for k in range(1, 20):
        p += 2 * ((-1) ** (k - 1)) * math.exp(-2 * (lam**2) * (k**2))
    p = max(0.0, min(1.0, p))
    return d, p


def dynamic_text_threshold(profile: BaselineProfile, floor: float = 0.10) -> float:
    """Threshold = mean + 2*std, bounded below by floor."""
    return max(floor, profile.text_drift_mean + 2.0 * profile.text_drift_std)


def timing_drift_pvalue(
    timing: TimingInfo,
    baseline: BaselineProfile,
) -> float | None:
    """Compare current ITTs / TTFT against baseline using KS test."""
    samples: list[float] = []
    if timing.itts_ms:
        samples = list(timing.itts_ms)
    elif timing.ttft_ms is not None:
        samples = [timing.ttft_ms]

    baseline_samples: list[float] = []
    if baseline.itt_mean_ms is not None and baseline.itt_std_ms is not None:
        # Reconstruct pseudo-samples from stored mean/std for KS
        baseline_samples = [
            baseline.itt_mean_ms,
            baseline.itt_mean_ms + baseline.itt_std_ms,
            max(0.0, baseline.itt_mean_ms - baseline.itt_std_ms),
        ]
    elif baseline.ttft_mean_ms is not None and baseline.ttft_std_ms is not None:
        baseline_samples = [
            baseline.ttft_mean_ms,
            baseline.ttft_mean_ms + baseline.ttft_std_ms,
            max(0.0, baseline.ttft_mean_ms - baseline.ttft_std_ms),
        ]

    if len(samples) < 1 or len(baseline_samples) < 2:
        return None

  # Pad single-sample current with total latency spread if needed
    if len(samples) == 1 and timing.total_ms:
        samples = [samples[0], timing.total_ms * 0.5, timing.total_ms * 0.8]

    _, p = ks_statistic(samples, baseline_samples)
    return p


def metadata_changed(record: ResponseRecord, baseline: BaselineProfile) -> list[str]:
    evidence: list[str] = []
    fp = record.metadata.get("system_fingerprint")
    if fp is not None:
        fp_str = str(fp)
        if baseline.metadata_fingerprints and fp_str not in baseline.metadata_fingerprints:
            evidence.append(
                f"system_fingerprint 变更: 基线 {baseline.metadata_fingerprints[:3]} → 当前 `{fp_str}`"
            )
    elif record.model_requested and "gpt" in record.model_requested.lower():
        if baseline.metadata_fingerprints:
            evidence.append("system_fingerprint 字段缺失（基线期存在）")

    model_field = record.metadata.get("model")
    if isinstance(model_field, str) and record.model_requested:
        if model_field.split("/")[-1] != record.model_requested.split("/")[-1]:
            evidence.append(
                f"响应 model 字段与请求不一致: 请求 `{record.model_requested}` / 响应 `{model_field}`"
            )

    gemini_ver = record.metadata.get("modelVersion")
    if gemini_ver and record.model_requested:
        if record.model_requested.lower() not in str(gemini_ver).lower():
            evidence.append(f"Gemini modelVersion 与请求模型不匹配: `{gemini_ver}`")

    return evidence
