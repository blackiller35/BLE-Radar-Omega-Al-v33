"""Tests for lightweight operator escalation feedback / specialist return (step 27)."""
from __future__ import annotations

from ble_radar.history.operator_escalation_feedback import (
    build_operator_escalation_feedback_records,
    summarize_operator_escalation_feedback,
)


def test_build_operator_escalation_feedback_required_fields():
    feedback = build_operator_escalation_feedback_records(
        [
            {
                "escalation_id": "escalation-queue_item-q-device-aabb-1",
                "scope_type": "queue_item",
                "scope_id": "q-device-aabb",
                "escalation_reason": "blocked_long_too_long",
                "priority": "critical",
                "open_risks": ["queue_blockage", "insufficient_readiness"],
            }
        ],
        readiness_profiles=[
            {
                "scope_type": "queue_item",
                "scope_id": "q-device-aabb",
                "readiness_state": "needs_more_data",
            }
        ],
        outcomes=[
            {
                "scope_type": "queue_item",
                "scope_id": "q-device-aabb",
                "outcome_label": "reopened",
                "source_action": "manual_followup",
            }
        ],
        recommendation_profiles=[
            {
                "scope_id": "q-device-aabb",
                "source_playbook": "pb-critical-pack",
                "confidence_level": "low",
            }
        ],
        queue_items=[
            {
                "item_id": "q-device-aabb",
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "queue_state": "blocked",
            }
        ],
        queue_health_snapshot={"queue_pressure": "high", "stale_items": [{"item_id": "q-device-aabb"}]},
        evidence_packs=[],
        session_journal={"handoff_summary": "shift handoff", "next_shift_priorities": ["unblock queue"]},
        pattern_matches=[{"scope_type": "queue_item", "scope_id": "q-device-aabb", "pattern_id": "pattern-queue"}],
        generated_at="2026-04-18 21:00:00",
    )

    assert feedback
    required = {
        "feedback_id",
        "escalation_id",
        "scope_type",
        "scope_id",
        "review_result",
        "decision_summary",
        "specialist_notes",
        "requested_followup",
        "return_queue_state",
        "closure_recommendation",
        "received_at",
    }
    assert required.issubset(set(feedback[0].keys()))


def test_summarize_operator_escalation_feedback_sections_exist():
    summary = summarize_operator_escalation_feedback(
        [
            {
                "feedback_id": "feedback-1",
                "escalation_id": "escalation-1",
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "review_result": "close_as_resolved",
                "decision_summary": "ok",
                "specialist_notes": "notes",
                "requested_followup": ["finalize closure workflow"],
                "return_queue_state": "resolved",
                "closure_recommendation": "close_now",
                "received_at": "2026-04-18 21:00:00",
            },
            {
                "feedback_id": "feedback-2",
                "escalation_id": "escalation-2",
                "scope_type": "campaign",
                "scope_id": "campaign-aabb",
                "review_result": "needs_more_data",
                "decision_summary": "need more",
                "specialist_notes": "missing evidence",
                "requested_followup": ["collect additional evidence"],
                "return_queue_state": "in_review",
                "closure_recommendation": "keep_open",
                "received_at": "2026-04-18 21:05:00",
            },
        ]
    )

    assert "escalation_feedback" in summary
    assert "returned_for_followup" in summary
    assert "specialist_decisions" in summary
    assert "ready_to_close" in summary
    assert "needs_more_data" in summary
    assert len(summary["ready_to_close"]) == 1
    assert len(summary["needs_more_data"]) == 1
