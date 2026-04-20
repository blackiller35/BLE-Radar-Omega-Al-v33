from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .mode import SecurityContext


DEFAULT_SECRETS_PATH = Path("config/secrets.local.json")


def load_local_secrets(
    security: SecurityContext,
    secrets_path: str | Path | None = None,
) -> Dict[str, Any]:
    if not security.secrets_unlocked:
        return {}

    path = Path(secrets_path) if secrets_path else DEFAULT_SECRETS_PATH
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, dict):
        raise ValueError("secrets.local.json must contain a JSON object")

    return data
