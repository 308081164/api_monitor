"""Dispatch analysis alerts to configured channels."""

from __future__ import annotations

from dataclasses import dataclass, field

from api_monitor.alerts.system_notify import send_system_notification
from api_monitor.alerts.webhook import send_webhook_alert
from api_monitor.models import AnalysisReport, AnalysisRow
from api_monitor.storage.user_settings import UserSettings

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


@dataclass
class AlertDispatchResult:
    system_sent: int = 0
    webhook_sent: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


class AlertDispatcher:
    def __init__(self, settings: UserSettings) -> None:
        self.settings = settings
        self._min_level = _RISK_ORDER.get(settings.alert_min_risk, 2)

    def should_notify(self, alert: AnalysisRow) -> bool:
        return _RISK_ORDER.get(alert.risk_level, 0) >= self._min_level

    def dispatch_report(self, report: AnalysisReport) -> AlertDispatchResult:
        result = AlertDispatchResult()
        summary = {
            "total_records": report.total_records,
            "alert_count": len(report.alerts),
            "analyzed_records": report.analyzed_records,
        }
        for alert in report.alerts:
            if not self.should_notify(alert):
                result.skipped += 1
                continue
            if self.settings.alert_system_notify:
                ok = send_system_notification(
                    title=self._title(alert),
                    message=self._body(alert),
                )
                if ok:
                    result.system_sent += 1
                else:
                    result.errors.append(f"system notify failed for #{alert.record_id}")
            if self.settings.alert_webhook and self.settings.webhook_url:
                ok = send_webhook_alert(
                    self.settings.webhook_url,
                    alert=alert,
                    report_summary=summary,
                )
                if ok:
                    result.webhook_sent += 1
                else:
                    result.errors.append(f"webhook failed for #{alert.record_id}")
        return result

    @staticmethod
    def _title(alert: AnalysisRow) -> str:
        prefix = "⚠️" if alert.risk_level == "high" else "API Monitor"
        return f"{prefix} 模型漂移 · {alert.model_requested or 'unknown'}"

    @staticmethod
    def _body(alert: AnalysisRow) -> str:
        parts = [
            f"{alert.expected_family or '?'} → {alert.predicted_family}",
            f"融合分 {alert.fusion_score}",
        ]
        if alert.evidence:
            parts.append(str(alert.evidence[0])[:120])
        return " | ".join(parts)


def dispatch_report_alerts(
    report: AnalysisReport,
    user_settings: UserSettings,
) -> AlertDispatchResult:
    return AlertDispatcher(user_settings).dispatch_report(report)
