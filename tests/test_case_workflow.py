"""Tests for ble_radar.history.case_workflow (step 10)."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from ble_radar.security import SecurityContext


# ---------------------------------------------------------------------------
# Fixtures — isolate file I/O to tmp directories
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_storage(tmp_path, monkeypatch):
    """Redirect CASES_FILE and CASE_EVENTS_FILE to tmp directories."""
    cases_file = tmp_path / "cases.json"
    events_file = tmp_path / "case_events.json"

    import ble_radar.history.cases as cases_mod
    import ble_radar.history.case_workflow as wf_mod

    monkeypatch.setattr(cases_mod, "CASES_FILE", cases_file)
    monkeypatch.setattr(wf_mod, "CASE_EVENTS_FILE", events_file)
    monkeypatch.setattr(
        cases_mod,
        "build_security_context",
        lambda: SecurityContext(
            mode="operator",
            yubikey_present=True,
            key_name="primary",
            key_label="YubiKey-1",
            sensitive_enabled=True,
            secrets_unlocked=True,
        ),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import():
    import importlib
    import ble_radar.history.case_workflow as m

    return m


# ---------------------------------------------------------------------------
# VALID_STATUSES / constants
# ---------------------------------------------------------------------------


def test_valid_statuses_contains_all():
    m = _import()
    assert set(m.VALID_STATUSES) == {
        "new",
        "watch",
        "review",
        "investigating",
        "resolved",
        "ignored",
    }


def test_open_statuses_excludes_terminal():
    m = _import()
    for s in ("resolved", "ignored"):
        assert s not in m.OPEN_STATUSES


def test_needs_action_statuses_excludes_watch():
    m = _import()
    assert "watch" not in m.NEEDS_ACTION_STATUSES


# ---------------------------------------------------------------------------
# log_event
# ---------------------------------------------------------------------------


def test_log_event_returns_event():
    m = _import()
    ev = m.log_event("AA:BB:CC:DD:EE:FF", "case_created", "initial")
    assert ev["address"] == "AA:BB:CC:DD:EE:FF"
    assert ev["action"] == "case_created"
    assert ev["detail"] == "initial"
    assert "timestamp" in ev


def test_log_event_normalises_address():
    m = _import()
    ev = m.log_event("aa:bb:cc:dd:ee:ff", "note_added")
    assert ev["address"] == "AA:BB:CC:DD:EE:FF"


def test_log_event_empty_address_raises():
    m = _import()
    with pytest.raises(ValueError):
        m.log_event("", "note_added")


def test_log_event_appends():
    m = _import()
    m.log_event("11:22:33:44:55:66", "case_created")
    m.log_event("11:22:33:44:55:66", "note_added", "follow-up")
    events = m.load_events("11:22:33:44:55:66")
    assert len(events) == 2
    assert events[1]["action"] == "note_added"


# ---------------------------------------------------------------------------
# load_events
# ---------------------------------------------------------------------------


def test_load_events_filter_by_address():
    m = _import()
    m.log_event("AA:00:00:00:00:01", "case_created")
    m.log_event("BB:00:00:00:00:02", "case_created")
    events = m.load_events("AA:00:00:00:00:01")
    assert all(e["address"] == "AA:00:00:00:00:01" for e in events)
    assert len(events) == 1


def test_load_events_no_filter_returns_all():
    m = _import()
    m.log_event("AA:00:00:00:00:01", "case_created")
    m.log_event("BB:00:00:00:00:02", "case_created")
    assert len(m.load_events()) == 2


# ---------------------------------------------------------------------------
# transition_case
# ---------------------------------------------------------------------------


def test_transition_case_creates_new_record():
    m = _import()
    rec = m.transition_case("CC:DD:EE:FF:00:01", "new")
    assert rec["status"] == "new"
    assert rec["address"] == "CC:DD:EE:FF:00:01"


def test_transition_case_invalid_status_raises():
    m = _import()
    with pytest.raises(ValueError, match="Invalid status"):
        m.transition_case("CC:DD:EE:FF:00:02", "flying")


def test_transition_case_logs_status_changed():
    m = _import()
    m.transition_case("DD:EE:FF:00:01:02", "watch")
    m.transition_case("DD:EE:FF:00:01:02", "review")
    events = m.load_events("DD:EE:FF:00:01:02")
    actions = [e["action"] for e in events]
    assert "status_changed" in actions


def test_transition_to_resolved_logs_case_resolved():
    m = _import()
    m.transition_case("EE:FF:00:01:02:03", "watch")
    m.transition_case("EE:FF:00:01:02:03", "resolved")
    events = m.load_events("EE:FF:00:01:02:03")
    assert any(e["action"] == "case_resolved" for e in events)


def test_transition_case_preserves_created_at():
    from ble_radar.history.cases import upsert_case

    m = _import()
    upsert_case("FF:00:01:02:03:04", "test", "watch")
    from ble_radar.history.cases import load_cases

    created_at = load_cases()["FF:00:01:02:03:04"]["created_at"]
    m.transition_case("FF:00:01:02:03:04", "review")
    assert load_cases()["FF:00:01:02:03:04"]["created_at"] == created_at


def test_transition_case_with_note_in_event():
    m = _import()
    m.transition_case(
        "00:11:22:33:44:55", "investigating", note="added satellite signal"
    )
    events = m.load_events("00:11:22:33:44:55")
    assert any("added satellite signal" in e.get("detail", "") for e in events)


def test_transition_case_empty_address_raises():
    m = _import()
    with pytest.raises(ValueError):
        m.transition_case("", "new")


# ---------------------------------------------------------------------------
# case_workflow_summary
# ---------------------------------------------------------------------------


def _make_cases(*pairs):
    """Return a dict of cases from (address, status) pairs."""
    from datetime import datetime

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cases = {}
    for addr, status in pairs:
        cases[addr] = {
            "address": addr,
            "reason": "test",
            "status": status,
            "created_at": now,
            "updated_at": now,
        }
    return cases


def test_summary_empty_cases():
    m = _import()
    s = m.case_workflow_summary({})
    assert s["total"] == 0
    assert s["open"] == []
    assert s["investigating"] == []


def test_summary_counts_open():
    m = _import()
    cases = _make_cases(
        ("A1", "new"), ("A2", "watch"), ("A3", "reviewing"), ("A4", "resolved")
    )
    s = m.case_workflow_summary(cases)
    # "reviewing" is not a valid status but shouldn't crash; it just won't be in open
    open_statuses = {r["status"] for r in s["open"]}
    assert "new" in open_statuses
    assert "watch" in open_statuses


def test_summary_investigating_subset():
    m = _import()
    cases = _make_cases(("B1", "investigating"), ("B2", "watch"))
    s = m.case_workflow_summary(cases)
    assert len(s["investigating"]) == 1
    assert s["investigating"][0]["address"] == "B1"


def test_summary_needs_action():
    m = _import()
    cases = _make_cases(("C1", "new"), ("C2", "watch"), ("C3", "review"))
    s = m.case_workflow_summary(cases)
    action_statuses = {r["status"] for r in s["needs_action"]}
    assert "new" in action_statuses
    assert "review" in action_statuses
    assert "watch" not in action_statuses


def test_summary_resolved_capped_at_5():
    m = _import()
    cases = _make_cases(*[(f"R{i}", "resolved") for i in range(8)])
    s = m.case_workflow_summary(cases)
    assert len(s["resolved"]) <= 5


def test_summary_total_count():
    m = _import()
    cases = _make_cases(("T1", "new"), ("T2", "resolved"), ("T3", "ignored"))
    s = m.case_workflow_summary(cases)
    assert s["total"] == 3


def test_summary_loads_from_disk_when_none():
    m = _import()
    from ble_radar.history.cases import upsert_case

    upsert_case("DD:11:22:33:44:55", "disk test", "investigating")
    s = m.case_workflow_summary()  # no argument → loads from file
    assert s["total"] == 1
    assert len(s["investigating"]) == 1


# ---------------------------------------------------------------------------
# next_action
# ---------------------------------------------------------------------------


def test_next_action_all_statuses():
    m = _import()
    for status in m.VALID_STATUSES:
        rec = {"status": status}
        suggestion = m.next_action(rec)
        assert isinstance(suggestion, str)
        assert len(suggestion) > 0


def test_next_action_unknown_status_returns_fallback():
    m = _import()
    rec = {"status": "unknown_status"}
    suggestion = m.next_action(rec)
    assert "No action defined" in suggestion


def test_next_action_new_suggests_escalate():
    m = _import()
    suggestion = m.next_action({"status": "new"})
    assert "escalate" in suggestion.lower() or "operator" in suggestion.lower()


def test_next_action_resolved_suggests_archive():
    m = _import()
    suggestion = m.next_action({"status": "resolved"})
    assert "archive" in suggestion.lower() or "re-open" in suggestion.lower()
