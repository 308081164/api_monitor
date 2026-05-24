"""EMA baseline updates from low-risk observations (Phase 3)."""

from __future__ import annotations

from api_monitor.analyzer.drift import _mean, _std, dynamic_text_threshold
from api_monitor.models import BaselineProfile, ResponseRecord


def ema(old: float | None, new: float, alpha: float) -> float:
    if old is None:
        return new
    return (1.0 - alpha) * old + alpha * new


def ema_std(old_std: float, old_mean: float, new_mean: float, alpha: float) -> float:
    """Approximate std update via EMA on squared deviation."""
    dev = abs(new_mean - old_mean)
    return max(0.02, (1.0 - alpha) * old_std + alpha * dev)


def update_baseline_from_record(
    profile: BaselineProfile,
    record: ResponseRecord,
    *,
    drift_score: float,
    alpha: float,
) -> BaselineProfile:
    """Incrementally update baseline with a trusted (low-risk) sample."""
    text_mean = ema(profile.text_drift_mean, drift_score, alpha)
    text_std = ema_std(profile.text_drift_std, profile.text_drift_mean, drift_score, alpha)

    ttft = record.timing.ttft_ms
    ttft_mean = ema(profile.ttft_mean_ms, ttft, alpha) if ttft is not None else profile.ttft_mean_ms
    ttft_std = (
        ema_std(profile.ttft_std_ms or 0.0, profile.ttft_mean_ms or ttft or 0.0, ttft or 0.0, alpha)
        if ttft is not None
        else profile.ttft_std_ms
    )

    itts = record.timing.itts_ms
    itt_mean = profile.itt_mean_ms
    itt_std = profile.itt_std_ms
    if itts:
        batch_mean = _mean(itts)
        itt_mean = ema(profile.itt_mean_ms, batch_mean, alpha)
        itt_std = ema_std(profile.itt_std_ms or 0.0, profile.itt_mean_ms or batch_mean, batch_mean, alpha)

    lp = record.logprobs_stats
    avg_logprob = profile.avg_logprob
    logprob_entropy = profile.logprob_entropy_mean
    logprob_std = profile.logprob_std
    if lp is not None:
        avg_logprob = ema(profile.avg_logprob, lp.avg_logprob, alpha)
        logprob_entropy = ema(profile.logprob_entropy_mean, lp.mean_entropy, alpha)
        logprob_std = ema_std(
            profile.logprob_std or 0.05,
            profile.avg_logprob or lp.avg_logprob,
            lp.avg_logprob,
            alpha,
        )

    fps = list(profile.metadata_fingerprints)
    fp = record.metadata.get("system_fingerprint")
    if fp is not None and str(fp) not in fps:
        fps.append(str(fp))
        fps = fps[-10:]

    updated = BaselineProfile(
        model_key=profile.model_key,
        sample_count=profile.sample_count + 1,
        text_drift_mean=text_mean,
        text_drift_std=text_std,
        ttft_mean_ms=ttft_mean,
        ttft_std_ms=ttft_std,
        itt_mean_ms=itt_mean,
        itt_std_ms=itt_std,
        avg_logprob=avg_logprob,
        logprob_entropy_mean=logprob_entropy,
        logprob_std=logprob_std,
        metadata_fingerprints=fps,
        dynamic_threshold=0.15,
    )
    updated = BaselineProfile(
        model_key=updated.model_key,
        sample_count=updated.sample_count,
        text_drift_mean=updated.text_drift_mean,
        text_drift_std=updated.text_drift_std,
        ttft_mean_ms=updated.ttft_mean_ms,
        ttft_std_ms=updated.ttft_std_ms,
        itt_mean_ms=updated.itt_mean_ms,
        itt_std_ms=updated.itt_std_ms,
        avg_logprob=updated.avg_logprob,
        logprob_entropy_mean=updated.logprob_entropy_mean,
        logprob_std=updated.logprob_std,
        metadata_fingerprints=updated.metadata_fingerprints,
        dynamic_threshold=dynamic_text_threshold(updated),
    )
    return updated
