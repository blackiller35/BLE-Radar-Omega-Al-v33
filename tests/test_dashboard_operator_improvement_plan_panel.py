"""Integration test for operator improvement plan panel in dashboard."""
from ble_radar import dashboard


def test_dashboard_contains_operator_improvement_plan_panel(monkeypatch):
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
    monkeypatch.setattr(dashboard, "build_operator_lifecycle_lineage_records", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_operator_lifecycle_lineage", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_operator_resolution_quality_records", lambda *args, **kwargs: [
        {
            "quality_id": "quality-device-test",
            "scope_type": "device",
            "scope_id": "test_device",
            "resolution_quality": "fragile",
            "stability_score": 45,
            "reopen_risk": 65,
            "supporting_factors": ["closed"],
            "weak_factors": ["previously_reopened"],
            "evaluated_at": "2024-01-01 12:00:00",
        }
    ])
    monkeypatch.setattr(dashboard, "summarize_operator_resolution_quality", lambda *args, **kwargs: {
        "resolution_quality": {"durable": 0, "mostly_stable": 0, "fragile": 1, "likely_to_reopen": 0, "insufficient_resolution": 0},
        "durable_closures": [],
        "fragile_closures": [],
        "likely_reopeners": [],
        "improvement_suggestions": [],
    })

    # Mock the improvement plan functions
    monkeypatch.setattr(dashboard, "build_operator_improvement_plan_records", lambda *args, **kwargs: [
        {
            "plan_id": "plan-device-test",
            "scope_type": "device",
            "scope_id": "test_device",
            "quality_id": "quality-device-test",
            "resolution_quality": "fragile",
            "priority_level": "high",
            "improvement_goal": "reduce_fragility",
            "recommended_actions": ["gather_missing_evidence", "increase_confidence_threshold"],
            "supporting_rationale": "Multiple risk factors detected.",
            "blocking_gaps": ["missing_evidence_data"],
            "expected_stability_gain": 70,
            "followup_mode": "enhanced_monitoring",
            "created_at": "2024-01-01 12:00:00",
        }
    ])
    monkeypatch.setattr(dashboard, "summarize_operator_improvement_plans", lambda *args, **kwargs: {
        "priority_counts": {"critical": 0, "high": 1, "medium": 0, "low": 0, "maintenance": 0},
        "improvement_plans": [
            {
                "scope_type": "device",
                "scope_id": "test_device",
                "improvement_goal": "reduce_fragility",
                "priority_level": "high",
            }
        ],
        "fragile_closures_needing_action": [],
        "top_blocking_gaps": [("missing_evidence_data", 1)],
        "expected_stability_gains": [
            {
                "scope_type": "device",
                "scope_id": "test_device",
                "current_stability": 42,
                "projected_stability": 70,
                "improvement_goal": "reduce_fragility",
            }
        ],
        "suggested_followup_modes": [
            {
                "scope_type": "device",
                "scope_id": "test_device",
                "followup_mode": "enhanced_monitoring",
                "priority": "high",
            }
        ],
    })

    monkeypatch.setattr(dashboard, "build_session_movement", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "enrich_devices_for_session", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "explain_device", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "normalize_device", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "compute_device_score", lambda *args, **kwargs: 0)

    # Render dashboard with minimal data
    html = dashboard.render_dashboard_html(
        devices=[],
        stamp="2024-01-01T12:00:00Z",
    )

    # Assert the panel exists in the HTML
    assert "Resolution Improvement Plans / Corrective Guidance" in html
    assert "render_operator_improvement_plan_panel" not in html  # Function name should not appear
    assert "improvement plans by priority" in html.lower() or "improvement" in html.lower()
    assert "fragile" in html.lower() or "action" in html.lower()
    assert "blocking" in html.lower() or "gap" in html.lower()
    assert "stability" in html.lower() or "gain" in html.lower()
    assert "followup" in html.lower() or "follow-up" in html.lower()
