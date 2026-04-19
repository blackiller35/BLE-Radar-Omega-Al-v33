"""Tests for lightweight operator lifecycle lineage / multi-cycle history system."""
from __future__ import annotations

from ble_radar.history.operator_lifecycle_lineage import (
    build_operator_lifecycle_lineage_records,
    summarize_operator_lifecycle_lineage,
)


def test_build_operator_lifecycle_lineage_records_required_fields():
    rows = build_operator_lifecycle_lineage_records(
        [
            {
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
            }
        ],
        outcomes=[
            {
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "outcome_label": "resolved_but_returned",
                "reopened": True,
            }
        ],
        closure_packages=[
            {
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "closure_id": "closure-case-aabb-1",
                "final_disposition": "resolved",
            }
        ],
        post_closure_monitoring_policies=[
            {
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "monitoring_mode": "watch_for_recurrence",
                "reopen_triggers": ["signal_pattern_detected"],
            }
        ],
        reopen_policy_records=[
            {
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "trigger_type": "pattern_recurred",
            }
        ],
        escalation_packages=[
            {
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "escalation_reason": "high_risk_cluster",
            }
        ],
        escalation_feedback=[
            {
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "review_result": "needs_more_data",
            }
        ],
        session_journal={"handoff_summary": "carry over case"},
        pattern_library=[
            {
                "pattern_id": "pattern-case-aabb",
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "title": "Recurring case pattern",
            }
        ],
        pattern_matches=[
            {
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "pattern_id": "pattern-case-aabb",
            }
        ],
        operator_queue_context=[
            {
                "item_id": "q-case-aabb",
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "queue_state": "in_review",
            }
        ],
        campaign_tracking=[],
        evidence_packs=[],
        generated_at="2026-04-19 12:00:00",
    )

    assert rows
    row = rows[0]

    required_fields = {
        "lineage_id",
        "scope_type",
        "scope_id",
        "cycle_count",
        "opened_count",
        "reopened_count",
        "closure_count",
        "escalation_count",
        "last_trigger_type",
        "recurring_pattern_summary",
        "timeline_summary",
        "current_lifecycle_state",
        "updated_at",
    }
    assert required_fields.issubset(set(row.keys()))


def test_summarize_operator_lifecycle_lineage_sections_exist():
    summary = summarize_operator_lifecycle_lineage(
        [
            {
                "lineage_id": "lineage-case-aabb",
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "cycle_count": 3,
                "opened_count": 2,
                "reopened_count": 2,
                "closure_count": 2,
                "escalation_count": 1,
                "last_trigger_type": "pattern_recurred",
                "recurring_pattern_summary": "pattern-case-aabb",
                "timeline_summary": "opened=2 | escalations=1 | closures=2 | reopens=2",
                "current_lifecycle_state": "stabilized_after_reopen",
                "updated_at": "2026-04-19 12:00:00",
            },
            {
                "lineage_id": "lineage-case-ccdd",
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:02",
                "cycle_count": 2,
                "opened_count": 1,
                "reopened_count": 1,
                "closure_count": 1,
                "escalation_count": 0,
                "last_trigger_type": "monitoring_triggered",
                "recurring_pattern_summary": "none",
                "timeline_summary": "opened=1 | escalations=0 | closures=1 | reopens=1",
                "current_lifecycle_state": "reopened_active",
                "updated_at": "2026-04-19 12:01:00",
            },
        ]
    )

    required_sections = {
        "lifecycle_lineage",
        "repeated_reopeners",
        "recurring_triggers",
        "multi_cycle_cases",
        "stabilized_after_reopen",
    }
    assert required_sections.issubset(set(summary.keys()))
    assert len(summary["lifecycle_lineage"]) == 2
    assert len(summary["multi_cycle_cases"]) >= 1
    assert len(summary["recurring_triggers"]) >= 1
