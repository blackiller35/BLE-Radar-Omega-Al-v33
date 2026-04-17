from ble_radar import incident_pack, investigation


def test_build_incident_pack_creates_manifest_and_summary(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")
    monkeypatch.setattr(incident_pack, "INCIDENT_PACKS_DIR", tmp_path / "incident_packs")

    case = investigation.create_case("Tracker suspect")
    case = investigation.add_case_note(case["id"], "Premier signal confirmé")

    result = incident_pack.build_incident_pack(case["id"])

    assert result["pack_dir"].exists()
    assert result["manifest_path"].exists()
    assert result["summary_path"].exists()
    assert result["manifest"]["case_id"] == case["id"]
    assert result["manifest"]["notes_count"] == 1
    assert result["manifest"]["matched_devices_count"] == 0


def test_build_incident_pack_matches_latest_device_by_address(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")
    monkeypatch.setattr(incident_pack, "INCIDENT_PACKS_DIR", tmp_path / "incident_packs")

    case = investigation.create_case(
        "Beacon check",
        device={"name": "Beacon-One", "address": "AA:BB:CC:DD:EE:01", "risk_score": 12},
    )

    latest_devices = [
        {
            "name": "Beacon-One",
            "address": "AA:BB:CC:DD:EE:01",
            "vendor": "TestVendor",
            "risk_score": 20,
            "follow_score": 5,
            "confidence_score": 55,
            "final_score": 72,
            "reason_short": "watch_hit",
            "alert_level": "critique",
        }
    ]

    result = incident_pack.build_incident_pack(case["id"], latest_devices=latest_devices)

    assert result["manifest"]["matched_devices_count"] == 1
    match = result["manifest"]["matched_devices"][0]
    assert match["device"]["address"] == "AA:BB:CC:DD:EE:01"
    assert match["explanation"]["scores"]["final_score"] == 72
    assert "reason=watch_hit" in match["explanation"]["summary"]


def test_incident_summary_mentions_case_device_explanation(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")
    monkeypatch.setattr(incident_pack, "INCIDENT_PACKS_DIR", tmp_path / "incident_packs")

    case = investigation.create_case(
        "Tracker review",
        device={
            "name": "Tracker-Two",
            "address": "AA:BB:CC",
            "risk_score": 14,
            "follow_score": 8,
            "confidence_score": 31,
            "final_score": 44,
            "reason_short": "tracker",
        },
    )

    result = incident_pack.build_incident_pack(case["id"])
    text = result["summary_path"].read_text(encoding="utf-8")

    assert "Case device explanation:" in text
    assert "risk=14" in text
    assert "follow=8" in text
    assert "confidence=31" in text
    assert "final=44" in text
    assert "reason=tracker" in text


def test_list_incident_packs_returns_created_pack_dirs(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")
    monkeypatch.setattr(incident_pack, "INCIDENT_PACKS_DIR", tmp_path / "incident_packs")

    case = investigation.create_case("Pack list check")
    result = incident_pack.build_incident_pack(case["id"])

    packs = incident_pack.list_incident_packs()

    assert result["pack_dir"] in packs
