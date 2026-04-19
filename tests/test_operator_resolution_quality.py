"""Unit tests for operator resolution quality / stability assessment system."""
import pytest

from ble_radar.history.operator_resolution_quality import (
    build_operator_resolution_quality_records,
    summarize_operator_resolution_quality,
)


def test_build_operator_resolution_quality_records_required_fields():
    """Test that build_operator_resolution_quality_records returns records with required fields."""
    lineage_records = [
        {
            "lineage_id": "lineage-device-device123",
            "scope_type": "device",
            "scope_id": "device123",
            "cycle_count": 2,
            "opened_count": 1,
            "reopened_count": 1,
            "closure_count": 2,
            "escalation_count": 0,
            "last_trigger_type": "pattern_recurred",
            "updated_at": "2024-01-01 12:00:00",
        }
    ]

    closure_records = [
        {
            "closure_id": "closure-123",
            "scope_id": "device123",
            "closed_at": "2024-01-01 11:00:00",
            "closure_confidence": 0.85,
            "disposition": "resolved",
        }
    ]

    outcome_records = [
        {
            "scope_id": "device123",
            "outcome_label": "resolved_cleanly",
            "confidence_level": "high",
            "weak_confidence": False,
        }
    ]

    reopen_records = [
        {
            "scope_id": "device123",
            "trigger_type": "pattern_recurred",
        }
    ]

    monitoring_records = [
        {
            "scope_id": "device123",
            "monitoring_mode": "watch_for_recurrence",
            "monitoring_triggered": False,
        }
    ]

    feedback_records = [
        {
            "scope_id": "device123",
            "feedback_type": "confirmed_pattern",
        }
    ]

    pattern_records = [
        {
            "pattern_id": "pattern-001",
            "title": "Known Malware",
        }
    ]

    pattern_matches = [
        {
            "scope_id": "device123",
            "pattern_id": "pattern-001",
        }
    ]

    queue_records = [
        {
            "scope_id": "device123",
            "item_id": "item-456",
            "queue_state": "resolved",
        }
    ]

    records = build_operator_resolution_quality_records(
        quality_scopes=[
            {
                "scope_type": "device",
                "scope_id": "device123",
            }
        ],
        lineage_records=lineage_records,
        closure_packages=closure_records,
        operator_outcomes=outcome_records,
        reopen_policy_records=reopen_records,
        post_closure_monitoring_policies=monitoring_records,
        escalation_feedback=feedback_records,
        pattern_library=pattern_records,
        pattern_matches=pattern_matches,
        operator_queue_context=queue_records,
        generated_at="2024-01-01 12:30:00",
    )

    assert len(records) > 0, "Expected at least one quality record"
    record = records[0]

    # Verify all required fields are present
    required_fields = {
        "quality_id",
        "scope_type",
        "scope_id",
        "lineage_id",
        "closure_id",
        "resolution_quality",
        "stability_score",
        "reopen_risk",
        "supporting_factors",
        "weak_factors",
        "recommended_improvement",
        "evaluated_at",
    }

    for field in required_fields:
        assert field in record, f"Missing required field: {field}"

    # Verify field types
    assert isinstance(record["quality_id"], str)
    assert isinstance(record["scope_type"], str)
    assert isinstance(record["scope_id"], str)
    assert isinstance(record["resolution_quality"], str)
    assert isinstance(record["stability_score"], int)
    assert isinstance(record["reopen_risk"], int)
    assert isinstance(record["supporting_factors"], list)
    assert isinstance(record["weak_factors"], list)
    assert isinstance(record["recommended_improvement"], str)
    assert isinstance(record["evaluated_at"], str)

    # Verify value ranges
    assert 0 <= record["stability_score"] <= 100
    assert 0 <= record["reopen_risk"] <= 100
    assert record["resolution_quality"] in {
        "durable",
        "mostly_stable",
        "fragile",
        "likely_to_reopen",
        "insufficient_resolution",
    }


def test_summarize_operator_resolution_quality_sections_exist():
    """Test that summarize_operator_resolution_quality returns all expected sections."""
    quality_records = [
        {
            "quality_id": "quality-device-device1",
            "scope_type": "device",
            "scope_id": "device1",
            "lineage_id": "lineage-device-device1",
            "closure_id": "closure-1",
            "resolution_quality": "durable",
            "stability_score": 85,
            "reopen_risk": 5,
            "supporting_factors": ["closed", "no_reopens"],
            "weak_factors": [],
            "recommended_improvement": "maintain_current_process",
            "evaluated_at": "2024-01-01 12:00:00",
        },
        {
            "quality_id": "quality-device-device2",
            "scope_type": "device",
            "scope_id": "device2",
            "lineage_id": "lineage-device-device2",
            "closure_id": "closure-2",
            "resolution_quality": "fragile",
            "stability_score": 40,
            "reopen_risk": 65,
            "supporting_factors": ["closed"],
            "weak_factors": ["previously_reopened", "weak_closure_confidence"],
            "recommended_improvement": "extended_monitoring_required",
            "evaluated_at": "2024-01-01 12:00:00",
        },
        {
            "quality_id": "quality-case-case1",
            "scope_type": "case",
            "scope_id": "case1",
            "lineage_id": "lineage-case-case1",
            "closure_id": "closure-3",
            "resolution_quality": "likely_to_reopen",
            "stability_score": 25,
            "reopen_risk": 80,
            "supporting_factors": [],
            "weak_factors": ["multiple_reopens", "insufficient_evidence"],
            "recommended_improvement": "proactive_monitoring_or_early_reopen",
            "evaluated_at": "2024-01-01 12:00:00",
        },
    ]

    summary = summarize_operator_resolution_quality(quality_records)

    # Verify summary sections exist
    assert "resolution_quality" in summary
    assert "durable_closures" in summary
    assert "fragile_closures" in summary
    assert "likely_reopeners" in summary
    assert "improvement_suggestions" in summary

    # Verify resolution_quality summary
    quality_counts = summary["resolution_quality"]
    assert "durable" in quality_counts
    assert "mostly_stable" in quality_counts
    assert "fragile" in quality_counts
    assert "likely_to_reopen" in quality_counts
    assert "insufficient_resolution" in quality_counts

    assert quality_counts["durable"] == 1
    assert quality_counts["fragile"] == 1
    assert quality_counts["likely_to_reopen"] == 1

    # Verify categorization
    assert len(summary["durable_closures"]) >= 1, "Expected at least one durable closure"
    assert len(summary["fragile_closures"]) >= 1, "Expected at least one fragile/at-risk closure"
    assert len(summary["likely_reopeners"]) >= 1, "Expected at least one likely reopener"
    assert len(summary["improvement_suggestions"]) >= 1, "Expected at least one improvement suggestion"

    # Verify durable closures only include durable items
    for item in summary["durable_closures"]:
        assert item["resolution_quality"] == "durable"

    # Verify fragile closures include fragile or likely_to_reopen
    for item in summary["fragile_closures"]:
        assert item["resolution_quality"] in {"fragile", "likely_to_reopen"}

    # Verify likely reopeners have high reopen_risk
    for item in summary["likely_reopeners"]:
        assert item["reopen_risk"] >= 70

    # Verify improvement suggestions are structured
    for item in summary["improvement_suggestions"]:
        assert "scope_type" in item
        assert "scope_id" in item
        assert "recommendation" in item
        assert "quality" in item
