from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_CONFIG_PATH = Path("config/security.local.json")


def _default_registry() -> Dict[str, Any]:
    return {
        "allowed_tokens": [
            {
                "name": "primary",
                "enabled": True,
                "label": "YubiKey 5C NFC",
            },
            {
                "name": "backup",
                "enabled": True,
                "label": "YubiKey 5 NFC",
            },
        ],
        "policy": {
            "no_key_mode": "demo",
            "recognized_key_mode": "operator",
            "allow_backup_for_operator": True,
        },
    }


def load_registry(config_path: str | Path | None = None) -> Dict[str, Any]:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    if not path.exists():
        return _default_registry()

    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, dict):
        raise ValueError("security.local.json must contain a JSON object")

    merged = _default_registry()
    merged.update(data)

    if "allowed_tokens" not in merged or not isinstance(merged["allowed_tokens"], list):
        raise ValueError("allowed_tokens must be a list")

    if "policy" not in merged or not isinstance(merged["policy"], dict):
        raise ValueError("policy must be an object")

    return merged


def get_enabled_tokens(config_path: str | Path | None = None) -> List[Dict[str, Any]]:
    registry = load_registry(config_path)
    tokens = registry.get("allowed_tokens", [])
    return [token for token in tokens if token.get("enabled", True)]


def get_policy(config_path: str | Path | None = None) -> Dict[str, Any]:
    registry = load_registry(config_path)
    return dict(registry.get("policy", {}))
