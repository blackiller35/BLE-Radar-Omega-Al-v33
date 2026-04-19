from ble_radar import dashboard


SAMPLE_DEVICES = [
    {
        "name": "Beacon-One",
        "address": "AA:BB:CC:DD:EE:01",
        "vendor": "TestVendor",
        "profile": "general_ble",
        "rssi": -41,
        "risk_score": 20,
        "follow_score": 5,
        "confidence_score": 55,
        "final_score": 72,
        "alert_level": "critique",
        "seen_count": 4,
        "reason_short": "watch_hit",
        "flags": ["watch"],
        "watch_hit": True,
    },
]


def test_dashboard_contains_operator_escalation_package_panel(monkeypatch):
    monkeypatch.setattr(dashboard, "load_scan_history", lambda: [])
    monkeypatch.setattr(dashboard, "load_last_scan", lambda: [])
    monkeypatch.setattr(dashboard, "load_registry", lambda: {})
    monkeypatch.setattr(dashboard, "load_watch_cases", lambda: {})
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [("TestVendor", 1)])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: devices)
    monkeypatch.setattr(dashboard, "list_cases", lambda: [])
    monkeypatch.setattr(dashboard, "latest_session_diff", lambda: {"has_diff": False})
    monkeypatch.setattr(dashboard, "latest_session_overview", lambda: {})
    monkeypatch.setattr(dashboard, "build_session_catalog", lambda limit=5: [])
    monkeypatch.setattr(dashboard, "build_artifact_index", lambda: {})
    monkeypatch.setattr(dashboard, "build_investigation_profile", lambda *args, **kwargs: {
        "address": "AA:BB:CC:DD:EE:01",
        "identity": {"name": "Beacon-One", "vendor": "TestVendor", "profile": "general_ble", "alert_level": "critique", "watch_hit": True},
        "registry": {"seen_count": 1, "session_count": 1, "registry_score": 80},
        "triage": {"triage_score": 60, "triage_bucket": "critical", "short_reason": "alert:critique"},
        "case": {"status": "investigating", "reason": "-", "updated_at": "-"},
        "movement": {"status": "new"},
        "incident_refs": {"device_packs": [], "incident_packs": []},
        "summary": {"headline": "Beacon-One", "priority": "critical:60"},
    })
    monkeypatch.setattr(dashboard, "build_operator_timeline", lambda *args, **kwargs: {"events": []})
    monkeypatch.setattr(dashboard, "recent_timeline_events", lambda timeline, limit=8: [])
    monkeypatch.setattr(dashboard, "triage_device_list", lambda *args, **kwargs: [
        {
            "address": "AA:BB:CC:DD:EE:01",
            "name": "Beacon-One",
            "triage_score": 60,
            "triage_bucket": "critical",
            "short_reason": "alert:critique",
        }
    ])
    monkeypatch.setattr(dashboard, "recommend_operator_playbook", lambda *args, **kwargs: {
        "playbook_id": "pb-critical-pack",
        "recommended_action": "Escalate and generate incident pack",
        "reason": "Critical triage",
        "priority": "critical",
        "suggested_steps": ["Generate incident pack", "Escalate"],
    })
    monkeypatch.setattr(dashboard, "evaluate_operator_rules", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_rule_results", lambda rows: {
        "auto_applied": [],
        "pending_confirmations": [],
        "recent_matched": [],
    })
    monkeypatch.setattr(dashboard, "load_automation_events", lambda limit=8: [])
    monkeypatch.setattr(dashboard, "build_operator_briefing", lambda **kwargs: {
        "top_priorities": [],
        "open_cases_count": 1,
        "investigating_count": 1,
        "pending_confirmations_count": 0,
        "recent_auto_actions": [],
        "recent_timeline_highlights": [],
        "suggested_next_steps": ["Review handoff"],
    })
    monkeypatch.setattr(dashboard, "build_operator_alerts", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "load_alert_log", lambda limit=12: [])
    monkeypatch.setattr(dashboard, "summarize_alerts", lambda alerts, recent_log_events=None: {
        "active_alerts": [],
        "recent_escalations": [],
        "needs_immediate_review": [],
    })
    monkeypatch.setattr(dashboard, "build_correlation_clusters", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_clusters", lambda rows: {
        "top_correlation_clusters": [],
        "possible_coordinated_devices": [],
        "needs_cluster_review": [],
    })
    monkeypatch.setattr(dashboard, "load_campaign_records", lambda: [])
    monkeypatch.setattr(dashboard, "build_campaign_lifecycle", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_campaigns", lambda rows: {
        "active_campaigns": [],
        "recurring_clusters": [],
        "expanding_groups": [],
        "needs_campaign_review": [],
    })
    monkeypatch.setattr(dashboard, "build_evidence_packs", lambda **kwargs: [])
    monkeypatch.setattr(dashboard, "load_evidence_packs", lambda limit=12: [])
    monkeypatch.setattr(dashboard, "summarize_evidence_packs", lambda packs, persisted_packs=None: {
        "recent_evidence_packs": [],
        "ready_for_review_dossiers": [],
        "campaign_evidence_summary": [],
    })
    monkeypatch.setattr(dashboard, "build_operator_queue", lambda **kwargs: [
        {
            "item_id": "q-device-aabb",
            "scope_type": "device",
            "scope_id": "AA:BB:CC:DD:EE:01",
            "queue_state": "in_review",
            "priority": "high",
            "owner_hint": "Operator",
            "reason_summary": "triage high",
            "recommended_action": "Review now",
            "blocking_factors": [],
            "created_at": "2026-04-18 10:00:00",
            "updated_at": "2026-04-18 10:00:00",
        }
    ])
    monkeypatch.setattr(dashboard, "summarize_operator_queue", lambda rows: {
        "operator_queue": rows,
        "needs_review": rows,
        "blocked_items": [],
        "ready_now": [],
        "recently_resolved": [],
    })
    monkeypatch.setattr(dashboard, "build_queue_health_snapshot", lambda *args, **kwargs: {
        "snapshot_id": "qhealth-20260418",
        "generated_at": "2026-04-18 18:00:00",
        "total_items": 1,
        "ready_count": 0,
        "blocked_count": 0,
        "in_review_count": 1,
        "aging_buckets": {"fresh": 1, "warm": 0, "aging": 0, "stale": 0},
        "stale_items": [],
        "bottleneck_reasons": [],
        "queue_pressure": "low",
        "recommended_followup": "Continue routine cadence",
    })
    monkeypatch.setattr(dashboard, "summarize_queue_health", lambda snapshot, items: {
        "queue_health": snapshot,
        "aging_overview": [{"bucket": "fresh", "count": 1}],
        "blocked_items": [],
        "stale_items": [],
        "operator_pressure": {
            "queue_pressure": "low",
            "recommended_followup": "Continue routine cadence",
            "bottleneck_reasons": [],
        },
    })
    monkeypatch.setattr(dashboard, "build_operator_outcomes", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_operator_outcomes", lambda rows: {
        "operator_outcomes": [],
        "most_effective_actions": [],
        "reopened_items": [],
        "weak_recommendations": [],
    })
    monkeypatch.setattr(dashboard, "build_recommendation_tuning_profiles", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_recommendation_tuning_profiles", lambda rows: {
        "recommendation_confidence": [],
        "most_effective_playbooks": [],
        "weak_recommendations": [],
        "needs_manual_review": [],
    })
    monkeypatch.setattr(dashboard, "build_review_readiness_profiles", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "summarize_review_readiness", lambda rows: {
        "review_readiness": [],
        "ready_for_review": [],
        "needs_more_evidence": [],
        "ready_for_handoff": [],
        "ready_for_archive": [],
    })
    monkeypatch.setattr(dashboard, "build_operator_session_journal", lambda **kwargs: {
        "session_id": "opsession-a",
        "started_at": "2026-04-18 10:00:00",
        "ended_at": "2026-04-18 12:00:00",
        "items_touched": 1,
        "campaigns_updated": 0,
        "alerts_reviewed": 0,
        "outcomes_recorded": 0,
        "readiness_changes": 0,
        "handoff_summary": "ok",
        "next_shift_priorities": ["Review carry-over"],
    })
    monkeypatch.setattr(dashboard, "summarize_operator_session_journal", lambda *args, **kwargs: {
        "current_session_journal": {
            "session_id": "opsession-a",
            "started_at": "2026-04-18 10:00:00",
            "ended_at": "2026-04-18 12:00:00",
        },
        "shift_activity": {
            "items_touched": 1,
            "campaigns_updated": 0,
            "alerts_reviewed": 0,
            "outcomes_recorded": 0,
            "readiness_changes": 0,
        },
        "carry_over_items": [],
        "next_shift_priorities": ["Review carry-over"],
        "recent_handoffs": [],
    })
    monkeypatch.setattr(dashboard, "build_operator_pattern_records", lambda **kwargs: [])
    monkeypatch.setattr(dashboard, "match_scopes_to_patterns", lambda scopes, patterns: [])
    monkeypatch.setattr(dashboard, "summarize_operator_pattern_library", lambda patterns, matches=None: {
        "known_patterns": [],
        "recurring_case_types": [],
        "likely_matches": [],
        "pattern_based_guidance": [],
    })
    monkeypatch.setattr(dashboard, "build_operator_escalation_packages", lambda *args, **kwargs: [
        {
            "escalation_id": "escalation-device-aabb-1",
            "scope_type": "device",
            "scope_id": "AA:BB:CC:DD:EE:01",
            "escalation_reason": "weak_recommendation_confidence",
            "priority": "high",
            "supporting_signals": ["alerts=1"],
            "actions_already_taken": ["manual_followup"],
            "open_risks": ["low_recommendation_confidence"],
            "recommended_next_owner": "specialist_review_team",
            "handoff_payload": {"summary": "ok"},
            "created_at": "2026-04-18 20:00:00",
        }
    ])
    monkeypatch.setattr(dashboard, "summarize_operator_escalation_packages", lambda packages: {
        "escalation_packages": packages,
        "ready_to_escalate": packages,
        "specialist_review_needed": packages,
        "high_risk_open_items": packages,
        "recent_escalations": packages,
    })

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-18 18:00:00")

    assert "Operator Escalation Packages / Transmission" in html
    assert "Escalation packages" in html
    assert "ready to escalate" in html
    assert "specialist review needed" in html
    assert "high-risk open items" in html
    assert "Recent escalations" in html
