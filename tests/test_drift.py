from api_monitor.analyzer.baseline_builder import build_baselines
from api_monitor.analyzer.drift import dynamic_text_threshold, ks_statistic
from api_monitor.models import BaselineProfile, ResponseRecord, TimingInfo


def _record(rid: int, model: str, text: str, ttft: float = 100.0) -> ResponseRecord:
    return ResponseRecord(
        id=rid,
        timestamp="2026-05-24T00:00:00+00:00",
        method="POST",
        path="/v1/chat/completions",
        upstream_url="https://api.example.com/v1/chat/completions",
        model_requested=model,
        response_text=text,
        metadata={"system_fingerprint": "fp_test"},
        timing=TimingInfo(ttft_ms=ttft, total_ms=ttft + 50, itts_ms=[10.0, 12.0, 11.0]),
    )


def test_ks_statistic_detects_shift():
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    b = [10.0, 11.0, 12.0, 13.0, 14.0]
    d, p = ks_statistic(a, b)
    assert d > 0.5
    assert p < 0.1


def test_build_baselines_requires_min_samples():
    records = [_record(i, "gpt-4o", "x" * 40) for i in range(25)]
    profiles = build_baselines(records, min_samples=20, drift_scores={r.id: 0.05 for r in records})
    assert "gpt-4o" in profiles
    assert profiles["gpt-4o"].sample_count == 20


def test_dynamic_threshold():
    profile = BaselineProfile(
        model_key="gpt-4o",
        sample_count=20,
        text_drift_mean=0.1,
        text_drift_std=0.03,
    )
    assert dynamic_text_threshold(profile, floor=0.15) >= 0.15
