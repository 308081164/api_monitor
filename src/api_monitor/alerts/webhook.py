"""Webhook alert delivery."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from api_monitor.models import AnalysisRow

logger = logging.getLogger(__name__)


def send_webhook_alert(
    url: str,
    *,
    alert: AnalysisRow,
    report_summary: dict[str, Any] | None = None,
    timeout: float = 15.0,
) -> bool:
    if not url.strip():
        return False
    payload = {
        "source": "api-monitor",
        "risk_level": alert.risk_level,
        "record_id": alert.record_id,
        "timestamp": alert.timestamp,
        "model_requested": alert.model_requested,
        "expected_family": alert.expected_family,
        "predicted_family": alert.predicted_family,
        "fusion_score": alert.fusion_score,
        "evidence": alert.evidence,
        "summary": report_summary or {},
        "text": _format_text(alert),
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        if resp.status_code >= 400:
            logger.warning("webhook returned %s", resp.status_code)
            return False
        return True
    except httpx.HTTPError as exc:
        logger.warning("webhook failed: %s", exc)
        return False


def _format_text(alert: AnalysisRow) -> str:
    lines = [
        f"[{alert.risk_level.upper()}] API Monitor 模型漂移告警",
        f"模型: {alert.model_requested or 'n/a'}",
        f"预测家族: {alert.predicted_family} (声称: {alert.expected_family or '?'})",
        f"融合分: {alert.fusion_score}",
    ]
    for item in alert.evidence[:5]:
        lines.append(f"- {item}")
    return "\n".join(lines)
