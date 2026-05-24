"""Dashboard API and static UI routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from api_monitor.analyzer.offline import OfflineAnalyzer
from api_monitor.analyzer.report import render_html_report, render_markdown_report
from api_monitor.config import Settings
from api_monitor.storage.baseline import BaselineStore
from api_monitor.storage.logger import ResponseLogger

_STATIC = Path(__file__).parent / "static"


def register_dashboard_routes(app: FastAPI, settings: Settings) -> None:
    logger = ResponseLogger(settings.db_path)
    baselines = BaselineStore(settings.db_path)

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard_page() -> HTMLResponse:
        html_path = _STATIC / "index.html"
        if not html_path.is_file():
            raise HTTPException(404, "Dashboard UI not found")
        return HTMLResponse(html_path.read_text(encoding="utf-8"))

    @app.get("/api/dashboard/stats")
    async def dashboard_stats() -> dict[str, Any]:
        records = logger.fetch_recent(limit=200)
        return {
            "total_records": logger.count(),
            "recent_count": len(records),
            "baselines": [
                {
                    "model_key": p.model_key,
                    "sample_count": p.sample_count,
                    "dynamic_threshold": p.dynamic_threshold,
                    "ttft_mean_ms": p.ttft_mean_ms,
                    "itt_mean_ms": p.itt_mean_ms,
                }
                for p in baselines.list_all().values()
            ],
        }

    @app.get("/api/dashboard/records")
    async def dashboard_records(limit: int = 30) -> dict[str, Any]:
        records = logger.fetch_recent(limit=min(limit, 100))
        return {
            "records": [
                {
                    "id": r.id,
                    "timestamp": r.timestamp,
                    "model_requested": r.model_requested,
                    "path": r.path,
                    "text_preview": (r.response_text or "")[:120],
                    "ttft_ms": r.timing.ttft_ms,
                    "total_ms": r.timing.total_ms,
                    "itt_count": len(r.timing.itts_ms),
                }
                for r in records
            ]
        }

    @app.post("/api/dashboard/analyze")
    async def dashboard_analyze(format: str = "json") -> Any:
        records = logger.fetch_all()
        if not records:
            return JSONResponse({"error": "no_records"}, status_code=400)

        analyzer = OfflineAnalyzer(
            min_text_length=settings.min_text_length,
            drift_threshold=settings.drift_threshold,
            baseline_min_samples=settings.baseline_min_samples,
            timing_pvalue_threshold=settings.timing_pvalue_threshold,
            db_path=str(settings.db_path),
        )
        try:
            report = analyzer.analyze_records(records)
        except RuntimeError as exc:
            return JSONResponse({"error": str(exc)}, status_code=503)

        if format == "html":
            return HTMLResponse(render_html_report(report))
        if format == "markdown":
            return JSONResponse({"markdown": render_markdown_report(report)})

        return {
            "total_records": report.total_records,
            "analyzed_records": report.analyzed_records,
            "alert_count": len(report.alerts),
            "alerts": [
                {
                    "record_id": a.record_id,
                    "timestamp": a.timestamp,
                    "model_requested": a.model_requested,
                    "expected_family": a.expected_family,
                    "predicted_family": a.predicted_family,
                    "risk_level": a.risk_level,
                    "fusion_score": a.fusion_score,
                    "evidence": a.evidence,
                }
                for a in report.alerts
            ],
            "summary_by_family": report.summary_by_family,
        }
