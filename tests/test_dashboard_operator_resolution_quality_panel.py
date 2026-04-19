"""Integration test for operator resolution quality panel in dashboard."""
from ble_radar import dashboard


def test_dashboard_contains_operator_resolution_quality_panel(monkeypatch):
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
            "lineage_id": "lineage-device-test",
            "scope_type": "device",
            "scope_id": "test_device",
            "cycle_count": 1,
            "opened_count": 1,
            "reopened_count": 0,
            "closure_count": 1,
            "escalation_count": 0,
            "last_trigger_type": "none",
            "recurring_pattern_summary": "none",
            "timeline_summary": "opened=1 | escalations=0 | closures=1 | reopens=0",
            "current_lifecycle_state": "closed",
            "updated_at": "2026-04-19 10:00:00",
        }
    ])
    monkeypatch.setattr(dashboard, "summarize_operator_lifecycle_lineage", lambda *args, **kwargs: {
        "lifecycle_lineage": [],
        "repeated_reopeners": [],
        "recurring_triggers": [],
        "multi_cycle_cases": [],
        "stabilized_after_reopen": [],
    })

    # Mock the new resolution quality functions
    monkeypatch.setattr(dashboard, "build_operator_resolution_quality_records", lambda *args, **kwargs: [
        {
            "quality_id": "quality-device-test",
            "scope_type": "device",
            "scope_id": "test_device",
            "lineage_id": "lineage-device-test",
            "closure_id": "closure-test",
            "resolution_quality": "durable",
            "stability_score": 85,
            "reopen_risk": 5,
            "supporting_factors": ["closed", "no_reopens"],
            "weak_factors": [],
            "recommended_improvement": "maintain_current_process",
            "evaluated_at": "2024-01-01 12:00:00",
        }
    ])
    monkeypatch.setattr(dashboard, "summarize_operator_resolution_quality", lambda *args, **kwargs: {
        "resolution_quality": {
            "durable": 1,
            "mostly_stable": 0,
            "fragile": 0,
            "likely_to_reopen": 0,
            "insufficient_resolution": 0,
        },
        "durable_closures": [
            {
                "scope_type": "device",
                "scope_id": "test_device",
                "resolution_quality": "durable",
                "stability_score": 85,
                "reopen_risk": 5,
            }
        ],
        "fragile_closures": [],
        "likely_reopeners": [],
        "improvement_suggestions": [],
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
    assert "Resolution Quality / Stability Assessment" in html
    assert "render_operator_resolution_quality_panel" not in html  # Function name should not appear
    assert "resolution quality" in html.lower()
    assert "durable closures" in html.lower() or "durable" in html.lower()
    assert "fragile" in html.lower() or "at-risk" in html.lower()
    assert "reopeners" in html.lower() or "reopen" in html.lower()
    assert "improvement" in html.lower()
