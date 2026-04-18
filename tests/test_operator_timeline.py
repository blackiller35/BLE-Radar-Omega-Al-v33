"""Tests for ble_radar.history.operator_timeline (step 11)."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_case_event_store(tmp_path, monkeypatch):
    import ble_radar.history.case_workflow as wf_mod
    import ble_radar.history.operator_timeline as tl_mod

    monkeypatch.setattr(wf_mod, "CASE_EVENTS_FILE", tmp_path / "case_events.json")
    monkeypatch.setattr(tl_mod, "REPORTS_DIR", tmp_path / "reports")


def _mod():
    import ble_radar.history.operator_timeline as m
    return m


def test_build_operator_timeline_empty_address_raises():
    m = _mod()
    with pytest.raises(ValueError):
        m.build_operator_timeline("")


def test_registry_events_are_added():
    m = _mod()
    registry = {
        "AA:BB:CC:DD:EE:FF": {
            "first_seen": "2026-04-18 10:00:00",
            "last_seen": "2026-04-18 12:00:00",
            "seen_count": 3,
            "session_count": 2,
        }
    }

    tl = m.build_operator_timeline("AA:BB:CC:DD:EE:FF", registry=registry)
    actions = [e["action"] for e in tl["events"]]
    assert "first_seen" in actions
    assert "last_seen" in actions


def test_case_workflow_events_are_included():
    from ble_radar.history.case_workflow import log_event

    m = _mod()
    log_event("AA:AA:AA:AA:AA:AA", "case_created", "opened by operator")
    log_event("AA:AA:AA:AA:AA:AA", "note_added", "manual note")

    tl = m.build_operator_timeline("AA:AA:AA:AA:AA:AA")
    summaries = [e["summary"] for e in tl["events"]]
    assert any("Case created" in s for s in summaries)
    assert any("Note added" in s for s in summaries)


def test_movement_new_event_is_included():
    m = _mod()
    movement = {
        "new": [{"address": "11:22:33:44:55:66"}],
        "disappeared": [],
        "recurring": [],
        "score_changes": [],
    }
    tl = m.build_operator_timeline("11:22:33:44:55:66", movement=movement)
    assert any(e["source"] == "session_movement" and e["action"] == "new" for e in tl["events"])


def test_movement_score_change_event_is_included():
    m = _mod()
    movement = {
        "new": [],
        "disappeared": [],
        "recurring": [],
        "score_changes": [{
            "address": "22:33:44:55:66:77",
            "prev_score": 40,
            "curr_score": 55,
            "delta": 15,
        }],
    }
    tl = m.build_operator_timeline("22:33:44:55:66:77", movement=movement)
    assert any("delta=15" in e["summary"] for e in tl["events"])


def test_triage_snapshot_event_is_included():
    m = _mod()
    triage_results = [{
        "address": "33:44:55:66:77:88",
        "triage_score": 48,
        "triage_bucket": "critical",
        "short_reason": "alert:critique",
    }]
    tl = m.build_operator_timeline("33:44:55:66:77:88", triage_results=triage_results)
    assert any(e["source"] == "triage" and e["action"] == "snapshot" for e in tl["events"])


def test_triage_change_hint_when_score_delta_available():
    m = _mod()
    triage_results = [{
        "address": "44:55:66:77:88:99",
        "triage_score": 25,
        "triage_bucket": "review",
        "short_reason": "registry_score≥60",
    }]
    movement = {
        "new": [],
        "disappeared": [],
        "recurring": [],
        "score_changes": [{"address": "44:55:66:77:88:99", "delta": -8}],
    }
    tl = m.build_operator_timeline(
        "44:55:66:77:88:99",
        triage_results=triage_results,
        movement=movement,
    )
    assert any(e["action"] == "change_hint" for e in tl["events"])


def test_incident_pack_generation_dirs_are_included(tmp_path, monkeypatch):
    m = _mod()
    reports_dir = tmp_path / "reports"
    packs_dir = reports_dir / "device_packs"
    packs_dir.mkdir(parents=True)

    (packs_dir / "AABBCCDDEEFF_2026-04-18_12-00-00").mkdir()
    (packs_dir / "AABBCCDDEEFF_2026-04-18_12-05-00").mkdir()

    monkeypatch.setattr(m, "REPORTS_DIR", reports_dir)
    tl = m.build_operator_timeline("AA:BB:CC:DD:EE:FF")

    pack_events = [e for e in tl["events"] if e["source"] == "incident_pack"]
    assert len(pack_events) == 2
    assert any("2026-04-18_12-05-00" in e["summary"] for e in pack_events)


def test_events_are_chronological_when_timestamps_exist():
    from ble_radar.history.case_workflow import log_event

    m = _mod()
    # Events share the same timestamp format and should remain chronological.
    log_event("55:66:77:88:99:AA", "case_created", "1")
    log_event("55:66:77:88:99:AA", "note_added", "2")

    tl = m.build_operator_timeline("55:66:77:88:99:AA")
    dated = [e for e in tl["events"] if str(e.get("timestamp"))]
    stamps = [e["timestamp"] for e in dated]
    assert stamps == sorted(stamps)


def test_compact_lines_are_readable():
    m = _mod()
    registry = {
        "66:77:88:99:AA:BB": {
            "first_seen": "2026-04-18 10:00:00",
            "last_seen": "2026-04-18 10:00:00",
            "seen_count": 1,
            "session_count": 1,
        }
    }
    tl = m.build_operator_timeline("66:77:88:99:AA:BB", registry=registry)
    assert len(tl["compact"]) >= 1
    assert "registry" in tl["compact"][0]


def test_recent_timeline_events_respects_limit_and_order():
    from ble_radar.history.case_workflow import log_event

    m = _mod()
    log_event("77:88:99:AA:BB:CC", "case_created", "a")
    log_event("77:88:99:AA:BB:CC", "note_added", "b")
    tl = m.build_operator_timeline("77:88:99:AA:BB:CC")

    recent = m.recent_timeline_events(tl, limit=1)
    assert len(recent) == 1
    assert recent[0]["source"] == "case_workflow"


def test_recent_timeline_events_handles_no_events():
    m = _mod()
    recent = m.recent_timeline_events({"events": []}, limit=5)
    assert recent == []


def test_address_normalization_applies_to_all_sources(tmp_path, monkeypatch):
    from ble_radar.history.case_workflow import log_event

    m = _mod()
    reports_dir = tmp_path / "reports"
    packs_dir = reports_dir / "device_packs"
    packs_dir.mkdir(parents=True)
    (packs_dir / "ABCDEFABCDEF_2026-04-18_12-00-00").mkdir()
    monkeypatch.setattr(m, "REPORTS_DIR", reports_dir)

    log_event("ab:cd:ef:ab:cd:ef", "case_created")
    tl = m.build_operator_timeline("ab:cd:ef:ab:cd:ef")

    assert tl["address"] == "AB:CD:EF:AB:CD:EF"
    assert any(e["source"] == "case_workflow" for e in tl["events"])
    assert any(e["source"] == "incident_pack" for e in tl["events"])


def test_combined_signals_present_in_one_timeline(tmp_path, monkeypatch):
    from ble_radar.history.case_workflow import log_event

    m = _mod()

    reports_dir = tmp_path / "reports"
    packs_dir = reports_dir / "device_packs"
    packs_dir.mkdir(parents=True)
    (packs_dir / "112233445566_2026-04-18_12-00-00").mkdir()
    monkeypatch.setattr(m, "REPORTS_DIR", reports_dir)

    log_event("11:22:33:44:55:66", "status_changed", "new -> review")

    registry = {
        "11:22:33:44:55:66": {
            "first_seen": "2026-04-18 10:00:00",
            "last_seen": "2026-04-18 12:00:00",
            "seen_count": 5,
            "session_count": 3,
        }
    }
    movement = {
        "new": [],
        "disappeared": [],
        "recurring": [{"address": "11:22:33:44:55:66"}],
        "score_changes": [{"address": "11:22:33:44:55:66", "delta": 4, "prev_score": 50, "curr_score": 54}],
    }
    triage_results = [{
        "address": "11:22:33:44:55:66",
        "triage_score": 33,
        "triage_bucket": "review",
        "short_reason": "watch_hit",
    }]

    tl = m.build_operator_timeline(
        "11:22:33:44:55:66",
        registry=registry,
        movement=movement,
        triage_results=triage_results,
    )

    sources = {e["source"] for e in tl["events"]}
    assert "registry" in sources
    assert "case_workflow" in sources
    assert "session_movement" in sources
    assert "triage" in sources
    assert "incident_pack" in sources
