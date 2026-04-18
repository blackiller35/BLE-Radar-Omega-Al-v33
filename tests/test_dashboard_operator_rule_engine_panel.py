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


def test_dashboard_contains_operator_rule_engine_panel(monkeypatch):
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
        "case": {"status": "new", "reason": "-", "updated_at": "-"},
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
    monkeypatch.setattr(dashboard, "evaluate_operator_rules", lambda *args, **kwargs: [
        {
            "rule_id": "re-critical-confirm",
            "matched": True,
            "recommended_action": "Escalate",
            "auto_applied": False,
            "requires_confirmation": True,
            "reason": "critical",
        },
        {
            "rule_id": "re-watch-auto-monitor",
            "matched": True,
            "recommended_action": "Enable passive watch monitoring",
            "auto_applied": True,
            "requires_confirmation": False,
            "reason": "watch",
        },
    ])
    monkeypatch.setattr(dashboard, "summarize_rule_results", lambda rows: {
        "auto_applied": [rows[1]],
        "pending_confirmations": [rows[0]],
        "recent_matched": rows,
    })
    monkeypatch.setattr(dashboard, "load_automation_events", lambda limit=8: [
        {
            "timestamp": "2026-04-18 12:00:00",
            "address": "AA:BB:CC:DD:EE:01",
            "rule_id": "re-watch-auto-monitor",
            "auto_applied": True,
        }
    ])

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-18_10-30-00")

    assert "Operator Rule Engine (Safe Auto-Actions)" in html
    assert "Auto-applied actions" in html
    assert "Pending confirmations" in html
    assert "recently match" in html.lower() or "recently matched" in html.lower()
