import os

from ble_radar.security import yubikey_guard


ALLOWED_TOKENS = [
    {"name": "primary", "label": "YubiKey 5C NFC", "enabled": True},
    {"name": "backup", "label": "YubiKey 5 NFC", "enabled": True},
]


def test_real_detection_path_returns_recognized_token(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BLE_OMEGA_KEY", raising=False)
    monkeypatch.setattr(
        yubikey_guard,
        "_detect_real_yubikey_hint_linux",
        lambda: "YubiKey 5C NFC",
    )

    token = yubikey_guard.detect_registered_yubikey(ALLOWED_TOKENS)

    assert token is not None
    assert token["name"] == "primary"


def test_fallback_env_path_still_works(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(yubikey_guard, "_detect_real_yubikey_hint_linux", lambda: None)
    monkeypatch.setenv("BLE_OMEGA_KEY", "backup")

    token = yubikey_guard.detect_registered_yubikey(ALLOWED_TOKENS)

    assert token is not None
    assert token["name"] == "backup"


def test_no_key_returns_none(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(yubikey_guard, "_detect_real_yubikey_hint_linux", lambda: None)
    monkeypatch.delenv("BLE_OMEGA_KEY", raising=False)

    token = yubikey_guard.detect_registered_yubikey(ALLOWED_TOKENS)

    assert token is None
