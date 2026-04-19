"""Dashboard integration test for post-closure monitoring policy panel."""
import pytest
from ble_radar import dashboard


def test_dashboard_contains_operator_post_closure_monitoring_policy_panel(monkeypatch):
    """Test that dashboard renders the post-closure monitoring policy panel correctly."""
    monkeypatch.setattr(dashboard, "load_scan_history", lambda: [])
    monkeypatch.setattr(dashboard, "load_last_scan", lambda: [])
    monkeypatch.setattr(dashboard, "load_registry", lambda: {})
    monkeypatch.setattr(dashboard, "load_watch_cases", lambda: {})
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "list_cases", lambda: [])
    monkeypatch.setattr(dashboard, "latest_session_diff", lambda: {})
    monkeypatch.setattr(dashboard, "latest_session_overview", lambda: {})
    monkeypatch.setattr(dashboard, "build_session_catalog", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "build_artifact_index", lambda: {})
    monkeypatch.setattr(dashboard, "build_investigation_profile", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_operator_timeline", lambda *args, **kwargs: {"events": []})
    monkeypatch.setattr(dashboard, "recent_timeline_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "triage_device_list", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "recommend_operator_playbook", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "evaluate_operator_rules", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_rule_results", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "load_automation_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "build_operator_briefing", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_operator_alerts", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "load_alert_log", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_alerts", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_correlation_clusters", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_clusters", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "load_campaign_records", lambda: [])
    monkeypatch.setattr(dashboard, "build_campaign_lifecycle", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_campaigns", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_evidence_packs", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "load_evidence_packs", lambda: [])
    monkeypatch.setattr(dashboard, "summarize_evidence_packs", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_operator_escalation_packages", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_operator_escalation_packages", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_operator_escalation_feedback_records", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_operator_escalation_feedback", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_operator_closure_packages", lambda *args, **kwargs: [
        {
            "closure_id": "closure-device-test-123",
            "scope_type": "device",
            "scope_id": "test",
            "final_disposition": "resolved",
            "final_risk_level": "medium",
            "followup_mode": "monitor",
            "archive_recommendation": "keep_active",
        }
    ])
    monkeypatch.setattr(dashboard, "summarize_operator_closure_packages", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_operator_post_closure_monitoring_policies", lambda *args, **kwargs: [
        {
            "policy_id": "policy-device-test-123",
            "scope_type": "device",
            "scope_id": "test",
            "monitoring_mode": "watch_for_recurrence",
            "review_window": "immediate",
            "priority_after_closure": "high",
        }
    ])
    monkeypatch.setattr(dashboard, "summarize_operator_post_closure_monitoring_policies", lambda *args, **kwargs: {
        "monitoring_policies": [
            {
                "policy_id": "policy-device-test-123",
                "scope_type": "device",
                "scope_id": "test",
                "monitoring_mode": "watch_for_recurrence",
                "review_window": "immediate",
                "priority_after_closure": "high",
            }
        ],
        "watch_for_recurrence": [
            {
                "scope_type": "device",
                "scope_id": "test",
                "monitoring_reason": "standard_closure_review",
                "watch_signals": ["pattern:test"],
            }
        ],
        "scheduled_rechecks": [],
        "high_attention": [],
        "recent_reopen_triggers": [],
    })
    monkeypatch.setattr(dashboard, "build_operator_outcomes", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_operator_outcomes", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_operator_queue", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_operator_queue", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_queue_health_snapshot", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "summarize_queue_health", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_operator_session_journal", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "summarize_operator_session_journal", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_recommendation_tuning_profiles", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_recommendation_tuning_profiles", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_review_readiness_profiles", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_review_readiness", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_operator_pattern_records", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "match_scopes_to_patterns", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_operator_pattern_library", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "recommend_operator_playbook", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_session_movement", lambda *args, **kwargs: {})

    # Render the dashboard
    html = dashboard.render_dashboard_html([], "2026-04-18 10:00:00")

    # Verify panel title and key sections exist
    assert "Post-Closure Monitoring / Recurrence Watch" in html
    assert "Watch for recurrence" in html
    assert "Scheduled rechecks" in html
    assert "High attention after closure" in html
    assert "Recent reopen triggers" in html
