"""Tests for ble_radar.history.operator_briefing (step 14)."""
from __future__ import annotations


def _mod():
    import ble_radar.history.operator_briefing as m
    return m


def test_briefing_returns_required_fields():
    m = _mod()
    out = m.build_operator_briefing()
    for key in (
        "top_priorities",
        "open_cases_count",
        "investigating_count",
        "pending_confirmations_count",
        "recent_auto_actions",
        "recent_timeline_highlights",
        "suggested_next_steps",
    ):
        assert key in out


def test_top_priorities_sorted_by_triage_score_desc():
    m = _mod()
    out = m.build_operator_briefing(
        triage_results=[
            {"address": "A", "name": "a", "triage_score": 10, "triage_bucket": "watch", "short_reason": "x"},
            {"address": "B", "name": "b", "triage_score": 60, "triage_bucket": "critical", "short_reason": "y"},
            {"address": "C", "name": "c", "triage_score": 30, "triage_bucket": "review", "short_reason": "z"},
        ]
    )
    assert out["top_priorities"][0]["address"] == "B"
    assert out["top_priorities"][1]["address"] == "C"


def test_counts_come_from_workflow_and_rule_summary():
    m = _mod()
    out = m.build_operator_briefing(
        workflow_summary={
            "open": [{"address": "A"}, {"address": "B"}],
            "investigating": [{"address": "A"}],
        },
        rule_summary={
            "pending_confirmations": [{"rule_id": "r1"}, {"rule_id": "r2"}],
            "auto_applied": [],
            "recent_matched": [],
        },
    )
    assert out["open_cases_count"] == 2
    assert out["investigating_count"] == 1
    assert out["pending_confirmations_count"] == 2


def test_recent_auto_actions_prefers_rule_summary_rows():
    m = _mod()
    out = m.build_operator_briefing(
        rule_summary={
            "auto_applied": [
                {"address": "AA", "rule_id": "re-watch-auto-monitor", "recommended_action": "x", "reason": "r"}
            ],
            "pending_confirmations": [],
            "recent_matched": [],
        },
        rule_log_events=[
            {"address": "ZZ", "rule_id": "old", "auto_applied": True}
        ],
    )
    assert out["recent_auto_actions"]
    assert out["recent_auto_actions"][0]["address"] == "AA"


def test_recent_auto_actions_falls_back_to_log_events():
    m = _mod()
    out = m.build_operator_briefing(
        rule_summary={"auto_applied": [], "pending_confirmations": [], "recent_matched": []},
        rule_log_events=[
            {
                "address": "AA:BB",
                "rule_id": "re-baseline-auto",
                "auto_applied": True,
                "recommended_action": "Observe",
                "reason": "normal",
            }
        ],
    )
    assert out["recent_auto_actions"]
    assert out["recent_auto_actions"][0]["rule_id"] == "re-baseline-auto"


def test_timeline_highlights_compact_lines():
    m = _mod()
    out = m.build_operator_briefing(
        timeline_events=[
            {"timestamp": "2026-04-18 12:00:00", "source": "triage", "summary": "Critical rise"}
        ]
    )
    assert out["recent_timeline_highlights"]
    assert "triage" in out["recent_timeline_highlights"][0]


def test_suggested_next_steps_includes_confirmation_priority():
    m = _mod()
    out = m.build_operator_briefing(
        triage_results=[{"address": "AA", "name": "x", "triage_score": 60, "triage_bucket": "critical", "short_reason": "alert"}],
        workflow_summary={"open": [{}, {}], "investigating": [{}]},
        rule_summary={"pending_confirmations": [{}, {}], "auto_applied": [], "recent_matched": []},
        playbook_recommendations=[{"recommended_action": "Escalate"}],
        investigation_profile={"case": {"status": "investigating"}},
    )
    joined = " | ".join(out["suggested_next_steps"])
    assert "pending confirmations" in joined.lower()
    assert "prioritize" in joined.lower()


def test_suggested_next_steps_has_baseline_fallback():
    m = _mod()
    out = m.build_operator_briefing(
        triage_results=[],
        workflow_summary={},
        rule_summary={"pending_confirmations": [], "auto_applied": [], "recent_matched": []},
        playbook_recommendations=[],
        investigation_profile=None,
    )
    assert out["suggested_next_steps"]
