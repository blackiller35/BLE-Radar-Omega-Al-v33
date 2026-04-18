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


def test_dashboard_contains_operator_evidence_panel(monkeypatch):
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
        "suggested_next_steps": ["Review evidence pack"],
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
    monkeypatch.setattr(dashboard, "build_evidence_packs", lambda **kwargs: [
        {
            "pack_id": "pack-device-aabb",
            "scope_type": "device",
            "scope_id": "AA:BB:CC:DD:EE:01",
            "generated_at": "2026-04-18_10-30-00",
            "summary": "Device dossier",
            "key_findings": ["triage critical"],
            "risk_level": "high",
            "timeline_highlights": ["triage: spike"],
            "alerts_summary": "critical=1",
            "recommended_followup": "Review",
            "included_artifacts": ["scan_manifest_a"],
        }
    ])
    monkeypatch.setattr(dashboard, "load_evidence_packs", lambda limit=12: [])
    monkeypatch.setattr(dashboard, "summarize_evidence_packs", lambda packs, persisted_packs=None: {
        "recent_evidence_packs": packs,
        "ready_for_review_dossiers": packs,
        "campaign_evidence_summary": packs,
    })

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-18_10-30-00")

    assert "Evidence Pack / Consolidated Operator Dossier" in html
    assert "Recent evidence packs" in html
    assert "Ready for review dossiers" in html
    assert "Campaign evidence summary" in html
