import pytest

from ble_radar.security.mode import SecurityContext
from ble_radar.security import policy


def test_denied_sensitive_action_writes_audit_event(monkeypatch):
    events = []

    def _log_event(kind, level, message, data=None):
        events.append(
            {"kind": kind, "level": level, "message": message, "data": data or {}}
        )

    monkeypatch.setattr(policy, "log_event", _log_event)

    security = SecurityContext(
        mode="operator",
        yubikey_present=True,
        key_name="primary",
        key_label="YubiKey-1",
        sensitive_enabled=False,
        secrets_unlocked=False,
    )

    with pytest.raises(PermissionError):
        policy.require_sensitive_feature(security)

    assert events
    assert events[-1]["kind"] == "security.sensitive_action.denied"
