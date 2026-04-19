"""Tests for operator_post_closure_monitoring_policy module."""
import pytest
from ble_radar.history.operator_post_closure_monitoring_policy import (
    build_operator_post_closure_monitoring_policies,
    summarize_operator_post_closure_monitoring_policies,
)


def test_build_operator_post_closure_monitoring_policies_required_fields():
    """Test that all required fields are present in monitoring policy output."""
    closure_packages = [
        {
            "closure_id": "closure-device-test123-123",
            "scope_type": "device",
            "scope_id": "test123",
            "final_disposition": "resolved",
            "final_risk_level": "medium",
            "followup_mode": "monitor",
            "archive_recommendation": "keep_active",
        }
    ]

    monitoring_scopes = [
        {
            "scope_type": "device",
            "scope_id": "test123",
        }
    ]

    policies = build_operator_post_closure_monitoring_policies(
        monitoring_scopes,
        closure_packages=closure_packages,
    )

    assert len(policies) > 0
    policy = policies[0]

    # Check all required fields
    required_fields = [
        "policy_id",
        "scope_type",
        "scope_id",
        "closure_id",
        "monitoring_mode",
        "monitoring_reason",
        "watch_signals",
        "reopen_triggers",
        "review_window",
        "priority_after_closure",
        "created_at",
    ]

    for field in required_fields:
        assert field in policy, f"Missing required field: {field}"
        assert policy[field] is not None, f"Field {field} is None"

    # Verify field types
    assert isinstance(policy["policy_id"], str)
    assert isinstance(policy["scope_type"], str)
    assert isinstance(policy["scope_id"], str)
    assert isinstance(policy["monitoring_mode"], str)
    assert isinstance(policy["watch_signals"], list)
    assert isinstance(policy["reopen_triggers"], list)


def test_summarize_operator_post_closure_monitoring_policies_sections_exist():
    """Test that all summary sections are present and properly formatted."""
    policies = [
        {
            "policy_id": "policy-device-test1-123",
            "scope_type": "device",
            "scope_id": "test1",
            "monitoring_mode": "watch_for_recurrence",
            "monitoring_reason": "escalated",
            "watch_signals": ["pattern:malware"],
            "reopen_triggers": ["signal_pattern_detected"],
            "review_window": "immediate",
            "priority_after_closure": "high",
            "created_at": "2026-04-18 10:00:00",
        },
        {
            "policy_id": "policy-device-test2-123",
            "scope_type": "device",
            "scope_id": "test2",
            "monitoring_mode": "scheduled_recheck",
            "monitoring_reason": "needs_more_data",
            "watch_signals": ["outcome:weak_confidence"],
            "reopen_triggers": ["scheduled_review_time_reached"],
            "review_window": "7_days",
            "priority_after_closure": "medium",
            "created_at": "2026-04-18 10:00:00",
        },
        {
            "policy_id": "policy-device-test3-123",
            "scope_type": "device",
            "scope_id": "test3",
            "monitoring_mode": "high_attention_post_closure",
            "monitoring_reason": "specialist_needs_followup",
            "watch_signals": ["pattern:recurring_behavior"],
            "reopen_triggers": ["signal_pattern_detected", "new_alert_on_scope"],
            "review_window": "immediate",
            "priority_after_closure": "critical",
            "created_at": "2026-04-18 10:00:00",
        },
    ]

    summary = summarize_operator_post_closure_monitoring_policies(policies)

    # Check all required summary sections
    required_sections = [
        "monitoring_policies",
        "watch_for_recurrence",
        "scheduled_rechecks",
        "high_attention",
        "recent_reopen_triggers",
    ]

    for section in required_sections:
        assert section in summary, f"Missing summary section: {section}"
        assert isinstance(summary[section], list), f"Section {section} should be a list"

    # Verify basic categorization
    assert len(summary["monitoring_policies"]) == 3
    assert len(summary["watch_for_recurrence"]) >= 1
    assert len(summary["scheduled_rechecks"]) >= 1
    assert len(summary["high_attention"]) >= 1
