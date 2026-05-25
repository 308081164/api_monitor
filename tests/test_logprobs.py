import json

from api_monitor.analyzer.logprobs import extract_logprobs_stats, logprobs_drift_pvalue
from api_monitor.models import BaselineProfile, LogprobsStats


def test_extract_openai_logprobs():
    body = json.dumps(
        {
            "choices": [
                {
                    "logprobs": {
                        "content": [
                            {"token": "Hi", "logprob": -0.5},
                            {"token": "!", "logprob": -0.2},
                        ]
                    }
                }
            ]
        }
    ).encode()
    stats = extract_logprobs_stats(body)
    assert stats is not None
    assert stats["token_count"] == 2
    assert stats["avg_logprob"] < 0


def test_logprobs_drift_detects_shift():
    baseline = BaselineProfile(
        model_key="gpt-4o",
        sample_count=20,
        avg_logprob=-0.5,
        logprob_std=0.05,
    )
    current = LogprobsStats(avg_logprob=-0.9, mean_entropy=0.5, token_count=10)
    p = logprobs_drift_pvalue(current, baseline)
    assert p is not None
    assert p < 0.05
