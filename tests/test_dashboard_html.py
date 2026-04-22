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
    },
]


def test_render_dashboard_html_contains_main_sections(monkeypatch):
    monkeypatch.setattr(
        dashboard,
        "load_scan_history",
        lambda: [{"stamp": "2026-04-17_14-20-00", "count": 2, "critical": 1, "high": 0, "medium": 1}],
    )
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [("TestVendor", 1), ("TrackCorp", 1)])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: [devices[1]])

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-17_14-21-00")

    assert "BLE Radar Omega AI - Dashboard" in html
    assert "Résumé global" in html
    assert "Watchlist Hits" in html
    assert "Top trackers probables" in html
    assert "Répartition vendors" in html
    assert "Filtres rapides" in html
    assert "Tendance des derniers scans" in html
    assert "Tableau détaillé des appareils" in html
    assert "Horodatage : 2026-04-17_14-21-00" in html
    assert 'id="searchBox"' in html
    assert 'id="deviceTable"' in html
    assert "Beacon-One" in html
    assert "Tracker-Two" in html


def test_render_dashboard_html_marks_alert_rows(monkeypatch):
    monkeypatch.setattr(dashboard, "load_scan_history", lambda: [])
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: [])

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-17_14-22-00")

    assert 'tr class="critical"' in html
    assert 'tr class="medium"' in html
    assert 'data-alert="critique"' in html
    assert 'data-alert="moyen"' in html


def test_save_html_writes_dashboard_file(monkeypatch, tmp_path):
    monkeypatch.setattr(reports, "REPORTS_DIR", tmp_path / "reports")
    reports.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(reports, "render_dashboard_html", lambda devices, stamp: "<html>OK DASH</html>")

    path = reports.save_html(SAMPLE_DEVICES, "2026-04-17_14-23-00")

    assert path.name == "scan_2026-04-17_14-23-00.html"
    assert path.read_text(encoding="utf-8") == "<html>OK DASH</html>"
