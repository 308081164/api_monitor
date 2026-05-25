from api_monitor.analyzer.reference import (
    reference_comparison_evidence,
    resolve_upstream_kind,
)
from api_monitor.models import ResponseRecord


def _rec(upstream: str, fp: str | None = None, kind: str = "relay") -> ResponseRecord:
    return ResponseRecord(
        id=1,
        timestamp="t",
        method="POST",
        path="/v1/chat/completions",
        upstream_url=upstream,
        model_requested="gpt-4o",
        response_text="x" * 40,
        metadata={"system_fingerprint": fp, "upstream_kind": kind} if fp else {"upstream_kind": kind},
    )


def test_resolve_upstream_kind():
    assert (
        resolve_upstream_kind(
            "https://api.openai.com/v1/chat",
            relay_url="https://relay.example.com",
            reference_url="https://api.openai.com",
        )
        == "reference"
    )


def test_reference_evidence_on_fingerprint_mismatch():
    ref = [_rec("https://api.openai.com/v1", "fp_official", "reference")]
    relay = _rec("https://relay.example.com/v1", "fp_fake", "relay")
    ev = reference_comparison_evidence(
        relay, reference_records=ref, relay_url="https://relay.example.com"
    )
    assert any("system_fingerprint" in e for e in ev)
