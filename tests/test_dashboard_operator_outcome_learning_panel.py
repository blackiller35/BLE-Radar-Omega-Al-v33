"""Focused dashboard panel test for operator outcome learning."""

from ble_radar import dashboard


def test_render_operator_outcome_learning_panel_sections_present():
    summary = {
        "outcome_learning": [
            {
                "scope_type": "device",
                "scope_id": "d1",
                "action_pattern": "collect_additional_supporting_evidence",
                "confidence_level": "high",
                "reopen_delta": -1,
                "stability_delta": 18,
                "observed_outcome": "stabilized_after_action",
                "caution_flags": [],
                "recommended_reuse": "reuse_with_similar_scope",
            }
        ],
        "high_value_action_patterns": [
            {
                "scope_type": "device",
                "scope_id": "d1",
                "action_pattern": "collect_additional_supporting_evidence",
                "confidence_level": "high",
            }
        ],
        "reopen_reduction_signals": [
            {
                "scope_type": "device",
                "scope_id": "d1",
                "reopen_delta": -1,
                "stability_delta": 18,
            }
        ],
        "mixed_result_patterns": [
            {
                "scope_type": "case",
                "scope_id": "c1",
                "observed_outcome": "mixed_with_reopen",
                "caution_flags": ["fragile_resolution_quality"],
            }
        ],
        "recommended_reuse": [
            {
                "scope_type": "device",
                "scope_id": "d1",
                "action_pattern": "collect_additional_supporting_evidence",
                "recommended_reuse": "reuse_with_similar_scope",
            }
        ],
    }

    html = dashboard.render_operator_outcome_learning_panel(summary)

    assert "Outcome learning records" in html
    assert "High value action patterns" in html
    assert "Reopen reduction signals" in html
    assert "Mixed result patterns" in html
    assert "Recommended reuse" in html


def test_render_operator_learning_snapshot_section_with_data():
    summary = {
        "outcome_learning": [
            {
                "scope_type": "device",
                "scope_id": "d1",
                "action_pattern": "collect_additional_supporting_evidence",
                "confidence_level": "high",
                "recommended_reuse": "reuse_with_similar_scope",
            }
        ],
        "high_value_action_patterns": [{"scope_type": "device", "scope_id": "d1"}],
        "reopen_reduction_signals": [{"scope_type": "device", "scope_id": "d1"}],
        "mixed_result_patterns": [],
        "recommended_reuse": [
            {
                "scope_type": "device",
                "scope_id": "d1",
                "action_pattern": "collect_additional_supporting_evidence",
            }
        ],
    }

    html = dashboard.render_operator_learning_snapshot_section(summary)

    assert "Learned patterns" in html
    assert "Operator guidance" in html
    assert "keep" in html
    assert "priority=<strong>low</strong>" in html
    assert "Recommended action: <strong>continue current reuse pattern</strong>" in html
    assert (
        "Operator note: <strong>safe to continue under current pattern</strong>" in html
    )
    assert "Recommended action" in html
    assert "Recommended action: <strong>continue current reuse pattern</strong>" in html
    assert (
        "Operator note: <strong>safe to continue under current pattern</strong>" in html
    )
    assert "Review trigger: <strong>no immediate review needed</strong>" in html
    assert "Follow-up tempo: <strong>routine</strong>" in html
    assert "Attention band: <strong>low-touch</strong>" in html
    assert "Response posture: <strong>steady</strong>" in html
    assert "Reuse gate: <strong>open</strong>" in html
    assert "Approval mode: <strong>default</strong>" in html
    assert "Intervention level: <strong>minimal</strong>" in html
    assert "Oversight level: <strong>light</strong>" in html
    assert "Verification mode: <strong>spot-check</strong>" in html
    assert "Escalation path: <strong>none</strong>" in html
    assert "Operator checkpoint: <strong>optional</strong>" in html
    assert "Trace mode: <strong>light trace</strong>" in html
    assert "Audit readiness: <strong>background</strong>" in html
    assert "Review burden: <strong>low</strong>" in html
    assert "Documentation mode: <strong>compact</strong>" in html
    assert "Handoff readiness: <strong>standby</strong>" in html
    assert "Latest pattern" in html
    assert "Recommended reuse" in html


def test_render_operator_learning_snapshot_section_fallback():
    html = dashboard.render_operator_learning_snapshot_section({})
    assert "No learning snapshot available" in html


def test_render_operator_learning_snapshot_section_insufficient_data_fallback():
    summary = {
        "outcome_learning": [
            {
                "scope_type": "device",
                "scope_id": "d1",
                "action_pattern": "collect_additional_supporting_evidence",
                "confidence_level": "medium",
                "recommended_reuse": "reuse_with_operator_review",
            }
        ],
        "high_value_action_patterns": [],
        "reopen_reduction_signals": [],
        "mixed_result_patterns": [],
        "recommended_reuse": [],
    }

    html = dashboard.render_operator_learning_snapshot_section(summary)
    assert "Insufficient learning data for operator guidance" in html


def test_render_operator_learning_snapshot_section_investigate_guidance():
    summary = {
        "outcome_learning": [
            {
                "scope_type": "device",
                "scope_id": "d1",
                "action_pattern": "collect_additional_supporting_evidence",
                "confidence_level": "low",
                "recommended_reuse": "do_not_reuse_without_more_history",
                "caution_flags": ["reopen_pressure_increasing"],
            },
            {
                "scope_type": "case",
                "scope_id": "c1",
                "action_pattern": "review_closure_decision_logic",
                "confidence_level": "medium",
                "recommended_reuse": "reuse_with_operator_review",
                "caution_flags": ["fragile_resolution_quality"],
            },
        ],
        "high_value_action_patterns": [],
        "reopen_reduction_signals": [],
        "mixed_result_patterns": [{"scope_type": "device", "scope_id": "d1"}],
        "recommended_reuse": [],
    }

    html = dashboard.render_operator_learning_snapshot_section(summary)
    assert "Operator guidance" in html
    assert "investigate" in html
    assert "priority=<strong>high</strong>" in html
    assert (
        "Recommended action: <strong>review recent mixed patterns before reuse</strong>"
        in html
    )
    assert "Operator note: <strong>review recent caution signals first</strong>" in html
    assert "Recommended action" in html
    assert (
        "Recommended action: <strong>review recent mixed patterns before reuse</strong>"
        in html
    )
    assert "Operator note: <strong>review recent caution signals first</strong>" in html
    assert "Review trigger: <strong>review before next reuse</strong>" in html
    assert "Follow-up tempo: <strong>before reuse</strong>" in html
    assert "Attention band: <strong>hands-on</strong>" in html
    assert "Response posture: <strong>active review</strong>" in html
    assert "Reuse gate: <strong>blocked pending review</strong>" in html
    assert "Approval mode: <strong>hold</strong>" in html
    assert "Intervention level: <strong>direct</strong>" in html
    assert "Oversight level: <strong>strict</strong>" in html
    assert "Verification mode: <strong>full review</strong>" in html
    assert "Escalation path: <strong>prepare now</strong>" in html
    assert "Operator checkpoint: <strong>required</strong>" in html
    assert "Trace mode: <strong>full trace</strong>" in html
    assert "Audit readiness: <strong>immediate</strong>" in html
    assert "Review burden: <strong>high</strong>" in html
    assert "Documentation mode: <strong>expanded</strong>" in html
    assert "Handoff readiness: <strong>immediate handoff</strong>" in html


def test_dashboard_contains_learning_snapshot_section(monkeypatch):
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
    monkeypatch.setattr(
        dashboard, "build_investigation_profile", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(
        dashboard, "build_operator_timeline", lambda *args, **kwargs: {"events": []}
    )
    monkeypatch.setattr(dashboard, "recent_timeline_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "triage_device_list", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        dashboard, "recommend_operator_playbook", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(
        dashboard, "evaluate_operator_rules", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(dashboard, "summarize_rule_results", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "load_automation_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        dashboard, "build_operator_briefing", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(dashboard, "build_operator_alerts", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "load_alert_log", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_alerts", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        dashboard, "build_correlation_clusters", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(dashboard, "summarize_clusters", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "load_campaign_records", lambda: [])
    monkeypatch.setattr(
        dashboard, "build_campaign_lifecycle", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(dashboard, "summarize_campaigns", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "build_evidence_packs", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "load_evidence_packs", lambda: [])
    monkeypatch.setattr(
        dashboard, "summarize_evidence_packs", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(
        dashboard, "build_operator_escalation_packages", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        dashboard, "summarize_operator_escalation_packages", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(
        dashboard,
        "build_operator_escalation_feedback_records",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        dashboard, "summarize_operator_escalation_feedback", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(
        dashboard, "build_operator_closure_packages", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        dashboard, "summarize_operator_closure_packages", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(
        dashboard,
        "build_operator_post_closure_monitoring_policies",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        dashboard,
        "summarize_operator_post_closure_monitoring_policies",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(
        dashboard, "build_operator_reopen_records", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        dashboard, "summarize_operator_reopen_records", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(
        dashboard, "build_operator_outcomes", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        dashboard, "summarize_operator_outcomes", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(dashboard, "build_operator_queue", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        dashboard, "summarize_operator_queue", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(
        dashboard, "build_queue_health_snapshot", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(dashboard, "summarize_queue_health", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        dashboard, "build_operator_session_journal", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(
        dashboard, "summarize_operator_session_journal", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(
        dashboard, "build_recommendation_tuning_profiles", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        dashboard,
        "summarize_recommendation_tuning_profiles",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(
        dashboard, "build_review_readiness_profiles", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        dashboard, "summarize_review_readiness", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(
        dashboard, "build_operator_pattern_records", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        dashboard, "match_scopes_to_patterns", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        dashboard, "summarize_operator_pattern_library", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(
        dashboard,
        "build_operator_lifecycle_lineage_records",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        dashboard, "summarize_operator_lifecycle_lineage", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(
        dashboard,
        "build_operator_resolution_quality_records",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        dashboard,
        "summarize_operator_resolution_quality",
        lambda *args, **kwargs: {
            "resolution_quality": {
                "durable": 0,
                "mostly_stable": 0,
                "fragile": 0,
                "likely_to_reopen": 0,
                "insufficient_resolution": 0,
            },
            "durable_closures": [],
            "fragile_closures": [],
            "likely_reopeners": [],
            "improvement_suggestions": [],
        },
    )
    monkeypatch.setattr(
        dashboard, "build_operator_improvement_plan_records", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        dashboard,
        "summarize_operator_improvement_plans",
        lambda *args, **kwargs: {
            "priority_counts": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "maintenance": 0,
            },
            "improvement_plans": [],
            "fragile_closures_needing_action": [],
            "top_blocking_gaps": [],
            "expected_stability_gains": [],
            "suggested_followup_modes": [],
        },
    )
    monkeypatch.setattr(
        dashboard, "build_operator_outcome_learning_records", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        dashboard,
        "summarize_operator_outcome_learning",
        lambda *args, **kwargs: {
            "outcome_learning": [
                {
                    "scope_type": "device",
                    "scope_id": "d1",
                    "action_pattern": "collect_additional_supporting_evidence",
                    "confidence_level": "high",
                    "recommended_reuse": "reuse_with_similar_scope",
                    "caution_flags": [],
                },
                {
                    "scope_type": "case",
                    "scope_id": "c1",
                    "action_pattern": "review_closure_decision_logic",
                    "confidence_level": "medium",
                    "recommended_reuse": "reuse_with_operator_review",
                    "caution_flags": [],
                },
            ],
            "high_value_action_patterns": [{"scope_type": "device", "scope_id": "d1"}],
            "reopen_reduction_signals": [{"scope_type": "device", "scope_id": "d1"}],
            "mixed_result_patterns": [],
            "recommended_reuse": [
                {
                    "scope_type": "device",
                    "scope_id": "d1",
                    "action_pattern": "collect_additional_supporting_evidence",
                    "recommended_reuse": "reuse_with_similar_scope",
                }
            ],
        },
    )

    monkeypatch.setattr(dashboard, "build_session_movement", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        dashboard, "enrich_devices_for_session", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(dashboard, "explain_device", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "normalize_device", lambda *args, **kwargs: {})
    monkeypatch.setattr(dashboard, "compute_device_score", lambda *args, **kwargs: 0)

    html = dashboard.render_dashboard_html(devices=[], stamp="2024-01-01T12:00:00Z")

    assert "Learning snapshot" in html
    assert "Operator guidance" in html
    assert "keep" in html
    assert "Recommended action" in html
    assert "Recommended action: <strong>continue current reuse pattern</strong>" in html
    assert (
        "Operator note: <strong>safe to continue under current pattern</strong>" in html
    )
    assert "Review trigger: <strong>no immediate review needed</strong>" in html


def test_render_operator_learning_snapshot_section_watch_guidance():
    summary = {
        "outcome_learning": [
            {
                "scope_type": "device",
                "scope_id": "d1",
                "action_pattern": "collect_additional_supporting_evidence",
                "confidence_level": "medium",
                "recommended_reuse": "reuse_with_operator_review",
                "caution_flags": [],
            },
            {
                "scope_type": "case",
                "scope_id": "c1",
                "action_pattern": "review_closure_decision_logic",
                "confidence_level": "medium",
                "recommended_reuse": "reuse_with_operator_review",
                "caution_flags": [],
            },
        ],
        "high_value_action_patterns": [],
        "reopen_reduction_signals": [],
        "mixed_result_patterns": [],
        "recommended_reuse": [],
    }

    html = dashboard.render_operator_learning_snapshot_section(summary)

    assert "Operator guidance" in html
    assert "watch" in html
    assert "priority=<strong>medium</strong>" in html
    assert (
        "Recommended action: <strong>monitor next sessions before broad reuse</strong>"
        in html
    )
    assert (
        "Operator note: <strong>wait for one more stable learning cycle</strong>"
        in html
    )
    assert "Recommended action" in html
    assert (
        "Recommended action: <strong>monitor next sessions before broad reuse</strong>"
        in html
    )
    assert (
        "Operator note: <strong>wait for one more stable learning cycle</strong>"
        in html
    )
    assert "Review trigger: <strong>recheck after next stable cycle</strong>" in html
    assert "Follow-up tempo: <strong>next cycle</strong>" in html
    assert "Attention band: <strong>monitor</strong>" in html
    assert "Response posture: <strong>cautious</strong>" in html
    assert "Reuse gate: <strong>guarded</strong>" in html
    assert "Approval mode: <strong>confirm</strong>" in html
    assert "Intervention level: <strong>selective</strong>" in html
    assert "Oversight level: <strong>active</strong>" in html
    assert "Verification mode: <strong>confirm</strong>" in html
    assert "Escalation path: <strong>ready if needed</strong>" in html
    assert "Operator checkpoint: <strong>advised</strong>" in html
    assert "Trace mode: <strong>tracked</strong>" in html
    assert "Audit readiness: <strong>prepared</strong>" in html
    assert "Review burden: <strong>moderate</strong>" in html
    assert "Documentation mode: <strong>standard</strong>" in html
    assert "Handoff readiness: <strong>ready</strong>" in html
    assert "mixed signals require monitored reuse" in html
