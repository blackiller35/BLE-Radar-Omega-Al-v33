"""Focused tests: Security quick actions wire to real runtime behavior."""

import time
from pathlib import Path

import pytest

from ble_radar.security import mode as security_mode
from ble_radar.security.mode import (
    OPERATOR_SESSION_UNLOCK_FILE,
    OPERATOR_SESSION_TIMEOUT_SECONDS,
    clear_expired_operator_session,
    is_operator_session_unlocked,
    lock_operator_session,
    unlock_operator_session,
)
from ble_radar import dashboard
from ble_radar.security import SecurityContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_unlock_file(tmp_path, monkeypatch):
    """Redirect the unlock file into a temp directory for test isolation."""
    unlock_file = tmp_path / "operator_session.unlock"
    monkeypatch.setattr(security_mode, "OPERATOR_SESSION_UNLOCK_FILE", unlock_file)
    return unlock_file


# ---------------------------------------------------------------------------
# 1. Unlock action changes runtime session state
# ---------------------------------------------------------------------------


def test_unlock_action_creates_unlock_file(tmp_path, monkeypatch):
    unlock_file = _patch_unlock_file(tmp_path, monkeypatch)
    assert not unlock_file.exists()

    unlock_operator_session()

    assert unlock_file.exists()
    assert unlock_file.read_text().strip() == "unlocked"


def test_unlock_action_makes_session_unlocked(tmp_path, monkeypatch):
    unlock_file = _patch_unlock_file(tmp_path, monkeypatch)
    monkeypatch.setattr(security_mode, "log_event", lambda *a, **kw: None)

    unlock_operator_session()

    assert is_operator_session_unlocked()


# ---------------------------------------------------------------------------
# 2. Lock action changes runtime session state
# ---------------------------------------------------------------------------


def test_lock_action_removes_unlock_file(tmp_path, monkeypatch):
    unlock_file = _patch_unlock_file(tmp_path, monkeypatch)
    monkeypatch.setattr(security_mode, "log_event", lambda *a, **kw: None)
    unlock_operator_session()
    assert unlock_file.exists()

    lock_operator_session()

    assert not unlock_file.exists()


def test_lock_action_makes_session_locked(tmp_path, monkeypatch):
    unlock_file = _patch_unlock_file(tmp_path, monkeypatch)
    monkeypatch.setattr(security_mode, "log_event", lambda *a, **kw: None)
    unlock_operator_session()
    assert is_operator_session_unlocked()

    lock_operator_session()

    assert not is_operator_session_unlocked()


# ---------------------------------------------------------------------------
# 3. Clear expired session removes only an expired unlocked state
# ---------------------------------------------------------------------------


def test_clear_expired_session_removes_expired_file(tmp_path, monkeypatch):
    unlock_file = _patch_unlock_file(tmp_path, monkeypatch)
    monkeypatch.setattr(security_mode, "log_event", lambda *a, **kw: None)
    # Write unlock file with a backdated mtime to simulate expiry
    unlock_file.parent.mkdir(parents=True, exist_ok=True)
    unlock_file.write_text("unlocked")
    expired_mtime = time.time() - OPERATOR_SESSION_TIMEOUT_SECONDS - 10
    import os

    os.utime(unlock_file, (expired_mtime, expired_mtime))

    cleared = clear_expired_operator_session()

    assert cleared is True
    assert not unlock_file.exists()


def test_clear_expired_session_does_not_remove_active_session(tmp_path, monkeypatch):
    unlock_file = _patch_unlock_file(tmp_path, monkeypatch)
    monkeypatch.setattr(security_mode, "log_event", lambda *a, **kw: None)
    unlock_operator_session()  # fresh file → not expired

    cleared = clear_expired_operator_session()

    assert cleared is False
    assert unlock_file.exists()


def test_clear_expired_session_no_file_returns_false(tmp_path, monkeypatch):
    _patch_unlock_file(tmp_path, monkeypatch)

    cleared = clear_expired_operator_session()

    assert cleared is False


# ---------------------------------------------------------------------------
# 4. Open security audit view: quick actions panel links to dedicated view
# ---------------------------------------------------------------------------


def test_quick_actions_panel_open_audit_link_points_to_dedicated_view():
    context = SecurityContext(
        mode="operator",
        yubikey_present=True,
        key_name="primary",
        key_label="YubiKey-1",
        sensitive_enabled=True,
        secrets_unlocked=True,
    )
    html = dashboard.render_security_quick_actions_panel(context)

    assert 'href="#security-audit-dedicated-view"' in html
    assert "Open security audit view" in html


def test_dedicated_audit_view_has_correct_anchor_id():
    html = dashboard.render_security_audit_dedicated_view([], active_filter="all")
    assert 'id="security-audit-dedicated-view"' in html


def test_dedicated_audit_view_renders_events():
    events = [
        {
            "ts": "2026-04-20 12:00:00",
            "kind": "security.operator_session.unlocked",
            "message": "Operator session unlocked",
            "data": {"reason": "manual_unlock"},
        }
    ]
    html = dashboard.render_security_audit_dedicated_view(events)
    assert "security.operator_session.unlocked" in html
    assert 'data-security-audit-view-filter-row="session"' in html


def test_dedicated_audit_view_fallback_on_empty():
    html = dashboard.render_security_audit_dedicated_view([])
    assert "No security audit events." in html


# ---------------------------------------------------------------------------
# 5. Quick actions panel state-aware disabled states
# ---------------------------------------------------------------------------


def test_quick_actions_panel_unlock_disabled_when_already_unlocked():
    context = SecurityContext(
        mode="operator",
        yubikey_present=True,
        key_name="primary",
        key_label="YubiKey-1",
        sensitive_enabled=True,
        secrets_unlocked=True,
    )
    html = dashboard.render_security_quick_actions_panel(context)
    # Unlock chip must be disabled, Lock chip must be active
    assert 'data-security-quick-action="session unlock"' in html
    assert 'data-security-quick-action="session lock"' in html
    # Unlock should be disabled (session already unlocked)
    assert (
        'data-runtime-command="session unlock" data-security-quick-action="session unlock" style='
        in html
    )


def test_quick_actions_panel_demo_mode_both_session_chips_disabled():
    context = SecurityContext(
        mode="demo",
        yubikey_present=False,
        key_name=None,
        key_label=None,
        sensitive_enabled=False,
        secrets_unlocked=False,
    )
    html = dashboard.render_security_quick_actions_panel(context)
    # In demo mode, operator not present → unlock and lock both disabled
    assert "disabled" in html
    assert "Open security audit view" in html


def test_dashboard_html_contains_quick_actions_and_dedicated_view(monkeypatch):
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
    monkeypatch.setattr(dashboard, "read_events", lambda limit=25: [])

    html = dashboard.render_dashboard_html(
        [
            {
                "name": "X",
                "address": "AA:BB:CC:DD:EE:01",
                "vendor": "V",
                "rssi": -50,
                "risk_score": 10,
                "follow_score": 0,
                "confidence_score": 50,
                "final_score": 60,
                "alert_level": "low",
                "seen_count": 1,
                "reason_short": "",
                "flags": [],
                "watch_hit": False,
                "profile": "general_ble",
            }
        ],
        "2026-04-20_12-00-00",
    )

    assert "Security quick actions" in html
    assert "Security audit view" in html
    assert 'id="security-audit-dedicated-view"' in html
    assert "Open security audit view" in html
    assert 'href="#security-audit-dedicated-view"' in html
