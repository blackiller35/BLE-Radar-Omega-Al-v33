import json

import pytest

from ble_radar.security import SecurityContext
from ble_radar.security.secrets import load_local_secrets


def test_load_local_secrets_operator_session_locked_denied(tmp_path):
    secrets_path = tmp_path / "secrets.local.json"
    secrets_path.write_text(json.dumps({"api_key": "x"}), encoding="utf-8")

    security = SecurityContext(
        mode="operator",
        yubikey_present=True,
        key_name="primary",
        key_label="YubiKey-1",
        sensitive_enabled=False,
        secrets_unlocked=False,
    )

    with pytest.raises(PermissionError):
        load_local_secrets(security, secrets_path=secrets_path)


def test_load_local_secrets_operator_session_unlocked_allowed(tmp_path):
    secrets_path = tmp_path / "secrets.local.json"
    secrets_path.write_text(json.dumps({"api_key": "x"}), encoding="utf-8")

    security = SecurityContext(
        mode="operator",
        yubikey_present=True,
        key_name="primary",
        key_label="YubiKey-1",
        sensitive_enabled=True,
        secrets_unlocked=True,
    )

    data = load_local_secrets(security, secrets_path=secrets_path)

    assert data["api_key"] == "x"
