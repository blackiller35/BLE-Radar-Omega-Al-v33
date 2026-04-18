"""Tests for lightweight recommendation tuning / operator confidence system (step 22)."""
from __future__ import annotations

from ble_radar.history.recommendation_tuning import (
    build_recommendation_tuning_profiles,
    summarize_recommendation_tuning_profiles,
)


def test_build_recommendation_tuning_profiles_required_fields_and_confidence_levels():
    outcomes = [
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
            "outcome_id": "outcome-device-aabb-2",
            "scope_type": "device",
            "scope_id": "AA:BB:CC:DD:EE:01",
            "source_action": "Run review triage workflow",
            "source_playbook": "pb-review-triage",
            "queue_state_before": "in_review",
            "queue_state_after": "resolved",
            "resolution_state": "closed",
            "outcome_label": "resolved_cleanly",
            "effectiveness": 82,
            "reopened": False,
            "created_at": "2026-04-18 18:03:00",
        },
        {
            "outcome_id": "outcome-campaign-aabb-1",
            "scope_type": "campaign",
            "scope_id": "campaign-aabb",
            "source_action": "Review campaign lifecycle",
            "source_playbook": "pb-watch-monitor",
            "queue_state_before": "in_review",
            "queue_state_after": "in_review",
            "resolution_state": "monitoring",
            "outcome_label": "stabilized",
            "effectiveness": 70,
            "reopened": True,
            "created_at": "2026-04-18 18:05:00",
        },
    ]

    profiles = build_recommendation_tuning_profiles(
        outcomes,
        playbook_recommendations=[
            {
                "address": "AA:BB:CC:DD:EE:01",
                "playbook_id": "pb-review-triage",
                "recommended_action": "Run review triage workflow",
            },
            {
                "address": "AA:BB:CC:DD:EE:01",
                "playbook_id": "pb-critical-pack",
                "recommended_action": "Escalate and generate incident pack",
            },
        ],
        rule_results=[
            {
                "address": "AA:BB:CC:DD:EE:01",
                "requires_confirmation": True,
            }
        ],
        alerts=[{"device_address": "AA:BB:CC:DD:EE:01", "severity": "critical"}],
        queue_items=[
            {
                "item_id": "q-device-aabb",
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "queue_state": "blocked",
            },
            {
                "item_id": "q-campaign-aabb",
                "scope_type": "campaign",
                "scope_id": "campaign-aabb",
                "queue_state": "in_review",
            },
        ],
        campaigns=[
            {
                "campaign_id": "campaign-aabb",
                "status": "expanding",
                "risk_level": "high",
            }
        ],
        evidence_packs=[
            {
                "pack_id": "pack-device-aabb",
                "risk_level": "high",
            }
        ],
        generated_at="2026-04-18 18:10:00",
    )

    assert profiles

    required = {
        "recommendation_id",
        "source_playbook",
        "scope_type",
        "success_count",
        "failure_count",
        "reopened_count",
        "confidence_level",
        "effectiveness_score",
        "usage_notes",
        "recommended_rank_adjustment",
    }
    for row in profiles:
        assert required.issubset(set(row.keys()))

    assert {r["confidence_level"] for r in profiles}.issubset({"high", "medium", "low", "uncertain"})
    assert any(r["source_playbook"] == "pb-review-triage" for r in profiles)


def test_summarize_recommendation_tuning_profiles_sections_exist():
    summary = summarize_recommendation_tuning_profiles(
        [
            {
                "recommendation_id": "rectune-pb-review-triage-aabb",
                "source_playbook": "pb-review-triage",
                "scope_type": "device",
                "success_count": 2,
                "failure_count": 1,
                "reopened_count": 0,
                "confidence_level": "medium",
                "effectiveness_score": 66,
                "usage_notes": "stable",
                "recommended_rank_adjustment": 1,
            },
            {
                "recommendation_id": "rectune-pb-critical-pack-aabb",
                "source_playbook": "pb-critical-pack",
                "scope_type": "device",
                "success_count": 0,
                "failure_count": 2,
                "reopened_count": 1,
                "confidence_level": "low",
                "effectiveness_score": 34,
                "usage_notes": "manual review",
                "recommended_rank_adjustment": -2,
            },
        ]
    )

    assert "recommendation_confidence" in summary
    assert "most_effective_playbooks" in summary
    assert "weak_recommendations" in summary
    assert "needs_manual_review" in summary
    assert len(summary["recommendation_confidence"]) == 2
    assert len(summary["weak_recommendations"]) == 1
    assert len(summary["needs_manual_review"]) == 1
