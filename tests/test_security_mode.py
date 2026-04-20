from ble_radar.security import mode


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
