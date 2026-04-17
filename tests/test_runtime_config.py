import json

from ble_radar import config


def test_runtime_config_merges_example_and_local(monkeypatch, tmp_path):
    example_path = tmp_path / "config.example.json"
    runtime_path = tmp_path / "config.json"

    example_path.write_text(
        json.dumps(
            {
                "scan_timeout": 8,
                "live_scan_timeout": 4,
                "aegis": {"priority_high": 77},
                "automation": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    runtime_path.write_text(
        json.dumps(
            {
                "scan_timeout": 11,
                "aegis": {"priority_critical": 91},
                "ui": {"theme": "neo"},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "EXAMPLE_CONFIG_FILE", example_path)
    monkeypatch.setattr(config, "RUNTIME_CONFIG_FILE", runtime_path)

    data = config.load_runtime_config()

    assert data["scan_timeout"] == 11
    assert data["live_scan_timeout"] == 4
    assert data["aegis"]["priority_high"] == 77
    assert data["aegis"]["priority_critical"] == 91
    assert data["automation"]["enabled"] is False
    assert data["ui"]["theme"] == "neo"


def test_get_runtime_section_returns_defaults_when_files_missing(monkeypatch, tmp_path):
    example_path = tmp_path / "missing.example.json"
    runtime_path = tmp_path / "missing.json"

    monkeypatch.setattr(config, "EXAMPLE_CONFIG_FILE", example_path)
    monkeypatch.setattr(config, "RUNTIME_CONFIG_FILE", runtime_path)

    aegis_cfg = config.get_runtime_section("aegis")

    assert isinstance(aegis_cfg, dict)
    assert aegis_cfg["priority_high"] == 70
    assert aegis_cfg["priority_critical"] == 85
