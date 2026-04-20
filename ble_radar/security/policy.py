from __future__ import annotations

from .mode import SecurityContext


def is_operator_mode(security: SecurityContext) -> bool:
    return security.mode == "operator"


def is_sensitive_feature_enabled(security: SecurityContext) -> bool:
    return security.sensitive_enabled


def require_operator(security: SecurityContext) -> None:
    if not is_operator_mode(security):
        raise PermissionError("Operator mode requires a recognized YubiKey")


def require_sensitive_feature(security: SecurityContext) -> None:
    if not is_sensitive_feature_enabled(security):
        raise PermissionError("Sensitive feature is locked")
