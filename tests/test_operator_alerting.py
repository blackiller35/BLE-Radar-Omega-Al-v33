"""Tests for ble_radar.history.operator_alerting (step 15)."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_alert_log(tmp_path, monkeypatch):
    import ble_radar.history.operator_alerting as al
    monkeypatch.setattr(al, "ALERT_LOG_FILE", tmp_path / "operator_alerts.json")


def _mod():
    import ble_radar.history.operator_alerting as m
    return m


def test_build_operator_alerts_empty_address_raises():
    m = _mod()
    with pytest.raises(ValueError):
        m.build_operator_alerts("")


def test_alert_row_has_required_fields():
    m = _mod()
    rows = m.build_operator_alerts(
        "AA:BB:CC:DD:EE:FF",
        triage_row={"triage_score": 60, "triage_bucket": "critical", "short_reason": "alert:critique"},
        pending_confirmations_count=1,
    )
    assert rows
    for key in ("alert_id", "severity", "title", "reason", "device_address", "recommended_followup", "created_at"):
        assert key in rows[0]


def test_critical_triage_generates_critical_escalation_alert():
    m = _mod()
    rows = m.build_operator_alerts(
        "AA:BB:CC:DD:EE:01",
        triage_row={"triage_score": 55, "triage_bucket": "critical", "short_reason": "alert"},
    )
    assert any(r["severity"] == "critical" and "escalation" in r["title"].lower() for r in rows)


def test_pending_confirmations_generate_high_alert():
    m = _mod()
    rows = m.build_operator_alerts(
        "AA:BB:CC:DD:EE:02",
        triage_row={"triage_score": 20, "triage_bucket": "review", "short_reason": "x"},
        pending_confirmations_count=2,
    )
    assert any("pending confirmation" in r["title"].lower() for r in rows)


def test_playbook_escalation_signal_generates_alert():
    m = _mod()
    rows = m.build_operator_alerts(
        "AA:BB:CC:DD:EE:03",
        playbook_recommendation={
            "playbook_id": "pb-critical-pack",
            "recommended_action": "Escalate and generate incident pack",
        },
        triage_row={"triage_score": 10, "triage_bucket": "watch", "short_reason": "x"},
    )
    assert any("playbook" in r["title"].lower() for r in rows)


def test_investigation_with_timeline_change_generates_medium_alert():
    m = _mod()
    rows = m.build_operator_alerts(
        "AA:BB:CC:DD:EE:04",
        case_record={"status": "investigating"},
        timeline_events=[{"action": "score_change", "summary": "delta"}],
        triage_row={"triage_score": 15, "triage_bucket": "watch", "short_reason": "x"},
    )
    assert any(r["severity"] == "medium" for r in rows)


def test_auto_action_signal_generates_low_alert():
    m = _mod()
    rows = m.build_operator_alerts(
        "AA:BB:CC:DD:EE:05",
        rule_results=[{"auto_applied": True}],
        triage_row={"triage_score": 0, "triage_bucket": "normal", "short_reason": "x"},
    )
    assert any("auto-action" in r["title"].lower() for r in rows)


def test_persist_log_and_load_log_work():
    m = _mod()
    rows = m.build_operator_alerts(
        "AA:BB:CC:DD:EE:06",
        triage_row={"triage_score": 55, "triage_bucket": "critical", "short_reason": "alert"},
        persist_log=True,
    )
    loaded = m.load_alert_log(address="AA:BB:CC:DD:EE:06")
    assert len(loaded) == len(rows)


def test_load_alert_log_limit_applies():
    m = _mod()
    for i in range(4):
        m.log_alert(
            {
                "alert_id": f"a{i}",
                "severity": "low",
                "title": "t",
                "reason": "r",
                "device_address": "AA:BB:CC:DD:EE:07",
                "recommended_followup": "f",
                "created_at": f"2026-04-18 10:0{i}:00",
            }
        )
    rows = m.load_alert_log(limit=2)
    assert len(rows) == 2


def test_summarize_alerts_groups_active_escalation_immediate():
    m = _mod()
    summary = m.summarize_alerts(
        [
            {
                "alert_id": "a1",
                "severity": "critical",
                "title": "Critical triage escalation",
                "reason": "x",
                "device_address": "A",
                "recommended_followup": "f",
                "created_at": "2026-04-18 10:00:00",
            },
            {
                "alert_id": "a2",
                "severity": "medium",
                "title": "Investigation context changed",
                "reason": "y",
                "device_address": "B",
                "recommended_followup": "f",
                "created_at": "2026-04-18 10:01:00",
            },
        ]
    )
    assert len(summary["active_alerts"]) == 2
    assert len(summary["recent_escalations"]) == 1
    assert len(summary["needs_immediate_review"]) == 1


def test_summarize_alerts_falls_back_to_recent_log_for_escalations():
    m = _mod()
    summary = m.summarize_alerts(
        [],
        recent_log_events=[
            {
                "alert_id": "x",
                "severity": "high",
                "title": "Playbook escalation recommended",
                "reason": "x",
                "device_address": "AA",
                "recommended_followup": "f",
                "created_at": "2026-04-18 10:00:00",
            }
        ],
    )
    assert len(summary["recent_escalations"]) == 1
