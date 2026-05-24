"""Logprobs extraction and drift detection (optional API signal)."""

from __future__ import annotations

import json
import math
from typing import Any

from api_monitor.models import BaselineProfile, LogprobsStats


def _entropy_from_logprob(lp: float) -> float:
    p = math.exp(lp) if lp <= 0 else math.exp(min(lp, 0.0))
    if p <= 0:
        return 0.0
    return -p * math.log(p + 1e-12)


def extract_logprobs_stats(body: bytes) -> dict[str, Any] | None:
    """Parse logprobs from OpenAI / Gemini JSON responses."""
    if not body:
        return None
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    logprobs: list[float] = []
    entropies: list[float] = []

    choices = data.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            lp_block = choice.get("logprobs") or {}
            content_items = lp_block.get("content") if isinstance(lp_block, dict) else None
            if isinstance(content_items, list):
                for item in content_items:
                    if isinstance(item, dict) and "logprob" in item:
                        lp = float(item["logprob"])
                        logprobs.append(lp)
                        entropies.append(_entropy_from_logprob(lp))

    # Gemini logprobs_result
    candidates = data.get("candidates")
    if isinstance(candidates, list):
        for cand in candidates:
            if not isinstance(cand, dict):
                continue
            result = cand.get("logprobs_result") or cand.get("logprobsResult")
            if not isinstance(result, dict):
                continue
            for chosen in result.get("chosen_candidates") or result.get("chosenCandidates") or []:
                if isinstance(chosen, dict) and "log_probability" in chosen:
                    lp = float(chosen["log_probability"])
                    logprobs.append(lp)
                    entropies.append(_entropy_from_logprob(lp))

    if not logprobs:
        return None

    return {
        "avg_logprob": sum(logprobs) / len(logprobs),
        "mean_entropy": sum(entropies) / len(entropies) if entropies else 0.0,
        "token_count": len(logprobs),
    }


def logprobs_drift_pvalue(
    current: LogprobsStats | None,
    baseline: BaselineProfile,
) -> float | None:
    if current is None or baseline.avg_logprob is None:
        return None
    if baseline.logprob_std is None or baseline.logprob_std <= 0:
        return None

    z = abs(current.avg_logprob - baseline.avg_logprob) / baseline.logprob_std
    # Two-tailed normal approximation
    p = math.erfc(z / math.sqrt(2))
    return max(0.0, min(1.0, p))
