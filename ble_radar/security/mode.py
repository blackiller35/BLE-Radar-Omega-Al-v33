from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .registry import get_enabled_tokens, get_policy
from .yubikey_guard import detect_registered_yubikey


@dataclass(frozen=True)
class SecurityContext:
    mode: str
    yubikey_present: bool
    key_name: Optional[str]
    key_label: Optional[str]
    sensitive_enabled: bool
    secrets_unlocked: bool

    def status_lines(self) -> list[str]:
        return [
            f"mode={self.mode}",
            f"yubikey_present={self.yubikey_present}",
            f"key_name={self.key_name or 'none'}",
            f"key_label={self.key_label or 'none'}",
            f"sensitive_enabled={self.sensitive_enabled}",
            f"secrets_unlocked={self.secrets_unlocked}",
        ]


def build_security_context(config_path: str | Path | None = None) -> SecurityContext:
    allowed_tokens = get_enabled_tokens(config_path)
    policy = get_policy(config_path)

    detected = detect_registered_yubikey(allowed_tokens)

    no_key_mode = str(policy.get("no_key_mode", "demo"))
    recognized_key_mode = str(policy.get("recognized_key_mode", "operator"))
    allow_backup = bool(policy.get("allow_backup_for_operator", True))

    if detected is None:
        return SecurityContext(
            mode=no_key_mode,
            yubikey_present=False,
            key_name=None,
            key_label=None,
            sensitive_enabled=False,
            secrets_unlocked=False,
        )

    token_name = str(detected.get("name", "")).strip().lower()
    token_label = str(detected.get("label", token_name or "recognized-token"))

    if token_name == "backup" and not allow_backup:
        return SecurityContext(
            mode=no_key_mode,
            yubikey_present=True,
            key_name=token_name,
            key_label=token_label,
            sensitive_enabled=False,
            secrets_unlocked=False,
        )

    return SecurityContext(
        mode=recognized_key_mode,
        yubikey_present=True,
        key_name=token_name,
        key_label=token_label,
        sensitive_enabled=True,
        secrets_unlocked=True,
    )
