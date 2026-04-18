"""Tests for ble_radar.history.operator_rule_engine (step 13)."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_automation_log(tmp_path, monkeypatch):
    import ble_radar.history.operator_rule_engine as re_mod

    monkeypatch.setattr(re_mod, "AUTOMATION_EVENTS_FILE", tmp_path / "automation_events.json")


def _mod():
    import ble_radar.history.operator_rule_engine as m
    return m


def test_evaluate_operator_rules_empty_address_raises():
    m = _mod()
    with pytest.raises(ValueError):
        m.evaluate_operator_rules("")


def test_evaluate_returns_required_fields():
    m = _mod()
    rows = m.evaluate_operator_rules(
        "AA:BB:CC:DD:EE:FF",
        triage_row={"triage_score": 10, "triage_bucket": "watch"},
        persist_log=False,
    )
    assert rows
    for row in rows:
        for key in ("rule_id", "matched", "recommended_action", "auto_applied", "requires_confirmation", "reason"):
            assert key in row


def test_critical_rule_requires_confirmation_and_not_auto_applied():
    m = _mod()
    rows = m.evaluate_operator_rules(
        "AA:BB:CC:DD:EE:FF",
        triage_row={"triage_score": 60, "triage_bucket": "critical"},
        persist_log=False,
    )
    critical = next(r for r in rows if r["rule_id"] == "re-critical-confirm")
    assert critical["matched"] is True
    assert critical["requires_confirmation"] is True
    assert critical["auto_applied"] is False


def test_review_rule_matches_for_new_status():
    m = _mod()
    rows = m.evaluate_operator_rules(
        "AA:BB:CC:DD:EE:11",
        triage_row={"triage_score": 28, "triage_bucket": "review"},
        case_record={"status": "new"},
        persist_log=False,
    )
    review = next(r for r in rows if r["rule_id"] == "re-review-confirm")
    assert review["matched"] is True
    assert review["requires_confirmation"] is True


def test_watch_rule_can_auto_apply():
    m = _mod()
    rows = m.evaluate_operator_rules(
        "AA:BB:CC:DD:EE:22",
        triage_row={"triage_score": 12, "triage_bucket": "watch"},
        case_record={"status": "watch"},
        apply_auto=True,
        persist_log=False,
    )
    watch = next(r for r in rows if r["rule_id"] == "re-watch-auto-monitor")
    assert watch["matched"] is True
    assert watch["auto_applied"] is True
    assert watch["requires_confirmation"] is False


def test_close_rule_can_auto_apply_when_resolved():
    m = _mod()
    rows = m.evaluate_operator_rules(
        "AA:BB:CC:DD:EE:33",
        case_record={"status": "resolved"},
        triage_row={"triage_score": 2, "triage_bucket": "normal"},
        apply_auto=True,
        persist_log=False,
    )
    close = next(r for r in rows if r["rule_id"] == "re-close-auto")
    assert close["matched"] is True
    assert close["auto_applied"] is True


def test_baseline_rule_matches_for_normal_none_status():
    m = _mod()
    rows = m.evaluate_operator_rules(
        "AA:BB:CC:DD:EE:44",
        case_record={"status": "none"},
        triage_row={"triage_score": 0, "triage_bucket": "normal"},
        apply_auto=True,
        persist_log=False,
    )
    baseline = next(r for r in rows if r["rule_id"] == "re-baseline-auto")
    assert baseline["matched"] is True
    assert baseline["auto_applied"] is True


def test_playbook_signal_is_used():
    m = _mod()
    rows = m.evaluate_operator_rules(
        "AA:BB:CC:DD:EE:55",
        playbook_recommendation={"playbook_id": "pb-critical-pack", "recommended_action": "Escalate"},
        triage_row={"triage_score": 0, "triage_bucket": "normal"},
        persist_log=False,
    )
    critical = next(r for r in rows if r["rule_id"] == "re-critical-confirm")
    assert critical["matched"] is True
    assert "Escalate" in critical["recommended_action"]


def test_incident_pack_signal_is_used_in_reason():
    m = _mod()
    rows = m.evaluate_operator_rules(
        "AA:BB:CC:DD:EE:66",
        triage_row={"triage_score": 50, "triage_bucket": "critical"},
        investigation_profile={"incident_refs": {"device_packs": ["PK1"], "incident_packs": []}},
        persist_log=False,
    )
    critical = next(r for r in rows if r["rule_id"] == "re-critical-confirm")
    assert "pack_available=True" in critical["reason"]


def test_persist_log_writes_only_matched_rules():
    m = _mod()
    rows = m.evaluate_operator_rules(
        "AA:BB:CC:DD:EE:77",
        triage_row={"triage_score": 12, "triage_bucket": "watch"},
        case_record={"status": "watch"},
        persist_log=True,
    )
    events = m.load_automation_events("AA:BB:CC:DD:EE:77")
    matched_count = len([r for r in rows if r["matched"]])
    assert len(events) == matched_count


def test_load_automation_events_filter_and_limit():
    m = _mod()
    for i in range(3):
        m.log_automation_event(
            "AA:BB:CC:DD:EE:88",
            {
                "rule_id": f"r{i}",
                "matched": True,
                "auto_applied": False,
                "requires_confirmation": True,
                "recommended_action": "x",
                "reason": "y",
            },
        )
    m.log_automation_event(
        "FF:EE:DD:CC:BB:AA",
        {
            "rule_id": "other",
            "matched": True,
            "auto_applied": False,
            "requires_confirmation": True,
            "recommended_action": "x",
            "reason": "y",
        },
    )

    filtered = m.load_automation_events("AA:BB:CC:DD:EE:88", limit=2)
    assert len(filtered) == 2
    assert all(e["address"] == "AA:BB:CC:DD:EE:88" for e in filtered)


def test_summarize_rule_results_groups_rows():
    m = _mod()
    summary = m.summarize_rule_results([
        {"rule_id": "a", "matched": True, "auto_applied": True, "requires_confirmation": False},
        {"rule_id": "b", "matched": True, "auto_applied": False, "requires_confirmation": True},
        {"rule_id": "c", "matched": False, "auto_applied": False, "requires_confirmation": False},
    ])
    assert len(summary["auto_applied"]) == 1
    assert len(summary["pending_confirmations"]) == 1
    assert len(summary["recent_matched"]) == 2
