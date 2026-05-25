"""Dashboard API, ingest endpoint, settings, and alert dispatch."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from api_monitor.alerts import dispatch_report_alerts
from api_monitor.analyzer.report import (
    render_html_report,
    render_json_report,
    render_markdown_report,
)
from api_monitor.analyzer.service import analyzer_from_settings
from api_monitor.config import Settings
from api_monitor.dashboard.ingest import IngestPayload, ingest_record
from api_monitor.storage.baseline import BaselineStore
from api_monitor.storage.logger import ResponseLogger
from api_monitor.storage.user_settings import UserSettings, UserSettingsStore, settings_path_for_db

_STATIC = Path(__file__).parent / "static"


class UserSettingsUpdate(BaseModel):
    onboarding_completed: bool | None = None
    upstream_url: str | None = None
    reference_upstream_url: str | None = None
    analysis_mode: str | None = Field(None, pattern="^(lite|precise)$")
    alert_system_notify: bool | None = None
    alert_webhook: bool | None = None
    webhook_url: str | None = None
    alert_min_risk: str | None = Field(None, pattern="^(medium|high)$")


def register_dashboard_routes(app: FastAPI, settings: Settings) -> None:
    logger = ResponseLogger(settings.db_path)
    baselines = BaselineStore(settings.db_path)
    prefs_path = settings_path_for_db(settings.db_path)
    user_store = UserSettingsStore(prefs_path)

    def _effective_settings() -> Settings:
        return settings.merge_user_settings(user_store.load())

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard_page() -> HTMLResponse:
        html_path = _STATIC / "index.html"
        if not html_path.is_file():
            raise HTTPException(404, "Dashboard UI not found")
        return HTMLResponse(html_path.read_text(encoding="utf-8"))

    @app.get("/api/dashboard/onboarding")
    async def onboarding_status() -> dict[str, Any]:
        prefs = user_store.load()
        eff = _effective_settings()
        total = logger.count()
        return {
            "onboarding_completed": prefs.onboarding_completed,
            "upstream_configured": bool(eff.upstream_base_url),
            "reference_configured": bool(eff.reference_upstream_url),
            "total_records": total,
            "baseline_ready": total >= eff.baseline_min_samples,
            "baseline_min_samples": eff.baseline_min_samples,
            "analysis_mode": eff.analysis_mode,
            "alert_system_notify": prefs.alert_system_notify,
            "alert_webhook": prefs.alert_webhook,
            "webhook_url": prefs.webhook_url,
            "alert_min_risk": prefs.alert_min_risk,
            "proxy_url": f"http://{eff.host}:{eff.port}/v1",
            "dashboard_url": f"http://{eff.host}:{eff.port}/dashboard",
        }

    @app.put("/api/dashboard/settings")
    async def update_settings(body: UserSettingsUpdate) -> dict[str, Any]:
        prefs = user_store.load()
        data = body.model_dump(exclude_none=True)
        for key, value in data.items():
            setattr(prefs, key, value)
        user_store.save(prefs)
        return {"ok": True, "settings": prefs.to_dict()}

    @app.get("/api/dashboard/stats")
    async def dashboard_stats() -> dict[str, Any]:
        records = logger.fetch_recent(limit=200)
        eff = _effective_settings()
        return {
            "total_records": logger.count(),
            "recent_count": len(records),
            "analysis_mode": eff.analysis_mode,
            "baselines": [
                {
                    "model_key": p.model_key,
                    "sample_count": p.sample_count,
                    "dynamic_threshold": p.dynamic_threshold,
                    "ttft_mean_ms": p.ttft_mean_ms,
                    "itt_mean_ms": p.itt_mean_ms,
                    "avg_logprob": p.avg_logprob,
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
                    "upstream_kind": r.metadata.get("upstream_kind"),
                    "text_preview": (r.response_text or "")[:120],
                    "ttft_ms": r.timing.ttft_ms,
                    "total_ms": r.timing.total_ms,
                    "itt_count": len(r.timing.itts_ms),
                    "has_logprobs": r.logprobs_stats is not None,
                }
                for r in records
            ]
        }

    @app.post("/api/ingest")
    async def api_ingest(payload: IngestPayload) -> dict[str, Any]:
        try:
            rid = ingest_record(logger, payload)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return {"ok": True, "record_id": rid}

    @app.post("/api/dashboard/analyze")
    async def dashboard_analyze(
        format: str = "json",
        notify: bool = True,
    ) -> Any:
        records = logger.fetch_all()
        if not records:
            return JSONResponse({"error": "no_records"}, status_code=400)

        eff = _effective_settings()
        analyzer = analyzer_from_settings(eff, load_user_prefs=False)
        try:
            report = analyzer.analyze_records(records)
        except RuntimeError as exc:
            return JSONResponse({"error": str(exc)}, status_code=503)

        notify_result = None
        if notify:
            prefs = user_store.load()
            notify_result = dispatch_report_alerts(report, prefs)
            notify_payload = {
                "system_sent": notify_result.system_sent,
                "webhook_sent": notify_result.webhook_sent,
                "skipped": notify_result.skipped,
                "errors": notify_result.errors,
            }
        else:
            notify_payload = None

        if format == "html":
            return HTMLResponse(render_html_report(report))
        if format == "markdown":
            return JSONResponse({"markdown": render_markdown_report(report)})
        if format == "json":
            payload = json.loads(render_json_report(report))
            payload["notifications"] = notify_payload
            return JSONResponse(payload)

        return {
            "total_records": report.total_records,
            "analyzed_records": report.analyzed_records,
            "alert_count": len(report.alerts),
            "baselines_updated": report.baselines_updated,
            "alerts_suppressed_by_smoothing": report.alerts_suppressed_by_smoothing,
            "analysis_mode": eff.analysis_mode,
            "notifications": notify_payload,
            "alerts": [
                {
                    "record_id": a.record_id,
                    "timestamp": a.timestamp,
                    "model_requested": a.model_requested,
                    "expected_family": a.expected_family,
                    "predicted_family": a.predicted_family,
                    "risk_level": a.risk_level,
                    "raw_risk_level": a.raw_risk_level,
                    "fusion_score": a.fusion_score,
                    "evidence": a.evidence,
                }
                for a in report.alerts
            ],
            "summary_by_family": report.summary_by_family,
        }
