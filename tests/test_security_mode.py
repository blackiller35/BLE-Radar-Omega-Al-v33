from ble_radar.security import mode
import os
import time


def test_no_key_returns_demo_locked(monkeypatch, tmp_path):
    monkeypatch.setattr(
        mode, "OPERATOR_SESSION_UNLOCK_FILE", tmp_path / "operator.unlock"
    )
    monkeypatch.setattr(mode, "detect_registered_yubikey", lambda allowed_tokens: None)

    security = mode.build_security_context()

    assert security.mode == "demo"
    assert security.yubikey_present is False
    assert security.secrets_unlocked is False
    assert security.sensitive_enabled is False


def test_key_present_returns_operator_still_locked(monkeypatch, tmp_path):
    unlock_path = tmp_path / "operator.unlock"
    monkeypatch.setattr(mode, "OPERATOR_SESSION_UNLOCK_FILE", unlock_path)
    mode.lock_operator_session()
    monkeypatch.setattr(
        mode,
        "detect_registered_yubikey",
        lambda allowed_tokens: {"name": "primary", "label": "YubiKey 5C NFC"},
    )

    security = mode.build_security_context()

    assert security.mode == "operator"
    assert security.yubikey_present is True
    assert security.secrets_unlocked is False
    assert security.sensitive_enabled is False


def test_explicit_unlock_enables_operator_secrets(monkeypatch, tmp_path):
    unlock_path = tmp_path / "operator.unlock"
    monkeypatch.setattr(mode, "OPERATOR_SESSION_UNLOCK_FILE", unlock_path)
    mode.lock_operator_session()
    monkeypatch.setattr(
        mode,
        "detect_registered_yubikey",
        lambda allowed_tokens: {"name": "primary", "label": "YubiKey 5C NFC"},
    )

    mode.unlock_operator_session()
    security = mode.build_security_context()

    assert security.mode == "operator"
    assert security.yubikey_present is True
    assert security.secrets_unlocked is True
    assert security.sensitive_enabled is True


def test_unlock_writes_audit_event(monkeypatch, tmp_path):
    unlock_path = tmp_path / "operator.unlock"
    monkeypatch.setattr(mode, "OPERATOR_SESSION_UNLOCK_FILE", unlock_path)

    events = []

    def _log_event(kind, level, message, data=None):
        events.append(
            {"kind": kind, "level": level, "message": message, "data": data or {}}
        )

    monkeypatch.setattr(mode, "log_event", _log_event)

    mode.unlock_operator_session()

    assert events
    assert events[-1]["kind"] == "security.operator_session.unlocked"


def test_lock_action_relocks_operator_session(monkeypatch, tmp_path):
    unlock_path = tmp_path / "operator.unlock"
    monkeypatch.setattr(mode, "OPERATOR_SESSION_UNLOCK_FILE", unlock_path)
    monkeypatch.setattr(
        mode,
        "detect_registered_yubikey",
        lambda allowed_tokens: {"name": "primary", "label": "YubiKey 5C NFC"},
    )

    mode.unlock_operator_session()
    unlocked = mode.build_security_context()
    assert unlocked.mode == "operator"
    assert unlocked.secrets_unlocked is True
    assert unlocked.sensitive_enabled is True

    mode.lock_operator_session()
    relocked = mode.build_security_context()
    assert relocked.mode == "operator"
    assert relocked.secrets_unlocked is False
    assert relocked.sensitive_enabled is False


def test_lock_writes_audit_event(monkeypatch, tmp_path):
    unlock_path = tmp_path / "operator.unlock"
    monkeypatch.setattr(mode, "OPERATOR_SESSION_UNLOCK_FILE", unlock_path)

    events = []

    def _log_event(kind, level, message, data=None):
        events.append(
            {"kind": kind, "level": level, "message": message, "data": data or {}}
        )

    monkeypatch.setattr(mode, "log_event", _log_event)

    mode.lock_operator_session()

    assert events
    assert events[-1]["kind"] == "security.operator_session.locked"


def test_expired_operator_session_treated_as_locked(monkeypatch, tmp_path):
    unlock_path = tmp_path / "operator.unlock"
    monkeypatch.setattr(mode, "OPERATOR_SESSION_UNLOCK_FILE", unlock_path)
    monkeypatch.setattr(mode, "OPERATOR_SESSION_TIMEOUT_SECONDS", 1)
    monkeypatch.setattr(
        mode,
        "detect_registered_yubikey",
        lambda allowed_tokens: {"name": "primary", "label": "YubiKey 5C NFC"},
    )

    mode.unlock_operator_session()
    stale = time.time() - 10
    os.utime(unlock_path, (stale, stale))

    security = mode.build_security_context()

    assert security.mode == "operator"
    assert security.secrets_unlocked is False
    assert security.sensitive_enabled is False
    assert unlock_path.exists() is False


def test_expired_session_writes_auto_lock_event(monkeypatch, tmp_path):
    unlock_path = tmp_path / "operator.unlock"
    monkeypatch.setattr(mode, "OPERATOR_SESSION_UNLOCK_FILE", unlock_path)
    monkeypatch.setattr(mode, "OPERATOR_SESSION_TIMEOUT_SECONDS", 1)
    monkeypatch.setattr(
        mode,
        "detect_registered_yubikey",
        lambda allowed_tokens: {"name": "primary", "label": "YubiKey 5C NFC"},
    )

    events = []

    def _log_event(kind, level, message, data=None):
        events.append(
            {"kind": kind, "level": level, "message": message, "data": data or {}}
        )

    monkeypatch.setattr(mode, "log_event", _log_event)

    mode.unlock_operator_session()
    stale = time.time() - 10
    os.utime(unlock_path, (stale, stale))

    _ = mode.build_security_context()

    assert any(e["kind"] == "security.operator_session.auto_locked" for e in events)


def test_read_operator_session_status_reflects_demo_and_operator(monkeypatch, tmp_path):
    unlock_path = tmp_path / "operator.unlock"
    monkeypatch.setattr(mode, "OPERATOR_SESSION_UNLOCK_FILE", unlock_path)

    monkeypatch.setattr(mode, "detect_registered_yubikey", lambda allowed_tokens: None)
    demo_status = mode.read_operator_session_status()
    assert demo_status["mode"] == "demo"
    assert demo_status["session_unlocked"] is False
    assert demo_status["sensitive_enabled"] is False

    monkeypatch.setattr(
        mode,
        "detect_registered_yubikey",
        lambda allowed_tokens: {"name": "primary", "label": "YubiKey 5C NFC"},
    )
    mode.unlock_operator_session()
    operator_status = mode.read_operator_session_status()
    assert operator_status["mode"] == "operator"
    assert operator_status["session_unlocked"] is True
    assert operator_status["sensitive_enabled"] is True


def test_expired_session_status_reports_locked(monkeypatch, tmp_path):
    unlock_path = tmp_path / "operator.unlock"
    monkeypatch.setattr(mode, "OPERATOR_SESSION_UNLOCK_FILE", unlock_path)
    monkeypatch.setattr(mode, "OPERATOR_SESSION_TIMEOUT_SECONDS", 1)
    monkeypatch.setattr(
        mode,
        "detect_registered_yubikey",
        lambda allowed_tokens: {"name": "primary", "label": "YubiKey 5C NFC"},
    )

    mode.unlock_operator_session()
    stale = time.time() - 10
    os.utime(unlock_path, (stale, stale))

    status = mode.read_operator_session_status()
    assert status["mode"] == "operator"
    assert status["session_unlocked"] is False
    assert status["sensitive_enabled"] is False
