from ble_radar import incident_pack, investigation


def _latest_session():
    return {
        "stamp": "2026-04-17_20-10-00",
        "device_count": 5,
        "critical": 1,
        "high": 1,
        "medium": 2,
        "low": 1,
        "watch_hits": 1,
        "tracker_candidates": 2,
        "top_vendor": "TestVendor",
        "top_vendor_count": 2,
        "top_device_name": "Beacon-One",
        "top_device_score": 72,
        "top_device_alert": "critique",
    }


def _recent_sessions():
    return [
        {
            "stamp": "2026-04-17_20-10-00",
            "device_count": 5,
            "critical": 1,
            "watch_hits": 1,
            "tracker_candidates": 2,
            "top_vendor": "TestVendor",
        },
        {
            "stamp": "2026-04-17_20-05-00",
            "device_count": 3,
            "critical": 0,
            "watch_hits": 0,
            "tracker_candidates": 1,
            "top_vendor": "TrackCorp",
        },
    ]


def test_incident_pack_manifest_contains_session_catalog_context(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")
    monkeypatch.setattr(incident_pack, "INCIDENT_PACKS_DIR", tmp_path / "incident_packs")
    monkeypatch.setattr(incident_pack, "latest_session_diff", lambda: {"has_diff": False})
    monkeypatch.setattr(incident_pack, "latest_session_overview", _latest_session)
    monkeypatch.setattr(incident_pack, "build_session_catalog", lambda limit=3: _recent_sessions())
    monkeypatch.setattr(incident_pack, "diff_summary_lines", lambda diff: ["BLE Radar Omega AI - Session Diff"])

    case = investigation.create_case("Tracker suspect")
    result = incident_pack.build_incident_pack(case["id"])

    assert result["manifest"]["session_overview"]["stamp"] == "2026-04-17_20-10-00"
    assert len(result["manifest"]["recent_sessions"]) == 2
    assert result["manifest"]["recent_sessions"][0]["top_vendor"] == "TestVendor"


def test_incident_summary_mentions_latest_session_overview(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")
    monkeypatch.setattr(incident_pack, "INCIDENT_PACKS_DIR", tmp_path / "incident_packs")
    monkeypatch.setattr(incident_pack, "latest_session_diff", lambda: {"has_diff": False})
    monkeypatch.setattr(incident_pack, "latest_session_overview", _latest_session)
    monkeypatch.setattr(incident_pack, "build_session_catalog", lambda limit=3: _recent_sessions())
    monkeypatch.setattr(incident_pack, "diff_summary_lines", lambda diff: ["BLE Radar Omega AI - Session Diff"])

    case = investigation.create_case("Beacon check")
    result = incident_pack.build_incident_pack(case["id"])
    text = result["summary_path"].read_text(encoding="utf-8")

    assert "Latest session overview:" in text
    assert "Stamp: 2026-04-17_20-10-00" in text
    assert "Top vendor: TestVendor" in text
    assert "Top device: Beacon-One (72)" in text


def test_incident_summary_mentions_recent_sessions(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")
    monkeypatch.setattr(incident_pack, "INCIDENT_PACKS_DIR", tmp_path / "incident_packs")
    monkeypatch.setattr(incident_pack, "latest_session_diff", lambda: {"has_diff": False})
    monkeypatch.setattr(incident_pack, "latest_session_overview", _latest_session)
    monkeypatch.setattr(incident_pack, "build_session_catalog", lambda limit=3: _recent_sessions())
    monkeypatch.setattr(incident_pack, "diff_summary_lines", lambda diff: ["BLE Radar Omega AI - Session Diff"])

    case = investigation.create_case("Session context")
    result = incident_pack.build_incident_pack(case["id"])
    text = result["summary_path"].read_text(encoding="utf-8")

    assert "Recent sessions:" in text
    assert "2026-04-17_20-10-00" in text
    assert "top_vendor=TestVendor" in text
    assert "2026-04-17_20-05-00" in text
