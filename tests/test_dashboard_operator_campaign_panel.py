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


def test_dashboard_contains_operator_campaign_panel(monkeypatch):
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
        "suggested_next_steps": ["Review campaign continuity"],
    })
    monkeypatch.setattr(dashboard, "build_operator_alerts", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "load_alert_log", lambda limit=12: [])
    monkeypatch.setattr(dashboard, "summarize_alerts", lambda alerts, recent_log_events=None: {
        "active_alerts": [],
        "recent_escalations": [],
        "needs_immediate_review": [],
    })
    monkeypatch.setattr(dashboard, "build_correlation_clusters", lambda *args, **kwargs: [
        {
            "cluster_id": "cluster-aabb-2",
            "member_addresses": ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"],
            "member_count": 2,
            "reason_summary": "triage bucket proximity",
            "risk_level": "high",
            "top_signals": ["triage bucket proximity", "playbook similarity"],
            "recommended_followup": "Review as possible coordinated campaign",
        }
    ])
    monkeypatch.setattr(dashboard, "summarize_clusters", lambda rows: {
        "top_correlation_clusters": rows,
        "possible_coordinated_devices": rows,
        "needs_cluster_review": rows,
    })
    monkeypatch.setattr(dashboard, "load_campaign_records", lambda: [])
    monkeypatch.setattr(dashboard, "build_campaign_lifecycle", lambda *args, **kwargs: [
        {
            "campaign_id": "campaign-aabb",
            "member_addresses": ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"],
            "member_count": 2,
            "status": "new",
            "first_seen": "2026-04-18_10-00-00",
            "last_seen": "2026-04-18_10-00-00",
            "activity_trend": "up",
            "risk_level": "high",
            "reason_summary": "triage bucket proximity",
            "recommended_followup": "Review campaign continuity",
        }
    ])
    monkeypatch.setattr(dashboard, "summarize_campaigns", lambda rows: {
        "active_campaigns": rows,
        "recurring_clusters": rows,
        "expanding_groups": rows,
        "needs_campaign_review": rows,
    })

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-18_10-30-00")

    assert "Campaign Tracking / Cluster Lifecycle" in html
    assert "Active campaigns" in html
    assert "Recurring clusters" in html
    assert "Expanding groups" in html
    assert "Needs campaign review" in html
