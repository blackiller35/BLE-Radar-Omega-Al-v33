import json

from ble_radar import session_diff_report


def test_build_latest_session_diff_report_uses_latest_diff(monkeypatch):
    monkeypatch.setattr(
        session_diff_report,
        "latest_session_diff",
        lambda root=None: {
            "has_diff": True,
            "previous_stamp": "2026-04-17_19-00-00",
            "current_stamp": "2026-04-17_19-05-00",
            "device_count_delta": 2,
            "critical_delta": 1,
            "high_delta": 0,
            "medium_delta": 1,
            "low_delta": 0,
            "watch_hits_delta": 1,
            "tracker_candidates_delta": 1,
            "previous_top_vendor": "VendorA",
            "current_top_vendor": "VendorB",
            "previous_top_device": "Device-A",
            "current_top_device": "Device-B",
        },
    )
    monkeypatch.setattr(
        session_diff_report,
        "summary_lines",
        lambda diff: ["BLE Radar Omega AI - Session Diff", "Device delta: 2"],
    )

    payload = session_diff_report.build_latest_session_diff_report()

    assert payload["has_diff"] is True
    assert payload["diff"]["device_count_delta"] == 2
    assert payload["lines"][0] == "BLE Radar Omega AI - Session Diff"


def test_save_latest_session_diff_report_writes_json_and_md(monkeypatch, tmp_path):
    monkeypatch.setattr(
        session_diff_report,
        "build_latest_session_diff_report",
        lambda root_manifests=None: {
            "stamp": "2026-04-17_19-20-00",
            "has_diff": True,
            "diff": {"device_count_delta": 3},
            "lines": ["BLE Radar Omega AI - Session Diff", "Device delta: 3"],
        },
    )

    result = session_diff_report.save_latest_session_diff_report(output_root=tmp_path)

    assert result["json_path"].exists()
    assert result["md_path"].exists()

    payload = json.loads(result["json_path"].read_text(encoding="utf-8"))
    text = result["md_path"].read_text(encoding="utf-8")

    assert payload["diff"]["device_count_delta"] == 3
    assert "Device delta: 3" in text


def test_save_latest_session_diff_report_handles_no_diff(monkeypatch, tmp_path):
    monkeypatch.setattr(
        session_diff_report,
        "build_latest_session_diff_report",
        lambda root_manifests=None: {
            "stamp": "2026-04-17_19-21-00",
            "has_diff": False,
            "diff": {"has_diff": False},
            "lines": ["BLE Radar Omega AI - Session Diff", "No comparable sessions available."],
        },
    )

    result = session_diff_report.save_latest_session_diff_report(output_root=tmp_path)
    text = result["md_path"].read_text(encoding="utf-8")

    assert "No comparable sessions available." in text


def test_list_session_diff_reports_returns_latest_first(tmp_path):
    a = tmp_path / "session_diff_2026-04-17_19-22-00.md"
    b = tmp_path / "session_diff_2026-04-17_19-23-00.json"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")

    items = session_diff_report.list_session_diff_reports(root=tmp_path)

    assert items[0].name == "session_diff_2026-04-17_19-23-00.json"
    assert items[1].name == "session_diff_2026-04-17_19-22-00.md"


def test_list_session_diff_reports_returns_empty_when_missing(tmp_path):
    items = session_diff_report.list_session_diff_reports(root=tmp_path / "missing")
    assert items == []


def test_build_latest_session_diff_report_keeps_summary_lines(monkeypatch):
    monkeypatch.setattr(
        session_diff_report,
        "latest_session_diff",
        lambda root=None: {"has_diff": False},
    )
    monkeypatch.setattr(
        session_diff_report,
        "summary_lines",
        lambda diff: ["BLE Radar Omega AI - Session Diff", "No comparable sessions available."],
    )

    payload = session_diff_report.build_latest_session_diff_report()

    assert payload["has_diff"] is False
    assert payload["lines"][-1] == "No comparable sessions available."
