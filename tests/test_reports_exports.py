import csv
import json

from ble_radar import reports


SAMPLE_DEVICES = [
    {
        "address": "AA:BB:CC:DD:EE:01",
        "name": "Beacon-One",
        "vendor": "TestVendor",
        "rssi": -41,
        "company": "TestCo",
        "type": "beacon",
        "profile": "general_ble",
        "watch_hit": False,
        "whitelisted": False,
        "priority": 22,
        "risk_score": 22,
        "final_score": 22,
        "alert_level": "faible",
    },
    {
        "address": "AA:BB:CC:DD:EE:02",
        "name": "Tracker-Two",
        "vendor": "TrackCorp",
        "rssi": -58,
        "company": "TrackCorp",
        "type": "tracker",
        "profile": "tracker_like",
        "watch_hit": True,
        "whitelisted": False,
        "priority": 88,
        "risk_score": 88,
        "final_score": 88,
        "alert_level": "critique",
        "possible_suivi": True,
        "reason_short": "tracking probable",
    },
]


def test_save_json_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(reports, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(reports, "HISTORY_DIR", tmp_path / "history")
    reports.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    reports.HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    path = reports.save_json(SAMPLE_DEVICES, "2026-04-17_14-10-00")

    assert path.name == "scan_2026-04-17_14-10-00.json"
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    assert loaded[0]["address"] == "AA:BB:CC:DD:EE:01"
    assert loaded[1]["watch_hit"] is True


def test_save_csv_has_expected_header_and_rows(monkeypatch, tmp_path):
    monkeypatch.setattr(reports, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(reports, "HISTORY_DIR", tmp_path / "history")
    reports.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    reports.HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    path = reports.save_csv(SAMPLE_DEVICES, "2026-04-17_14-10-01")

    assert path.name == "scan_2026-04-17_14-10-01.csv"

    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    assert len(rows) >= 3
    assert "address" in rows[0]
    assert "name" in rows[0]
    assert "risk_score" in rows[0]
    assert "AA:BB:CC:DD:EE:01" in rows[1]
    assert "AA:BB:CC:DD:EE:02" in rows[2]


def test_build_operator_panel_events_uses_real_device_data():
    events = reports.build_operator_panel_events(SAMPLE_DEVICES)

    assert len(events) >= 1
    assert any("Tracker-Two" in event["title"] for event in events)
    assert any(event["severity"] in {"high", "critical"} for event in events)


def test_save_all_reports_returns_expected_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(reports, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(reports, "HISTORY_DIR", tmp_path / "history")
    reports.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    reports.HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(reports, "now_stamp", lambda: "2026-04-17_14-10-02", raising=False)

    result = reports.save_all_reports(SAMPLE_DEVICES)

    assert set(result.keys()) >= {"json", "csv", "txt", "html", "operator_panel_html", "summary"}
    assert result["json"].name == "scan_2026-04-17_14-10-02.json"
    assert result["csv"].name == "scan_2026-04-17_14-10-02.csv"
    assert result["txt"].name == "scan_2026-04-17_14-10-02.txt"
    assert result["html"].name == "scan_2026-04-17_14-10-02.html"
    assert result["operator_panel_html"].name == "operator_panel_2026-04-17_14-10-02.html"
    assert result["summary"].name == "executive_summary_2026-04-17_14-10-02.json"

    for key in ("json", "csv", "txt", "html", "operator_panel_html", "summary"):
        assert result[key].exists()


def test_save_all_reports_summary_is_valid_json(monkeypatch, tmp_path):
    monkeypatch.setattr(reports, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(reports, "HISTORY_DIR", tmp_path / "history")
    reports.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    reports.HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(reports, "now_stamp", lambda: "2026-04-17_14-10-03", raising=False)

    result = reports.save_all_reports(SAMPLE_DEVICES)
    summary = json.loads(result["summary"].read_text(encoding="utf-8"))

    assert isinstance(summary, dict)
    assert summary["stamp"] == "2026-04-17_14-10-03"
    assert "top_hot" in summary
    assert "critical" in summary
    assert "high" in summary


def test_save_operator_panel_html_contains_live_devices(monkeypatch, tmp_path):
    monkeypatch.setattr(reports, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(reports, "HISTORY_DIR", tmp_path / "history")
    reports.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    reports.HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    path = reports.save_operator_panel_html(SAMPLE_DEVICES, "2026-04-17_14-10-04")
    html = path.read_text(encoding="utf-8")

    assert path.name == "operator_panel_2026-04-17_14-10-04.html"
    assert "Beacon-One" in html
    assert "Tracker-Two" in html
    assert "window.BleRadarOmegaUI" in html
