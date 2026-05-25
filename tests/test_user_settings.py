from pathlib import Path

from api_monitor.storage.user_settings import UserSettings, UserSettingsStore


def test_user_settings_roundtrip(tmp_path: Path):
    path = tmp_path / "user-settings.json"
    store = UserSettingsStore(path)
    store.save(
        UserSettings(
            onboarding_completed=True,
            upstream_url="https://relay.example.com",
            analysis_mode="precise",
            alert_system_notify=True,
        )
    )
    loaded = store.load()
    assert loaded.onboarding_completed
    assert loaded.upstream_url == "https://relay.example.com"
    assert loaded.analysis_mode == "precise"
