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

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-20_12-00-00")

    assert "Security status" in html
    assert "Mode: <strong>operator</strong>" in html
    assert "YubiKey present: <strong>true</strong>" in html
    assert "Key source: <strong>primary</strong>" in html
    assert "Sensitive features: <strong>true</strong>" in html
    assert "Secrets unlocked: <strong>true</strong>" in html
    assert "Operator session: <strong>unlocked</strong>" in html
    assert "Elevated sensitive access: <strong>enabled</strong>" in html
    assert "Operator-only actions:" in html
    assert "Operator enabled" in html


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
