import csv

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


def test_dashboard_html_contains_explanation_column(monkeypatch):
    monkeypatch.setattr(dashboard, "load_scan_history", lambda: [])
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [("TestVendor", 1), ("TrackCorp", 1)])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: [devices[1]])

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-17_15-30-00")

    assert "Explication" in html
    assert "risk=20" in html
    assert "follow=5" in html
    assert "confidence=55" in html
    assert "final=72" in html
    assert "reason=watch_hit" in html


def test_save_csv_contains_score_explanation(monkeypatch, tmp_path):
    monkeypatch.setattr(reports, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(reports, "HISTORY_DIR", tmp_path / "history")
    reports.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    reports.HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    path = reports.save_csv(SAMPLE_DEVICES, "2026-04-17_15-30-01")

    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    assert "score_explanation" in rows[0]
    assert any("reason=watch_hit" in cell for cell in rows[1])
    assert any("final=72" in cell for cell in rows[1])


def test_save_txt_contains_explanation_summary(monkeypatch, tmp_path):
    monkeypatch.setattr(reports, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(reports, "HISTORY_DIR", tmp_path / "history")
    reports.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    reports.HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    path = reports.save_txt(SAMPLE_DEVICES, "2026-04-17_15-30-02")
    text = path.read_text(encoding="utf-8")

    assert "explication:risk=20" in text
    assert "follow=5" in text
    assert "confidence=55" in text
    assert "final=72" in text
    assert "reason=watch_hit" in text


def test_save_html_contains_explanation_summary(monkeypatch, tmp_path):
    monkeypatch.setattr(reports, "REPORTS_DIR", tmp_path / "reports")
    reports.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(dashboard, "load_scan_history", lambda: [])
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [("TestVendor", 1), ("TrackCorp", 1)])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: [devices[1]])

    path = reports.save_html(SAMPLE_DEVICES, "2026-04-17_15-30-03")
    text = path.read_text(encoding="utf-8")

    assert "Explication" in text
    assert "reason=watch_hit" in text
