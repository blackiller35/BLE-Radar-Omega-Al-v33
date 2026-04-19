"""Dashboard integration test for lifecycle lineage / multi-cycle history panel."""
from ble_radar import dashboard


def test_dashboard_contains_operator_lifecycle_lineage_panel(monkeypatch):
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
    monkeypatch.setattr(dashboard, "build_operator_closure_packages", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_operator_closure_packages", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_operator_post_closure_monitoring_policies", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_operator_post_closure_monitoring_policies", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_operator_reopen_records", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_operator_reopen_records", lambda *args, **kwargs: {})
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
    monkeypatch.setattr(dashboard, "build_operator_lifecycle_lineage_records", lambda *args, **kwargs: [
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
            "updated_at": "2026-04-19 10:00:00",
        }
    ])
    monkeypatch.setattr(dashboard, "summarize_operator_lifecycle_lineage", lambda *args, **kwargs: {
        "lifecycle_lineage": [
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
                "updated_at": "2026-04-19 10:00:00",
            }
        ],
        "repeated_reopeners": [
            {
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "reopened_count": 2,
                "last_trigger_type": "pattern_recurred",
            }
        ],
        "recurring_triggers": [
            {
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "last_trigger_type": "pattern_recurred",
                "reopened_count": 2,
            }
        ],
        "multi_cycle_cases": [
            {
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "cycle_count": 3,
                "timeline_summary": "opened=2 | escalations=1 | closures=2 | reopens=2",
            }
        ],
        "stabilized_after_reopen": [
            {
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "current_lifecycle_state": "stabilized_after_reopen",
                "updated_at": "2026-04-19 10:00:00",
            }
        ],
    })
    monkeypatch.setattr(dashboard, "build_session_movement", lambda *args, **kwargs: {})

    html = dashboard.render_dashboard_html([], "2026-04-19 10:00:00")

    assert "Lifecycle Lineage / Multi-Cycle History" in html
    assert "Lifecycle lineage" in html
    assert "Repeated reopeners" in html
    assert "Recurring triggers" in html
    assert "Multi-cycle cases" in html
    assert "Stabilized after reopen" in html
