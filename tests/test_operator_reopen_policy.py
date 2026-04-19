"""Tests for lightweight operator reopen policy / controlled reopening system."""
from __future__ import annotations

from ble_radar.history.operator_reopen_policy import (
    build_operator_reopen_records,
    summarize_operator_reopen_records,
)


def test_build_operator_reopen_records_required_fields_and_trigger_type():
    rows = build_operator_reopen_records(
        [
            {
                "scope_type": "campaign",
                "scope_id": "campaign-aabb",
            }
        ],
        closure_packages=[
            {
                "closure_id": "closure-campaign-aabb-1",
                "scope_type": "campaign",
                "scope_id": "campaign-aabb",
                "final_disposition": "resolved_with_followup",
                "followup_mode": "monitor",
            }
        ],
        post_closure_monitoring_policies=[
            {
                "policy_id": "policy-campaign-aabb-1",
                "scope_type": "campaign",
                "scope_id": "campaign-aabb",
                "monitoring_mode": "watch_for_recurrence",
                "reopen_triggers": ["signal_pattern_detected"],
            }
        ],
        escalation_feedback=[
            {
                "feedback_id": "feedback-campaign-aabb-1",
                "scope_type": "campaign",
                "scope_id": "campaign-aabb",
                "review_result": "needs_more_data",
            }
        ],
        outcomes=[
            {
                "outcome_id": "outcome-campaign-aabb-1",
                "scope_type": "campaign",
                "scope_id": "campaign-aabb",
                "outcome_label": "resolved_but_returned",
                "reopened": True,
            }
        ],
        pattern_library=[
            {
                "pattern_id": "pattern-campaign-aabb",
                "scope_type": "campaign",
                "scope_id": "campaign-aabb",
            }
        ],
        queue_health_snapshot={"queue_pressure": "high"},
        alerts_history=[{"scope_id": "campaign-aabb", "severity": "high"}],
        campaign_tracking=[
            {
                "campaign_id": "campaign-aabb",
                "scope_id": "campaign-aabb",
                "status": "recurring",
            }
        ],
        evidence_packs=[
            {
                "pack_id": "pack-campaign-aabb-1",
                "scope_type": "campaign",
                "scope_id": "campaign-aabb",
            }
        ],
        session_journal={"next_shift_priorities": ["Carry-over queue items: 2"]},
        generated_at="2026-04-19 10:00:00",
    )

    assert rows
    row = rows[0]

    required_fields = {
        "reopen_id",
        "scope_type",
        "scope_id",
        "closure_id",
        "trigger_type",
        "trigger_summary",
        "reopen_reason",
        "reopen_priority",
        "target_queue_state",
        "carry_forward_context",
        "reopen_count",
        "reopened_at",
    }
    assert required_fields.issubset(set(row.keys()))

    allowed_trigger_types = {
        "pattern_recurred",
        "campaign_resurfaced",
        "similar_alert_returned",
        "monitoring_triggered",
        "specialist_requested_reopen",
        "closure_confidence_too_low",
        "new_evidence_attached",
    }
    assert row["trigger_type"] in allowed_trigger_types
    assert isinstance(row["carry_forward_context"], dict)


def test_summarize_operator_reopen_records_sections_exist():
    summary = summarize_operator_reopen_records(
        [
            {
                "reopen_id": "reopen-case-aabb-1",
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "closure_id": "closure-case-aabb-1",
                "trigger_type": "pattern_recurred",
                "trigger_summary": "trigger=pattern_recurred",
                "reopen_reason": "known_pattern_recurred_on_closed_scope",
                "reopen_priority": "high",
                "target_queue_state": "in_review",
                "carry_forward_context": {"queue_pressure": "medium"},
                "reopen_count": 2,
                "reopened_at": "2026-04-19 10:00:00",
            },
            {
                "reopen_id": "reopen-campaign-bbcc-1",
                "scope_type": "campaign",
                "scope_id": "campaign-bbcc",
                "closure_id": "closure-campaign-bbcc-1",
                "trigger_type": "campaign_resurfaced",
                "trigger_summary": "trigger=campaign_resurfaced",
                "reopen_reason": "campaign_activity_returned_post_closure",
                "reopen_priority": "critical",
                "target_queue_state": "ready",
                "carry_forward_context": {"queue_pressure": "high"},
                "reopen_count": 1,
                "reopened_at": "2026-04-19 11:00:00",
            },
        ]
    )

    required_sections = {
        "reopen_records",
        "reopened_cases",
        "recent_reopen_triggers",
        "returned_to_queue",
        "repeated_reopeners",
        "high_priority_reopens",
    }
    assert required_sections.issubset(set(summary.keys()))
    assert len(summary["reopen_records"]) == 2
    assert len(summary["reopened_cases"]) >= 1
    assert len(summary["returned_to_queue"]) >= 1
    assert len(summary["repeated_reopeners"]) >= 1
    assert len(summary["high_priority_reopens"]) >= 1
