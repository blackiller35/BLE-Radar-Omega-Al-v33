from datetime import datetime
from pathlib import Path
import json

from ble_radar.config import HISTORY_DIR

EVENT_LOG_FILE = HISTORY_DIR / "event_log.jsonl"
EVENT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def event_stamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_event(kind: str, level: str, message: str, data=None):
    row = {
        "ts": event_stamp(),
        "kind": str(kind),
        "level": str(level),
        "message": str(message),
        "data": data or {},
    }
    with EVENT_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def read_events(limit=50):
    if not EVENT_LOG_FILE.exists():
        return []

    rows = []
    for line in EVENT_LOG_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue

    rows.reverse()
    return rows[:limit]


def clear_events():
    EVENT_LOG_FILE.write_text("", encoding="utf-8")
