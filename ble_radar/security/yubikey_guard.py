from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional


def _match_token_name(
    requested_name: str,
    allowed_tokens: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    requested_name = requested_name.strip().lower()

    for token in allowed_tokens:
        name = str(token.get("name", "")).strip().lower()
        if name == requested_name:
            return token

    return None


def _match_token_hint(
    detected_hint: str,
    allowed_tokens: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    hint = detected_hint.strip().lower()
    if not hint:
        return None

    for token in allowed_tokens:
        name = str(token.get("name", "")).strip().lower()
        label = str(token.get("label", "")).strip().lower()
        if name and (name in hint or hint in name):
            return token
        if label and (label in hint or hint in label):
            return token

    return None


def _read_text_if_exists(path: Path) -> str:
    try:
        if path.exists():
            return path.read_text(encoding="utf-8", errors="ignore").strip()
    except Exception:
        return ""
    return ""


def _detect_real_yubikey_hint_linux() -> Optional[str]:
    if platform.system() != "Linux":
        return None

    # Prefer hidraw discovery first: this is usually present on Linux/Kali desktops.
    try:
        for uevent in Path("/sys/class/hidraw").glob("hidraw*/device/uevent"):
            content = _read_text_if_exists(uevent)
            if not content:
                continue
            lowered = content.lower()
            if "yubico" not in lowered and "yubikey" not in lowered:
                continue
            for line in content.splitlines():
                if line.startswith("HID_NAME="):
                    return line.split("=", 1)[1].strip()
            return "YubiKey"
    except Exception:
        pass

    # Fallback to usb sysfs metadata (manufacturer/product).
    try:
        for dev in Path("/sys/bus/usb/devices").glob("*"):
            manufacturer = _read_text_if_exists(dev / "manufacturer")
            product = _read_text_if_exists(dev / "product")
            if "yubico" in manufacturer.lower() or "yubikey" in product.lower():
                if product:
                    return product
                if manufacturer:
                    return manufacturer
                return "YubiKey"
    except Exception:
        pass

    return None


def detect_registered_yubikey(
    allowed_tokens: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    V1 simple et pratique pour projet local.

    Méthodes supportées:
    1. Variable d'environnement:
       BLE_OMEGA_KEY=primary
       BLE_OMEGA_KEY=backup

    2. Fichier local de simulation:
       runtime/yubikey.token
       contenu: primary ou backup
    """
    # 0. Real Linux/Kali YubiKey detection (best effort, non-fatal).
    detected_hint = _detect_real_yubikey_hint_linux()
    if detected_hint:
        token = _match_token_hint(detected_hint, allowed_tokens)
        if token:
            return token

    env_value = os.getenv("BLE_OMEGA_KEY", "").strip()
    if env_value:
        token = _match_token_name(env_value, allowed_tokens)
        if token:
            return token

    marker_path = Path("runtime/yubikey.token")
    if marker_path.exists():
        file_value = marker_path.read_text(encoding="utf-8").strip()
        if file_value:
            token = _match_token_name(file_value, allowed_tokens)
            if token:
                return token

    return None
