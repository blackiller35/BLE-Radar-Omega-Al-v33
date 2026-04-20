from __future__ import annotations

import os
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
