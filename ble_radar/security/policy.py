from __future__ import annotations

from .mode import SecurityContext
from ble_radar.eventlog import log_event


def is_operator_mode(security: SecurityContext) -> bool:
    return security.mode == "operator"


def is_sensitive_feature_enabled(security: SecurityContext) -> bool:
    return security.sensitive_enabled


def require_operator(security: SecurityContext) -> None:
    if not is_operator_mode(security):
        raise PermissionError("Operator mode requires a recognized YubiKey")


def require_sensitive_feature(security: SecurityContext) -> None:
    if not is_sensitive_feature_enabled(security):
        log_event(
            "security.sensitive_action.denied",
            "warning",
            "Sensitive action denied",
            {
                "mode": security.mode,
                "yubikey_present": security.yubikey_present,
                "session_unlocked": security.secrets_unlocked,
            },
        )
        raise PermissionError("Sensitive feature is locked")
    log_event(
        "security.sensitive_action.allowed",
        "info",
        "Sensitive action allowed",
        {
            "mode": security.mode,
            "yubikey_present": security.yubikey_present,
            "session_unlocked": security.secrets_unlocked,
        },
    )
