from unittest.mock import patch

from api_monitor.alerts.dispatcher import AlertDispatcher
from api_monitor.models import AnalysisReport, AnalysisRow
from api_monitor.storage.user_settings import UserSettings


def _alert(risk: str) -> AnalysisRow:
    return AnalysisRow(
        record_id=1,
        timestamp="2026-05-24T00:00:00+00:00",
        model_requested="gpt-4o",
        expected_family="gpt",
        predicted_family="claude",
        confidence=0.9,
        drift_score=0.3,
        risk_level=risk,
        evidence=["test"],
        fusion_score=0.7,
    )


def test_dispatcher_sends_for_high_only():
    prefs = UserSettings(alert_system_notify=True, alert_min_risk="high")
    report = AnalysisReport(
        total_records=10,
        analyzed_records=10,
        alerts=[_alert("high"), _alert("medium")],
    )
    with patch("api_monitor.alerts.dispatcher.send_system_notification", return_value=True):
        result = AlertDispatcher(prefs).dispatch_report(report)
    assert result.system_sent == 1
    assert result.skipped == 1


def test_should_notify_medium_when_configured():
    d = AlertDispatcher(UserSettings(alert_min_risk="medium"))
    assert d.should_notify(_alert("medium"))
    assert not d.should_notify(_alert("low"))
