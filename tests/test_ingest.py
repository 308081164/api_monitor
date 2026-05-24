import json
from pathlib import Path

from fastapi.testclient import TestClient

from api_monitor.config import Settings
from api_monitor.proxy.app import create_app


def test_ingest_endpoint(tmp_path: Path):
    settings = Settings(
        host="127.0.0.1",
        port=8080,
        upstream_base_url="https://api.example.com",
        db_path=tmp_path / "r.db",
        min_text_length=8,
        drift_threshold=0.15,
        baseline_min_samples=5,
        timing_pvalue_threshold=0.05,
        enable_dashboard=True,
        baseline_ema_alpha=0.08,
        baseline_auto_update=True,
        alert_smoothing_window=3,
        logprobs_pvalue_threshold=0.01,
        enable_cors=True,
    )
    client = TestClient(create_app(settings))
    body = json.dumps(
        {
            "choices": [
                {"message": {"role": "assistant", "content": "Hello world!!!"}}
            ]
        }
    )
    resp = client.post(
        "/api/ingest",
        json={
            "url": "https://api.openai.com/v1/chat/completions",
            "model_requested": "gpt-4o",
            "response_body": body,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["record_id"] == 1

    stats = client.get("/api/dashboard/stats")
    assert stats.json()["total_records"] == 1
