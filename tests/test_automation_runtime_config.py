import json

from ble_radar import automation


def test_load_automation_config_returns_defaults_when_file_missing(monkeypatch, tmp_path):
    missing_path = tmp_path / "automation.json"

    monkeypatch.setattr(automation, "AUTOMATION_FILE", missing_path)
    monkeypatch.setattr(
        automation,
        "DEFAULT_AUTOMATION",
        {
            "enabled": True,
            "rules": [
                {
                    "id": "watch_hit_audit",
                    "threshold": 1,
                    "action": "export_audit",
                }
            ],
        },
    )

    data = automation.load_automation_config()

    assert data["enabled"] is True
    assert isinstance(data["rules"], list)
    assert data["rules"][0]["id"] == "watch_hit_audit"


def test_load_automation_config_applies_file_override(monkeypatch, tmp_path):
    cfg_path = tmp_path / "automation.json"
    cfg_path.write_text(json.dumps({"enabled": False}), encoding="utf-8")

    monkeypatch.setattr(automation, "AUTOMATION_FILE", cfg_path)
    monkeypatch.setattr(
        automation,
        "DEFAULT_AUTOMATION",
        {
            "enabled": True,
            "rules": [
                {
                    "id": "watch_hit_audit",
                    "threshold": 1,
                    "action": "export_audit",
                }
            ],
        },
    )

    data = automation.load_automation_config()

    assert data["enabled"] is False
    assert isinstance(data["rules"], list)
    assert data["rules"][0]["id"] == "watch_hit_audit"
