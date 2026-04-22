from __future__ import annotations

import json

from ble_radar.config import STATE_DIR

POST_SCAN_PREFERENCE_FILE = STATE_DIR / "post_scan_preference.json"
VALID_POST_SCAN_OPEN_MODES = {"ask", "dashboard", "operator_panel", "both", "none"}
DEFAULT_POST_SCAN_PREFERENCE = {"open_mode": "ask"}


def load_post_scan_preference() -> dict:
    try:
        data = json.loads(POST_SCAN_PREFERENCE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}

    mode = str(data.get("open_mode", "ask")).strip().lower()
    if mode not in VALID_POST_SCAN_OPEN_MODES:
        mode = "ask"

    return {"open_mode": mode}


def save_post_scan_preference(open_mode: str) -> dict:
    mode = str(open_mode or "ask").strip().lower()
    if mode not in VALID_POST_SCAN_OPEN_MODES:
        mode = "ask"

    POST_SCAN_PREFERENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"open_mode": mode}
    POST_SCAN_PREFERENCE_FILE.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    return payload


def get_post_scan_open_mode() -> str:
    return load_post_scan_preference()["open_mode"]
