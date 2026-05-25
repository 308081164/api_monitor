"""Historical alert smoothing to reduce isolated false positives."""

from __future__ import annotations

from collections import defaultdict, deque


class AlertSmoother:
    """Require sustained drift before escalating to medium/high alerts."""

    def __init__(self, window: int = 3) -> None:
        self.window = max(1, window)
        self._history: dict[str, deque[str]] = defaultdict(
            lambda: deque(maxlen=self.window)
        )

    def smooth(self, model_key: str, raw_risk: str) -> str:
        history = self._history[model_key]
        history.append(raw_risk)
        hist = list(history)

        if raw_risk == "high":
            high_count = sum(1 for r in hist if r == "high")
            if high_count >= 2 or len(hist) >= self.window:
                return "high"
            return "medium"

        if raw_risk == "medium":
            elevated = sum(1 for r in hist if r in {"medium", "high"})
            if elevated >= self.window:
                return "medium"
            return "low"

        return "low"
