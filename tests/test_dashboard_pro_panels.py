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


def test_dashboard_contains_new_pro_panels(monkeypatch):
    monkeypatch.setattr(
        dashboard,
        "load_scan_history",
        lambda: [{"stamp": "2026-04-17_15-40-00", "count": 5, "critical": 1, "high": 1, "medium": 2}],
    )
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [("TestVendor", 1), ("TrackCorp", 1)])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: [devices[1]])
    monkeypatch.setattr(
        dashboard,
        "list_cases",
        lambda: [{"title": "Tracker suspect", "status": "watch", "updated_at": "2026-04-17T15:39:00"}],
    )

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-17_15-41-00")

    assert "Dashboard Pro" in html
    assert "Résumé comparatif" in html
    assert "Incidents visibles" in html
    assert "Cas d'investigation récents" in html
    assert "Tracker suspect" in html
    assert "status=watch" in html


def test_dashboard_contains_useful_filters(monkeypatch):
    monkeypatch.setattr(dashboard, "load_scan_history", lambda: [])
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [("TestVendor", 1), ("TrackCorp", 1)])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: [devices[1]])
    monkeypatch.setattr(dashboard, "list_cases", lambda: [])

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-17_15-42-00")

    assert 'id="vendorSelect"' in html
    assert "Watch hits" in html
    assert "Trackers" in html
    assert "data-watch=" in html
    assert "data-tracker=" in html


def test_dashboard_comparison_mentions_previous_scan(monkeypatch):
    monkeypatch.setattr(
        dashboard,
        "load_scan_history",
        lambda: [{"stamp": "2026-04-17_15-43-00", "count": 1, "critical": 0, "high": 0, "medium": 1}],
    )
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [("TestVendor", 1), ("TrackCorp", 1)])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: [devices[1]])
    monkeypatch.setattr(dashboard, "list_cases", lambda: [])

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-17_15-44-00")

    assert "vs précédent" in html
    assert "Total: 2 (+1 vs précédent)" in html


def test_save_html_contains_recent_cases_panel(monkeypatch, tmp_path):
    monkeypatch.setattr(reports, "REPORTS_DIR", tmp_path / "reports")
    reports.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(dashboard, "load_scan_history", lambda: [])
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [("TestVendor", 1), ("TrackCorp", 1)])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: [devices[1]])
    monkeypatch.setattr(
        dashboard,
        "list_cases",
        lambda: [{"title": "Beacon check", "status": "open", "updated_at": "2026-04-17T15:45:00"}],
    )

    path = reports.save_html(SAMPLE_DEVICES, "2026-04-17_15-45-00")
    text = path.read_text(encoding="utf-8")

    assert "Cas d'investigation récents" in text
    assert "Beacon check" in text
