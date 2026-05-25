"""Persistent user settings (onboarding, alerts, analysis mode)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass
class UserSettings:
    onboarding_completed: bool = False
    upstream_url: str = ""
    reference_upstream_url: str = ""
    analysis_mode: str = "lite"  # lite | precise
    alert_system_notify: bool = True
    alert_webhook: bool = False
    webhook_url: str = ""
    alert_min_risk: str = "high"  # notify for this level and above: medium, high

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> UserSettings:
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


class UserSettingsStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> UserSettings:
        if not self.path.is_file():
            return UserSettings()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return UserSettings()
        if not isinstance(data, dict):
            return UserSettings()
        return UserSettings.from_dict(data)

    def save(self, settings: UserSettings) -> None:
        self.path.write_text(
            json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def settings_path_for_db(db_path: Path) -> Path:
    return db_path.parent / "user-settings.json"
