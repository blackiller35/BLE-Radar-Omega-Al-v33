"""Dashboard integration test for controlled reopen policy panel."""
from ble_radar import dashboard


def test_dashboard_contains_operator_reopen_policy_panel(monkeypatch):
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
    monkeypatch.setattr(dashboard, "build_operator_reopen_records", lambda *args, **kwargs: [
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
            "carry_forward_context": {},
            "reopen_count": 2,
            "reopened_at": "2026-04-19 10:00:00",
        }
    ])
    monkeypatch.setattr(dashboard, "summarize_operator_reopen_records", lambda *args, **kwargs: {
        "reopen_records": [
            {
                "reopen_id": "reopen-case-aabb-1",
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "trigger_type": "pattern_recurred",
                "trigger_summary": "trigger=pattern_recurred",
                "reopen_reason": "known_pattern_recurred_on_closed_scope",
                "reopen_priority": "high",
                "target_queue_state": "in_review",
                "reopen_count": 2,
            }
        ],
        "reopened_cases": [{"scope_type": "case", "scope_id": "AA:BB:CC:DD:EE:01"}],
        "recent_reopen_triggers": [{"scope_type": "case", "scope_id": "AA:BB:CC:DD:EE:01", "trigger_type": "pattern_recurred", "trigger_summary": "trigger=pattern_recurred"}],
        "returned_to_queue": [{"scope_type": "case", "scope_id": "AA:BB:CC:DD:EE:01", "target_queue_state": "in_review"}],
        "repeated_reopeners": [{"scope_type": "case", "scope_id": "AA:BB:CC:DD:EE:01", "reopen_count": 2}],
        "high_priority_reopens": [{"scope_type": "case", "scope_id": "AA:BB:CC:DD:EE:01", "reopen_priority": "high"}],
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
    monkeypatch.setattr(dashboard, "build_session_movement", lambda *args, **kwargs: {})

    html = dashboard.render_dashboard_html([], "2026-04-19 10:00:00")

    assert "Controlled Reopen Policy / Case Reopening" in html
    assert "Reopened cases" in html
    assert "Recent reopen triggers" in html
    assert "Returned to queue" in html
    assert "Repeated reopeners" in html
    assert "High priority reopens" in html
