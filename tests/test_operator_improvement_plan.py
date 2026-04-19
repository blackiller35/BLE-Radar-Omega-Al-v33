"""Unit tests for operator improvement plan / corrective guidance system."""

from ble_radar.history.operator_improvement_plan import (
    build_operator_improvement_plan_records,
    summarize_operator_improvement_plans,
)


def test_build_operator_improvement_plan_records_required_fields():
    """Test that build_operator_improvement_plan_records returns records with required fields."""
    quality_records = [
        {
            "quality_id": "quality-device-device123",
            "scope_type": "device",
            "scope_id": "device123",
            "resolution_quality": "fragile",
            "stability_score": 45,
            "reopen_risk": 65,
            "supporting_factors": ["closed"],
            "weak_factors": ["previously_reopened", "weak_closure_confidence"],
            "evaluated_at": "2024-01-01 12:00:00",
        }
    ]

    closure_records = [
        {
            "closure_id": "closure-123",
            "scope_id": "device123",
            "closed_at": "2024-01-01 11:00:00",
            "closure_confidence": 0.6,
            "disposition": "resolved",
        }
    ]

    lineage_records = [
        {
            "lineage_id": "lineage-device-device123",
            "scope_type": "device",
            "scope_id": "device123",
            "cycle_count": 2,
            "opened_count": 1,
            "reopened_count": 1,
            "closure_count": 1,
            "escalation_count": 0,
        }
    ]

    records = build_operator_improvement_plan_records(
        plan_scopes=[
            {
                "scope_type": "device",
                "scope_id": "device123",
            }
        ],
        quality_records=quality_records,
        lineage_records=lineage_records,
        closure_packages=closure_records,
        generated_at="2024-01-01 12:30:00",
    )

    assert len(records) > 0, "Expected at least one improvement plan record"
    record = records[0]

    # Verify all required fields are present
    required_fields = {
        "plan_id",
        "scope_type",
        "scope_id",
        "quality_id",
        "resolution_quality",
        "priority_level",
        "improvement_goal",
        "recommended_actions",
        "supporting_rationale",
        "blocking_gaps",
        "expected_stability_gain",
        "followup_mode",
        "created_at",
    }

    for field in required_fields:
        assert field in record, f"Missing required field: {field}"

    # Verify field types
    assert isinstance(record["plan_id"], str)
    assert isinstance(record["scope_type"], str)
    assert isinstance(record["scope_id"], str)
    assert isinstance(record["priority_level"], str)
    assert isinstance(record["improvement_goal"], str)
    assert isinstance(record["recommended_actions"], list)
    assert isinstance(record["supporting_rationale"], str)
    assert isinstance(record["blocking_gaps"], list)
    assert isinstance(record["expected_stability_gain"], int)
    assert isinstance(record["followup_mode"], str)
    assert isinstance(record["created_at"], str)

    # Verify value ranges
    assert record["priority_level"] in {"critical", "high", "medium", "low", "maintenance"}
    assert 0 <= record["expected_stability_gain"] <= 100
    assert len(record["recommended_actions"]) > 0
    assert len(record["recommended_actions"]) <= 6
    assert record["improvement_goal"] in {
        "collect_more_evidence",
        "increase_monitoring",
        "tighten_closure",
        "request_specialist_review",
        "improve_followup",
        "reclassify_scope",
    }


def test_summarize_operator_improvement_plans_sections_exist():
    """Test that summarize_operator_improvement_plans returns all expected sections."""
    plan_records = [
        {
            "plan_id": "plan-device-device1",
            "scope_type": "device",
            "scope_id": "device1",
            "quality_id": "quality-device-device1",
            "resolution_quality": "fragile",
            "priority_level": "high",
            "improvement_goal": "tighten_closure",
            "recommended_actions": ["gather_missing_evidence", "increase_confidence_threshold"],
            "supporting_rationale": "Multiple risk factors detected.",
            "blocking_gaps": ["missing_evidence_data", "confidence_validation_needed"],
            "expected_stability_gain": 22,
            "current_stability_score": 48,
            "followup_mode": "enhanced_monitoring",
            "created_at": "2024-01-01 12:00:00",
        },
        {
            "plan_id": "plan-device-device2",
            "scope_type": "device",
            "scope_id": "device2",
            "quality_id": "quality-device-device2",
            "resolution_quality": "likely_to_reopen",
            "priority_level": "critical",
            "improvement_goal": "request_specialist_review",
            "recommended_actions": ["analyze_reopen_patterns", "implement_persistent_monitoring"],
            "supporting_rationale": "Item has reopened multiple times.",
            "blocking_gaps": ["pattern_recurrence_unresolved"],
            "expected_stability_gain": 20,
            "current_stability_score": 35,
            "followup_mode": "specialist_followup",
            "created_at": "2024-01-01 12:00:00",
        },
        {
            "plan_id": "plan-case-case1",
            "scope_type": "case",
            "scope_id": "case1",
            "quality_id": "quality-case-case1",
            "resolution_quality": "mostly_stable",
            "priority_level": "low",
            "improvement_goal": "improve_followup",
            "recommended_actions": ["extend_monitoring_period", "validate_stability"],
            "supporting_rationale": "Item is mostly stable.",
            "blocking_gaps": [],
            "expected_stability_gain": 12,
            "current_stability_score": 70,
            "followup_mode": "routine_monitoring",
            "created_at": "2024-01-01 12:00:00",
        },
    ]

    summary = summarize_operator_improvement_plans(plan_records)

    # Verify summary sections exist
    assert "priority_counts" in summary
    assert "improvement_plans" in summary
    assert "fragile_closures_needing_action" in summary
    assert "top_blocking_gaps" in summary
    assert "expected_stability_gains" in summary
    assert "suggested_followup_modes" in summary

    # Verify priority counts
    priority_counts = summary["priority_counts"]
    assert priority_counts["critical"] == 1
    assert priority_counts["high"] == 1
    assert priority_counts["low"] == 1

    # Verify improvement plans (should include critical and high)
    assert len(summary["improvement_plans"]) >= 1
    for plan in summary["improvement_plans"]:
        assert plan["priority_level"] in {"critical", "high"}

    # Verify fragile closures needing action
    assert len(summary["fragile_closures_needing_action"]) >= 1
    for closure in summary["fragile_closures_needing_action"]:
        assert closure["resolution_quality"] in {"fragile", "likely_to_reopen"}

    # Verify blocking gaps are aggregated
    assert len(summary["top_blocking_gaps"]) >= 1
    for gap, count in summary["top_blocking_gaps"]:
        assert isinstance(gap, str)
        assert isinstance(count, int)
        assert count >= 1

    # Verify stability gains are sorted
    assert len(summary["expected_stability_gains"]) >= 1
    for gain in summary["expected_stability_gains"]:
        assert "scope_type" in gain
        assert "scope_id" in gain
        assert "current_stability" in gain
        assert "projected_stability" in gain
        assert gain["projected_stability"] >= gain["current_stability"]

    # Verify follow-up modes
    assert len(summary["suggested_followup_modes"]) >= 1
    for followup in summary["suggested_followup_modes"]:
        assert "scope_type" in followup
        assert "scope_id" in followup
        assert "followup_mode" in followup
        assert "priority" in followup


def test_build_operator_improvement_plan_records_scope_filter_and_supported_types():
    quality_records = [
        {
            "quality_id": "quality-device-d1",
            "scope_type": "device",
            "scope_id": "d1",
            "resolution_quality": "fragile",
            "stability_score": 45,
            "reopen_risk": 62,
            "weak_factors": ["insufficient_evidence"],
        },
        {
            "quality_id": "quality-case-c1",
            "scope_type": "case",
            "scope_id": "c1",
            "resolution_quality": "likely_to_reopen",
            "stability_score": 38,
            "reopen_risk": 82,
            "weak_factors": ["multiple_reopens"],
        },
        {
            "quality_id": "quality-cluster-cl1",
            "scope_type": "cluster",
            "scope_id": "cl1",
            "resolution_quality": "mostly_stable",
            "stability_score": 68,
            "reopen_risk": 30,
            "weak_factors": [],
        },
        {
            "quality_id": "quality-campaign-camp1",
            "scope_type": "campaign",
            "scope_id": "camp1",
            "resolution_quality": "fragile",
            "stability_score": 50,
            "reopen_risk": 55,
            "weak_factors": ["resolution_not_durable"],
        },
        {
            "quality_id": "quality-evidence_pack-p1",
            "scope_type": "evidence_pack",
            "scope_id": "p1",
            "resolution_quality": "fragile",
            "stability_score": 52,
            "reopen_risk": 58,
            "weak_factors": ["weak_closure_confidence"],
        },
        {
            "quality_id": "quality-queue_item-q1",
            "scope_type": "queue_item",
            "scope_id": "q1",
            "resolution_quality": "fragile",
            "stability_score": 54,
            "reopen_risk": 50,
            "weak_factors": [],
        },
    ]

    plans = build_operator_improvement_plan_records(
        plan_scopes=[
            {"scope_type": "device", "scope_id": "d1"},
            {"scope_type": "case", "scope_id": "c1"},
            {"scope_type": "cluster", "scope_id": "cl1"},
            {"scope_type": "campaign", "scope_id": "camp1"},
            {"scope_type": "evidence_pack", "scope_id": "p1"},
            {"scope_type": "queue_item", "scope_id": "q1"},
        ],
        quality_records=quality_records,
        recommendation_tuning=[
            {
                "scope_type": "queue_item",
                "scope_id": "q1",
                "confidence_level": "low",
                "effectiveness_score": 35,
            }
        ],
        pattern_library=[
            {
                "pattern_type": "cluster",
                "scope_id": "cl1",
                "pattern_id": "pattern-cluster-cl1",
            }
        ],
        session_journal={
            "handoff_summary": "watch campaign:camp1",
            "next_shift_priorities": ["Follow up on queue_item:q1"],
        },
    )

    assert len(plans) == 6
    assert {p["scope_type"] for p in plans} == {"device", "case", "cluster", "campaign", "evidence_pack", "queue_item"}
    assert all(p["improvement_goal"] in {
        "collect_more_evidence",
        "increase_monitoring",
        "tighten_closure",
        "request_specialist_review",
        "improve_followup",
        "reclassify_scope",
    } for p in plans)

    filtered = build_operator_improvement_plan_records(
        plan_scopes=[{"scope_type": "case", "scope_id": "c1"}],
        quality_records=quality_records,
    )
    assert len(filtered) == 1
    assert filtered[0]["scope_type"] == "case"
    assert filtered[0]["scope_id"] == "c1"
