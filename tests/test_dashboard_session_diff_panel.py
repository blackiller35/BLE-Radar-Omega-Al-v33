from ble_radar import dashboard, reports


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
    {
        "name": "Tracker-Two",
        "address": "AA:BB:CC:DD:EE:02",
        "vendor": "TrackCorp",
        "profile": "tracker_like",
        "rssi": -58,
        "risk_score": 14,
        "follow_score": 8,
        "confidence_score": 31,
        "final_score": 44,
        "alert_level": "moyen",
        "seen_count": 2,
        "reason_short": "tracker",
        "flags": ["follow"],
        "watch_hit": False,
        "possible_suivi": True,
    },
]


def test_dashboard_contains_session_diff_panel(monkeypatch):
    monkeypatch.setattr(dashboard, "load_scan_history", lambda: [])
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [("TestVendor", 1), ("TrackCorp", 1)])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: [devices[1]])
    monkeypatch.setattr(dashboard, "list_cases", lambda: [])
    monkeypatch.setattr(
        dashboard,
        "latest_session_diff",
        lambda: {
            "has_diff": True,
            "previous_stamp": "2026-04-17_19-00-00",
            "current_stamp": "2026-04-17_19-05-00",
            "device_count_delta": 2,
            "critical_delta": 1,
            "watch_hits_delta": 1,
            "tracker_candidates_delta": 1,
            "previous_top_vendor": "VendorA",
            "current_top_vendor": "VendorB",
            "previous_top_device": "Device-A",
            "current_top_device": "Device-B",
        },
    )

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-17_19-20-00")

    assert "Session diff récent" in html
    assert "Previous: 2026-04-17_19-00-00" in html
    assert "Current: 2026-04-17_19-05-00" in html
    assert "Devices delta: 2" in html
    assert "Top vendor: VendorA -> VendorB" in html


def test_dashboard_handles_missing_session_diff(monkeypatch):
    monkeypatch.setattr(dashboard, "load_scan_history", lambda: [])
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [("TestVendor", 1), ("TrackCorp", 1)])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: [devices[1]])
    monkeypatch.setattr(dashboard, "list_cases", lambda: [])
    monkeypatch.setattr(dashboard, "latest_session_diff", lambda: {"has_diff": False})

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-17_19-21-00")

    assert "Session diff récent" in html
    assert "Aucun diff comparable disponible" in html


def test_save_html_keeps_session_diff_panel(monkeypatch, tmp_path):
    monkeypatch.setattr(reports, "REPORTS_DIR", tmp_path / "reports")
    reports.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(dashboard, "load_scan_history", lambda: [])
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [("TestVendor", 1), ("TrackCorp", 1)])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: [devices[1]])
    monkeypatch.setattr(dashboard, "list_cases", lambda: [])
    monkeypatch.setattr(
        dashboard,
        "latest_session_diff",
        lambda: {
            "has_diff": True,
            "previous_stamp": "2026-04-17_19-10-00",
            "current_stamp": "2026-04-17_19-11-00",
            "device_count_delta": 1,
            "critical_delta": 1,
            "watch_hits_delta": 0,
            "tracker_candidates_delta": 1,
            "previous_top_vendor": "VendorA",
            "current_top_vendor": "VendorB",
            "previous_top_device": "Device-A",
            "current_top_device": "Device-B",
        },
    )

    path = reports.save_html(SAMPLE_DEVICES, "2026-04-17_19-22-00")
    text = path.read_text(encoding="utf-8")

    assert "Session diff récent" in text
    assert "Devices delta: 1" in text


def test_readme_mentions_dashboard_session_diff():
    text = open("README.md", "r", encoding="utf-8").read()

    assert "## Dashboard session diff" in text
    assert "Session diff récent" in text


def test_project_status_mentions_v045():
    text = open("PROJECT_STATUS.md", "r", encoding="utf-8").read()

    assert "v0.4.5 : panneau session diff dans le dashboard" in text


def test_changelog_mentions_v045():
    text = open("CHANGELOG.md", "r", encoding="utf-8").read()

    assert "## v0.4.5" in text
    assert "Session diff récent".lower()[:12] in text.lower() or "dashboard html" in text.lower()
