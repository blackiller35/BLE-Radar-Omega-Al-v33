from ble_radar import dashboard


SAMPLE_DEVICES = [
    {
        "name": "Beacon-One",
        "address": "AA:BB:CC:DD:EE:01",
        "vendor": "TestVendor",
        "profile": "general_ble",
        "rssi": -41,
        "risk_score": 20,
        "follow_score": 5,
        "confidence_score": 55,
        "final_score": 72,
        "alert_level": "critique",
        "seen_count": 4,
        "reason_short": "watch_hit",
        "flags": ["watch"],
        "watch_hit": True,
    },
]


def test_dashboard_html_contains_device_registry_snapshot(monkeypatch):
    monkeypatch.setattr(dashboard, "load_scan_history", lambda: [])
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [("TestVendor", 1)])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: devices)
    monkeypatch.setattr(
        dashboard,
        "load_registry",
        lambda: {
            "AA:BB:CC:DD:EE:01": {
                "address": "AA:BB:CC:DD:EE:01",
                "first_seen": "2026-04-18 10:00:00",
                "last_seen": "2026-04-18 10:10:00",
                "seen_count": 7,
                "session_count": 2,
            }
        },
    )

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-18_10-30-00")

    assert "Device registry snapshot" in html
    assert "first_seen=2026-04-18 10:00:00" in html
    assert "last_seen=2026-04-18 10:10:00" in html
    assert "seen_count=7" in html
    assert "session_count=2" in html
