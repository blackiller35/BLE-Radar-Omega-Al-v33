"""Tests for lightweight operator closure package / final resolution system (step 28)."""
from __future__ import annotations

from ble_radar.history.operator_closure_package import (
    build_operator_closure_packages,
    summarize_operator_closure_packages,
)


def test_build_operator_closure_packages_required_fields():
    closures = build_operator_closure_packages(
        [
            {
                "scope_type": "queue_item",
                "scope_id": "q-device-aabb",
                "queue_state": "resolved",
            }
        ],
        escalation_feedback=[
            {
                "feedback_id": "feedback-1",
                "escalation_id": "escalation-1",
                "scope_type": "queue_item",
                "scope_id": "q-device-aabb",
                "review_result": "close_as_resolved",
                "requested_followup": ["finalize closure workflow"],
            }
        ],
        escalation_packages=[
            {
                "escalation_id": "escalation-1",
                "scope_type": "queue_item",
                "scope_id": "q-device-aabb",
                "escalation_reason": "blocked_long_too_long",
                "open_risks": [],
                "actions_already_taken": ["manual_followup"],
            }
        ],
        readiness_profiles=[{"scope_type": "queue_item", "scope_id": "q-device-aabb", "readiness_state": "ready_for_archive"}],
        outcomes=[{"scope_type": "queue_item", "scope_id": "q-device-aabb", "outcome_label": "resolved_cleanly"}],
        recommendation_profiles=[{"scope_id": "q-device-aabb", "confidence_level": "high"}],
        queue_items=[{"item_id": "q-device-aabb", "scope_type": "device", "scope_id": "AA:BB:CC:DD:EE:01", "queue_state": "resolved"}],
        queue_health_snapshot={"queue_pressure": "low"},
        evidence_packs=[{"pack_id": "pack-device-aabb", "scope_type": "device", "scope_id": "AA:BB:CC:DD:EE:01"}],
        pattern_matches=[{"scope_type": "queue_item", "scope_id": "q-device-aabb", "pattern_id": "pattern-queue"}],
        session_journal={"handoff_summary": "done"},
        generated_at="2026-04-18 22:00:00",
    )

    assert closures
    required = {
        "closure_id",
        "scope_type",
        "scope_id",
        "final_disposition",
        "resolution_summary",
        "key_supporting_signals",
        "actions_taken",
        "final_risk_level",
        "followup_mode",
        "archive_recommendation",
        "closed_at",
    }
    assert required.issubset(set(closures[0].keys()))


def test_summarize_operator_closure_packages_sections_exist():
    summary = summarize_operator_closure_packages(
        [
            {
                "closure_id": "closure-device-aabb-1",
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "final_disposition": "resolved",
                "resolution_summary": "ok",
                "key_supporting_signals": ["review_result=confirmed"],
                "actions_taken": ["manual_followup"],
                "final_risk_level": "low",
                "followup_mode": "none",
                "archive_recommendation": "archive_after_brief_hold",
                "closed_at": "2026-04-18 22:00:00",
            },
            {
                "closure_id": "closure-device-aabb-2",
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:02",
                "final_disposition": "false_positive",
                "resolution_summary": "fp",
                "key_supporting_signals": ["review_result=close_as_false_positive"],
                "actions_taken": ["triage"],
                "final_risk_level": "low",
                "followup_mode": "none",
                "archive_recommendation": "archive_now",
                "closed_at": "2026-04-18 22:01:00",
            },
        ]
    )

    assert "closure_packages" in summary
    assert "recently_closed" in summary
    assert "closed_after_escalation" in summary
    assert "resolved_vs_false_positive" in summary
    assert "followup_still_needed" in summary
    assert summary["resolved_vs_false_positive"]["resolved"] >= 1
    assert summary["resolved_vs_false_positive"]["false_positive"] >= 1
