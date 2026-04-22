from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

HISTORY_PATH = Path("history/alerts_history.json")


def _load():
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text())
    except Exception:
        return []


def _save(data):
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_PATH.write_text(json.dumps(data[-1000:], indent=2))
    except Exception:
        pass


def record_alert(event: dict, profile: dict):
    data = _load()

    entry = {
        "timestamp": datetime.now().isoformat(),
        "device": event.get("device"),
        "score": event.get("score"),
        "type": event.get("type"),
        "profile": profile.get("name"),
    }

    data.append(entry)
    _save(data)


def get_recent_alerts(limit=10):
    data = _load()
    return data[-limit:]
