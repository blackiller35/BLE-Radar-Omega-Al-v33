from ble_radar import app


def test_prof_scan_seconds_uses_runtime_config_fallback(monkeypatch):
    monkeypatch.setattr(app, "active_profile", lambda: {})
    monkeypatch.setattr(app, "load_runtime_config", lambda: {
        "scan_timeout": 9,
        "live_scan_timeout": 4,
    })

    assert app.prof_scan_seconds() == 9


def test_prof_live_seconds_uses_runtime_config_fallback(monkeypatch):
    monkeypatch.setattr(app, "active_profile", lambda: {})
    monkeypatch.setattr(app, "load_runtime_config", lambda: {
        "scan_timeout": 9,
        "live_scan_timeout": 6,
    })

    assert app.prof_live_seconds() == 6


def test_profile_values_override_runtime_config(monkeypatch):
    monkeypatch.setattr(app, "active_profile", lambda: {
        "scan_seconds": 12,
        "live_seconds": 7,
    })
    monkeypatch.setattr(app, "load_runtime_config", lambda: {
        "scan_timeout": 5,
        "live_scan_timeout": 3,
    })

    assert app.prof_scan_seconds() == 12
    assert app.prof_live_seconds() == 7
