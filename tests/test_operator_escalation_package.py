"""Tests for lightweight operator escalation package / transmission system (step 26)."""
from __future__ import annotations

from ble_radar.history.operator_escalation_package import (
    build_operator_escalation_packages,
    summarize_operator_escalation_packages,
)


def test_build_operator_escalation_packages_required_fields():
    packages = build_operator_escalation_packages(
        [
            {
                "scope_type": "queue_item",
                "scope_id": "q-device-aabb",
                "queue_state": "blocked",
            },
            {
                "scope_type": "campaign",
                "scope_id": "campaign-aabb",
                "status": "expanding",
            },
        ],
        alerts=[{"device_address": "AA:BB:CC:DD:EE:01", "scope_id": "q-device-aabb"}],
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
        queue_health_snapshot={
            "queue_pressure": "high",
            "stale_items": [{"item_id": "q-device-aabb", "age_minutes": 300}],
        },
        readiness_profiles=[
            {
                "scope_type": "queue_item",
                "scope_id": "q-device-aabb",
                "readiness_state": "needs_more_data",
            }
        ],
        evidence_packs=[
            {
                "pack_id": "pack-device-aabb",
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
            }
        ],
        campaigns=[{"campaign_id": "campaign-aabb", "status": "expanding"}],
        pattern_matches=[{"scope_type": "queue_item", "scope_id": "q-device-aabb", "pattern_id": "pattern-queue"}],
        session_journal={
            "handoff_summary": "shift handoff ready",
            "next_shift_priorities": ["unblock queue"],
        },
        generated_at="2026-04-18 20:00:00",
    )

    assert packages
    required = {
        "escalation_id",
        "scope_type",
        "scope_id",
        "escalation_reason",
        "priority",
        "supporting_signals",
        "actions_already_taken",
        "open_risks",
        "recommended_next_owner",
        "handoff_payload",
        "created_at",
    }
    assert required.issubset(set(packages[0].keys()))


def test_summarize_operator_escalation_packages_sections_exist():
    summary = summarize_operator_escalation_packages(
        [
            {
                "escalation_id": "escalation-device-aabb-1",
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "escalation_reason": "weak_recommendation_confidence",
                "priority": "high",
                "supporting_signals": ["alerts=1"],
                "actions_already_taken": ["manual_followup"],
                "open_risks": ["low_recommendation_confidence"],
                "recommended_next_owner": "specialist_review_team",
                "handoff_payload": {"summary": "ok"},
                "created_at": "2026-04-18 20:00:00",
            }
        ]
    )

    assert "escalation_packages" in summary
    assert "ready_to_escalate" in summary
    assert "specialist_review_needed" in summary
    assert "high_risk_open_items" in summary
    assert "recent_escalations" in summary
    assert len(summary["ready_to_escalate"]) == 1
    assert len(summary["specialist_review_needed"]) == 1
