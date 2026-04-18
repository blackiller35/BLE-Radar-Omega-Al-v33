"""Tests for lightweight operator outcome tracking / feedback loop system (step 21)."""
from __future__ import annotations

from ble_radar.history.operator_outcomes import build_operator_outcomes, summarize_operator_outcomes


def test_build_operator_outcomes_contains_supported_scopes_and_required_fields():
    queue_items = [
        {
            "item_id": "q-device-aabb",
            "scope_type": "device",
            "scope_id": "AA:BB:CC:DD:EE:01",
            "queue_state": "ready",
            "priority": "high",
            "recommended_action": "Review device",
            "created_at": "2026-04-18 10:00:00",
            "updated_at": "2026-04-18 10:00:00",
        },
        {
            "item_id": "q-case-aabb",
            "scope_type": "case",
            "scope_id": "AA:BB:CC:DD:EE:01",
            "queue_state": "blocked",
            "priority": "critical",
            "recommended_action": "Resolve blocker",
            "created_at": "2026-04-18 10:10:00",
            "updated_at": "2026-04-18 10:10:00",
        },
        {
            "item_id": "q-cluster-a",
            "scope_type": "cluster",
            "scope_id": "cluster-aabb-2",
            "queue_state": "in_review",
            "priority": "high",
            "recommended_action": "Review cluster",
            "created_at": "2026-04-18 10:20:00",
            "updated_at": "2026-04-18 10:20:00",
        },
        {
            "item_id": "q-campaign-a",
            "scope_type": "campaign",
            "scope_id": "campaign-aabb",
            "queue_state": "in_review",
            "priority": "medium",
            "recommended_action": "Review campaign",
            "created_at": "2026-04-18 10:30:00",
            "updated_at": "2026-04-18 10:30:00",
        },
        {
            "item_id": "q-pack-a",
            "scope_type": "evidence_pack",
            "scope_id": "pack-device-aabb",
            "queue_state": "ready",
            "priority": "high",
            "recommended_action": "Review evidence",
            "created_at": "2026-04-18 10:40:00",
            "updated_at": "2026-04-18 10:40:00",
        },
    ]

    outcomes = build_operator_outcomes(
        queue_items,
        workflow_summary={"needs_action": [{"address": "AA:BB:CC:DD:EE:01", "status": "review"}]},
        playbook_recommendations=[
            {
                "address": "AA:BB:CC:DD:EE:01",
                "playbook_id": "pb-review-triage",
                "recommended_action": "Run review triage workflow",
            }
        ],
        rule_results=[
            {
                "address": "AA:BB:CC:DD:EE:01",
                "requires_confirmation": True,
                "auto_applied": False,
            }
        ],
        alerts=[{"device_address": "AA:BB:CC:DD:EE:01", "severity": "critical"}],
        campaigns=[{"campaign_id": "campaign-aabb", "status": "stable", "risk_level": "medium"}],
        evidence_packs=[{"pack_id": "pack-device-aabb", "risk_level": "low"}],
        queue_health_snapshot={
            "queue_pressure": "high",
            "recommended_followup": "Prioritize stale blocked items",
            "stale_items": [
                {
                    "item_id": "q-case-aabb",
                    "scope_type": "case",
                    "scope_id": "AA:BB:CC:DD:EE:01",
                    "queue_state": "blocked",
                    "age_minutes": 420,
                }
            ],
        },
        generated_at="2026-04-18 18:00:00",
    )

    assert outcomes

    scope_types = {r["scope_type"] for r in outcomes}
    assert {"device", "case", "cluster", "campaign", "evidence_pack", "queue_item"}.issubset(scope_types)

    required = {
        "outcome_id",
        "scope_type",
        "scope_id",
        "source_action",
        "source_playbook",
        "queue_state_before",
        "queue_state_after",
        "resolution_state",
        "outcome_label",
        "effectiveness",
        "reopened",
        "created_at",
    }
    for row in outcomes:
        assert required.issubset(set(row.keys()))

    labels = {r["outcome_label"] for r in outcomes}
    assert labels.intersection(
        {
            "resolved_cleanly",
            "resolved_but_returned",
            "needs_more_review",
            "false_positive",
            "stabilized",
            "escalated",
        }
    )


def test_summarize_operator_outcomes_sections_exist():
    summary = summarize_operator_outcomes(
        [
            {
                "outcome_id": "outcome-device-aabb-1",
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "source_action": "Run review triage workflow",
                "source_playbook": "pb-review-triage",
                "queue_state_before": "blocked",
                "queue_state_after": "in_review",
                "resolution_state": "needs_action",
                "outcome_label": "needs_more_review",
                "effectiveness": 42,
                "reopened": False,
                "created_at": "2026-04-18 18:00:00",
            },
            {
                "outcome_id": "outcome-case-aabb-1",
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "source_action": "Close case and monitor",
                "source_playbook": "pb-close-monitor",
                "queue_state_before": "resolved",
                "queue_state_after": "in_review",
                "resolution_state": "reopened",
                "outcome_label": "resolved_but_returned",
                "effectiveness": 30,
                "reopened": True,
                "created_at": "2026-04-18 18:05:00",
            },
        ]
    )

    assert "operator_outcomes" in summary
    assert "most_effective_actions" in summary
    assert "reopened_items" in summary
    assert "weak_recommendations" in summary
    assert len(summary["operator_outcomes"]) == 2
    assert len(summary["reopened_items"]) == 1
