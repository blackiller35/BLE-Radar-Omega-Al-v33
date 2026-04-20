from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Optional

from .registry import get_enabled_tokens, get_policy
from .yubikey_guard import detect_registered_yubikey


OPERATOR_SESSION_UNLOCK_FILE = Path("runtime/operator_session.unlock")
OPERATOR_SESSION_TIMEOUT_SECONDS = 900


def is_operator_session_unlocked() -> bool:
    try:
        if not OPERATOR_SESSION_UNLOCK_FILE.exists():
            return False

        age_seconds = time.time() - OPERATOR_SESSION_UNLOCK_FILE.stat().st_mtime
        if (
            OPERATOR_SESSION_TIMEOUT_SECONDS > 0
            and age_seconds > OPERATOR_SESSION_TIMEOUT_SECONDS
        ):
            lock_operator_session()
            return False

        value = OPERATOR_SESSION_UNLOCK_FILE.read_text(
            encoding="utf-8", errors="ignore"
        ).strip()
        return value.lower() in {"1", "true", "yes", "unlocked"}
    except Exception:
        return False


def unlock_operator_session() -> None:
    OPERATOR_SESSION_UNLOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    OPERATOR_SESSION_UNLOCK_FILE.write_text("unlocked", encoding="utf-8")


def lock_operator_session() -> None:
    try:
        if OPERATOR_SESSION_UNLOCK_FILE.exists():
            OPERATOR_SESSION_UNLOCK_FILE.unlink()
    except Exception:
        return


def read_operator_session_status(config_path: str | Path | None = None) -> dict:
    security = build_security_context(config_path=config_path)
    return {
        "mode": security.mode,
        "yubikey_present": security.yubikey_present,
        "session_unlocked": security.secrets_unlocked,
        "sensitive_enabled": security.sensitive_enabled,
        "session_timeout_seconds": OPERATOR_SESSION_TIMEOUT_SECONDS,
    }


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

    session_unlocked = is_operator_session_unlocked()

    return SecurityContext(
        mode=recognized_key_mode,
        yubikey_present=True,
        key_name=token_name,
        key_label=token_label,
        sensitive_enabled=session_unlocked,
        secrets_unlocked=session_unlocked,
    )
