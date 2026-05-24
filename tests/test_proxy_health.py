from pathlib import Path

from fastapi.testclient import TestClient

from api_monitor.config import Settings
from api_monitor.proxy.app import create_app


def test_health_endpoint(tmp_path: Path):
    settings = Settings(
        host="127.0.0.1",
        port=8080,
        upstream_base_url="https://api.example.com",
        db_path=tmp_path / "r.db",
        min_text_length=32,
        drift_threshold=0.15,
        baseline_min_samples=20,
        timing_pvalue_threshold=0.05,
        enable_dashboard=True,
    )
    client = TestClient(create_app(settings))
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["dashboard"] is True


def test_dashboard_page(tmp_path: Path):
    settings = Settings(
        host="127.0.0.1",
        port=8080,
        upstream_base_url="https://api.example.com",
        db_path=tmp_path / "r.db",
        min_text_length=32,
        drift_threshold=0.15,
        baseline_min_samples=20,
        timing_pvalue_threshold=0.05,
        enable_dashboard=True,
    )
    client = TestClient(create_app(settings))
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "API Monitor" in resp.text
