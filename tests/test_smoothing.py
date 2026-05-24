from api_monitor.analyzer.smoothing import AlertSmoother


def test_isolated_high_downgraded():
    s = AlertSmoother(window=3)
    assert s.smooth("gpt-4o", "high") == "medium"
    assert s.smooth("gpt-4o", "high") == "high"


def test_sustained_medium_escalates():
    s = AlertSmoother(window=3)
    assert s.smooth("claude", "medium") == "low"
    assert s.smooth("claude", "medium") == "low"
    assert s.smooth("claude", "medium") == "medium"
