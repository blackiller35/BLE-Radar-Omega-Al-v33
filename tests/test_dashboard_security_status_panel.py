from ble_radar import dashboard
from ble_radar.security import SecurityContext


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


SAMPLE_SECURITY_AUDIT_EVENTS = [
    {
        "ts": "2026-04-20 12:00:04",
        "kind": "security.operator_session.unlocked",
        "message": "Operator session unlocked",
        "data": {"reason": "manual_unlock"},
    },
    {
        "ts": "2026-04-20 12:00:03",
        "kind": "security.operator_session.locked",
        "message": "Operator session locked",
        "data": {},
    },
    {
        "ts": "2026-04-20 12:00:02",
        "kind": "security.sensitive_action.denied",
        "message": "Sensitive action denied",
        "data": {},
    },
    {
        "ts": "2026-04-20 12:00:01",
        "kind": "security.sensitive_action.allowed",
        "message": "Sensitive action allowed",
        "data": {},
    },
    {
        "ts": "2026-04-20 12:00:00",
        "kind": "security.operator_session.auto_locked",
        "message": "Operator session auto-locked by timeout",
        "data": {"reason": "timeout"},
    },
]


def test_render_security_status_panel_with_context():
    context = SecurityContext(
        mode="operator",
        yubikey_present=True,
        key_name="primary",
        key_label="YubiKey-1",
        sensitive_enabled=True,
        secrets_unlocked=True,
    )

    html = dashboard.render_security_status_panel(context)

    assert "Mode: <strong>operator</strong>" in html
    assert "YubiKey present: <strong>true</strong>" in html
    assert "Key source: <strong>primary</strong>" in html
    assert "Sensitive features: <strong>true</strong>" in html
    assert "Secrets unlocked: <strong>true</strong>" in html
    assert "Operator session: <strong>unlocked</strong>" in html
    assert "Session controls (unlocked):" in html
    assert "Unlock operator session" in html
    assert "Lock operator session" in html
    assert 'data-runtime-command="session unlock"' in html
    assert 'data-runtime-command="session lock"' in html
    assert " disabled>Unlock operator session</button>" in html
    assert " disabled>Lock operator session</button>" not in html
    assert "Elevated sensitive access: <strong>enabled</strong>" in html
    assert "Operator-only actions:" in html
    assert "export context" in html
    assert "incident pack creation" in html
    assert "case writes" in html
    assert "registry writes" in html
    assert "Operator enabled" in html


def test_render_security_status_panel_demo_mode_locked_actions():
    context = SecurityContext(
        mode="demo",
        yubikey_present=False,
        key_name=None,
        key_label=None,
        sensitive_enabled=False,
        secrets_unlocked=False,
    )

    html = dashboard.render_security_status_panel(context)

    assert "Mode: <strong>demo</strong>" in html
    assert "Operator session: <strong>locked</strong>" in html
    assert "Session controls (locked):" in html
    assert " disabled>Unlock operator session</button>" in html
    assert " disabled>Lock operator session</button>" in html
    assert (
        "YubiKey/operator mode is required before session controls can be used." in html
    )
    assert "Operator-only actions:" in html
    assert "export context" in html
    assert "incident pack creation" in html
    assert "case writes" in html
    assert "registry writes" in html
    assert "Operator unlock required" in html
    assert "text-decoration:line-through;" in html


def test_render_security_status_panel_operator_mode_session_locked():
    context = SecurityContext(
        mode="operator",
        yubikey_present=True,
        key_name="primary",
        key_label="YubiKey-1",
        sensitive_enabled=False,
        secrets_unlocked=False,
    )

    html = dashboard.render_security_status_panel(context)

    assert "Mode: <strong>operator</strong>" in html
    assert "Operator session: <strong>locked</strong>" in html
    assert "Session controls (locked):" in html
    assert " disabled>Lock operator session</button>" in html
    assert " disabled>Unlock operator session</button>" not in html
    assert "Sensitive secrets remain locked until operator session unlock." in html
    assert "Operator unlock required" in html
    assert "text-decoration:line-through;" in html


def test_render_security_status_panel_fallback():
    html = dashboard.render_security_status_panel(None)
    assert "Security context unavailable." in html


def test_render_security_quick_actions_panel_demo_mode_disabled():
    context = SecurityContext(
        mode="demo",
        yubikey_present=False,
        key_name=None,
        key_label=None,
        sensitive_enabled=False,
        secrets_unlocked=False,
    )

    html = dashboard.render_security_quick_actions_panel(context)

    assert "Quick actions state: <strong>demo-disabled</strong>" in html
    assert " disabled" in html
    assert "YubiKey/operator mode is required before quick actions can run." in html


def test_render_security_quick_actions_panel_operator_locked():
    context = SecurityContext(
        mode="operator",
        yubikey_present=True,
        key_name="primary",
        key_label="YubiKey-1",
        sensitive_enabled=False,
        secrets_unlocked=False,
    )

    html = dashboard.render_security_quick_actions_panel(context)

    assert "Quick actions state: <strong>operator-locked</strong>" in html
    assert 'data-security-quick-action="unlock"' in html
    assert 'data-security-quick-action="lock"' in html
    assert 'disabled data-security-quick-action="lock"' in html
    assert 'disabled data-security-quick-action="unlock"' not in html


def test_render_security_quick_actions_panel_operator_unlocked():
    context = SecurityContext(
        mode="operator",
        yubikey_present=True,
        key_name="primary",
        key_label="YubiKey-1",
        sensitive_enabled=True,
        secrets_unlocked=True,
    )

    html = dashboard.render_security_quick_actions_panel(context)

    assert "Quick actions state: <strong>operator-unlocked</strong>" in html
    assert 'disabled data-security-quick-action="unlock"' in html
    assert 'disabled data-security-quick-action="lock"' not in html


def test_render_security_audit_events_panel_all_filter_shows_mixed_events():
    html = dashboard.render_security_audit_events_panel(SAMPLE_SECURITY_AUDIT_EVENTS)

    assert 'data-security-audit-filter="all"' in html
    assert 'data-security-audit-active-label="all"' in html
    assert 'data-security-audit-active="true"' in html
    assert "security.operator_session.unlocked" in html
    assert "security.sensitive_action.denied" in html
    assert "security.sensitive_action.allowed" in html
    assert "security.operator_session.auto_locked" in html


def test_render_security_audit_events_panel_filter_chips_render_correctly():
    html = dashboard.render_security_audit_events_panel(SAMPLE_SECURITY_AUDIT_EVENTS)

    assert 'data-security-audit-filter="all"' in html
    assert 'data-security-audit-filter="session"' in html
    assert 'data-security-audit-filter="denied"' in html
    assert 'data-security-audit-filter="allowed"' in html
    assert 'data-security-audit-filter="timeout"' in html
    assert "Security audit filter:" in html


def test_render_security_audit_events_panel_session_filter_only_session_events():
    html = dashboard.render_security_audit_events_panel(
        SAMPLE_SECURITY_AUDIT_EVENTS, active_filter="session"
    )

    assert 'data-security-audit-active-label="session"' in html
    assert "security.operator_session.unlocked" in html
    assert "security.operator_session.locked" in html
    assert "security.sensitive_action.denied" not in html
    assert "security.operator_session.auto_locked" not in html


def test_render_security_audit_events_panel_denied_filter_only_denied_events():
    html = dashboard.render_security_audit_events_panel(
        SAMPLE_SECURITY_AUDIT_EVENTS, active_filter="denied"
    )

    assert 'data-security-audit-active-label="denied"' in html
    assert "security.sensitive_action.denied" in html
    assert "security.operator_session.unlocked" not in html
    assert "security.sensitive_action.allowed" not in html


def test_render_security_audit_events_panel_timeout_filter_only_timeout_events():
    html = dashboard.render_security_audit_events_panel(
        SAMPLE_SECURITY_AUDIT_EVENTS, active_filter="timeout"
    )

    assert 'data-security-audit-active-label="timeout"' in html
    assert "security.operator_session.auto_locked" in html
    assert "timeout" in html
    assert "security.operator_session.unlocked" not in html
    assert "security.sensitive_action.denied" not in html


def test_render_security_audit_events_panel_empty_filtered_result_fallback():
    html = dashboard.render_security_audit_events_panel(
        SAMPLE_SECURITY_AUDIT_EVENTS, active_filter="allowed"
    )
    assert "security.sensitive_action.allowed" in html

    empty_html = dashboard.render_security_audit_events_panel(
        SAMPLE_SECURITY_AUDIT_EVENTS[:2], active_filter="denied"
    )
    assert "No recent security audit events." in empty_html


def test_render_security_audit_dedicated_view_renders():
    html = dashboard.render_security_audit_dedicated_view(SAMPLE_SECURITY_AUDIT_EVENTS)

    assert "Security audit view filter:" in html
    assert 'data-security-audit-view-filter="all"' in html
    assert 'data-security-audit-view-active-label="all"' in html


def test_render_security_audit_dedicated_view_shows_recent_events():
    html = dashboard.render_security_audit_dedicated_view(SAMPLE_SECURITY_AUDIT_EVENTS)

    assert "security.operator_session.unlocked" in html
    assert "2026-04-20 12:00:04" in html
    assert "security.operator_session.auto_locked" in html


def test_render_security_audit_dedicated_view_empty_fallback():
    html = dashboard.render_security_audit_dedicated_view([], active_filter="all")
    assert "No recent security audit events." in html


def test_render_security_audit_dedicated_view_filters_apply_correctly():
    session_html = dashboard.render_security_audit_dedicated_view(
        SAMPLE_SECURITY_AUDIT_EVENTS, active_filter="session"
    )
    assert "security.operator_session.unlocked" in session_html
    assert "security.operator_session.locked" in session_html
    assert "security.sensitive_action.denied" not in session_html

    timeout_html = dashboard.render_security_audit_dedicated_view(
        SAMPLE_SECURITY_AUDIT_EVENTS, active_filter="timeout"
    )
    assert "security.operator_session.auto_locked" in timeout_html
    assert "security.operator_session.unlocked" not in timeout_html


def test_dashboard_html_contains_security_status_panel(monkeypatch):
    monkeypatch.setattr(dashboard, "load_scan_history", lambda: [])
    monkeypatch.setattr(dashboard, "load_registry", lambda: {})
    monkeypatch.setattr(
        dashboard, "get_vendor_summary", lambda devices: [("TestVendor", 1)]
    )
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: devices)
    monkeypatch.setattr(
        dashboard,
        "build_security_context",
        lambda: SecurityContext(
            mode="operator",
            yubikey_present=True,
            key_name="primary",
            key_label="YubiKey-1",
            sensitive_enabled=True,
            secrets_unlocked=True,
        ),
    )
    monkeypatch.setattr(
        dashboard, "read_events", lambda limit=25: SAMPLE_SECURITY_AUDIT_EVENTS
    )

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-20_12-00-00")

    assert "Security status" in html
    assert "Security audit events" in html
    assert "Security audit view (dedicated)" in html
    assert "Mode: <strong>operator</strong>" in html
    assert "YubiKey present: <strong>true</strong>" in html
    assert "Key source: <strong>primary</strong>" in html
    assert "Sensitive features: <strong>true</strong>" in html
    assert "Secrets unlocked: <strong>true</strong>" in html
    assert "Operator session: <strong>unlocked</strong>" in html
    assert "Elevated sensitive access: <strong>enabled</strong>" in html
    assert "Operator-only actions:" in html
    assert "Operator enabled" in html
    assert 'data-security-audit-filter="all"' in html
    assert 'data-security-audit-view-filter="all"' in html
    assert "security.operator_session.unlocked" in html


def test_dashboard_html_security_status_fallback(monkeypatch):
    monkeypatch.setattr(dashboard, "load_scan_history", lambda: [])
    monkeypatch.setattr(dashboard, "load_registry", lambda: {})
    monkeypatch.setattr(
        dashboard, "get_vendor_summary", lambda devices: [("TestVendor", 1)]
    )
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: devices)

    def _raise_security_context():
        raise RuntimeError("security context unavailable")

    monkeypatch.setattr(dashboard, "build_security_context", _raise_security_context)

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-20_12-00-00")

    assert "Security status" in html
    assert "Security context unavailable." in html
