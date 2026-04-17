from pathlib import Path

from ble_radar import investigation


def test_create_case_creates_json_file(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")

    case = investigation.create_case("Tracker suspect")

    path = (tmp_path / "cases" / f"{case['id']}.json")
    assert path.exists()
    assert case["title"] == "Tracker suspect"
    assert case["status"] == "open"
    assert case["notes"] == []


def test_create_case_normalizes_device(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")

    case = investigation.create_case(
        "Beacon check",
        device={"name": "Beacon-One", "address": "AA:BB", "risk_score": 12},
    )

    assert case["device"]["name"] == "Beacon-One"
    assert case["device"]["address"] == "AA:BB"
    assert case["device"]["vendor"] == "Unknown"
    assert case["device"]["reason_short"] == "normal"


def test_add_case_note_appends_note(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")

    case = investigation.create_case("Case notes")
    updated = investigation.add_case_note(case["id"], "Premier commentaire")

    assert len(updated["notes"]) == 1
    assert updated["notes"][0]["text"] == "Premier commentaire"


def test_set_case_status_updates_status(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")

    case = investigation.create_case("Case status")
    updated = investigation.set_case_status(case["id"], "watch")

    assert updated["status"] == "watch"


def test_list_cases_returns_created_cases(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")

    a = investigation.create_case("Case A")
    b = investigation.create_case("Case B")
    items = investigation.list_cases()

    ids = {x["id"] for x in items}
    assert a["id"] in ids
    assert b["id"] in ids


def test_summarize_case_contains_expected_lines(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")

    case = investigation.create_case(
        "Tracker suspect",
        device={"name": "Tracker-Two", "address": "AA:BB:CC", "vendor": "TrackCorp"},
    )
    case = investigation.add_case_note(case["id"], "Signal récurrent près du poste")
    lines = investigation.summarize_case(case)

    joined = "\n".join(lines)
    assert "Case: Tracker suspect" in joined
    assert "Status: open" in joined
    assert "Device: Tracker-Two | AA:BB:CC" in joined
    assert "Notes: 1" in joined
    assert "Last note: Signal récurrent près du poste" in joined
