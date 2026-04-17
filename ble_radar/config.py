from pathlib import Path
import json

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT_DIR / "reports"
HISTORY_DIR = ROOT_DIR / "history"
STATE_DIR = ROOT_DIR / "state"

WHITELIST_FILE = STATE_DIR / "whitelist.json"
WATCHLIST_FILE = STATE_DIR / "watchlist.json"
LIVE_HISTORY_FILE = STATE_DIR / "live_devices.json"
LAST_SCAN_FILE = STATE_DIR / "last_scan.json"
SCAN_HISTORY_FILE = HISTORY_DIR / "scan_history.json"
TRENDS_FILE = HISTORY_DIR / "trends.json"

LEGACY_WHITELIST_FILE = HISTORY_DIR / "whitelist.json"
LEGACY_WATCHLIST_FILE = HISTORY_DIR / "watchlist.json"
LEGACY_LIVE_HISTORY_FILE = HISTORY_DIR / "live_devices.json"
LEGACY_LAST_SCAN_FILE = HISTORY_DIR / "last_scan.json"

QUICK_SCAN_SECONDS = 3
FULL_SCAN_SECONDS = 5
LIVE_SCAN_SECONDS = 3

ALERT_MEDIUM = 35
ALERT_HIGH = 60
ALERT_CRITICAL = 82

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)

RUNTIME_CONFIG_FILE = ROOT_DIR / "ble_radar" / "config.json"
EXAMPLE_CONFIG_FILE = ROOT_DIR / "ble_radar" / "config.example.json"

DEFAULT_RUNTIME_CONFIG = {
    "scan_timeout": FULL_SCAN_SECONDS,
    "log_dir": "logs",
    "aegis": {
        "enabled": True,
        "priority_high": 70,
        "priority_critical": 85,
        "watch_hits": 1,
        "critical_alerts": 1,
        "high_alerts": 2,
        "campaign_count": 1,
        "tracker_cluster": 2,
        "escalations": 2,
    },
    "automation": {
        "enabled": True,
        "rules": [
            {
                "id": "watch_hit_audit",
                "label": "Audit auto si watchlist hit",
                "enabled": True,
                "condition": "watch_hits_ge",
                "threshold": 1,
                "action": "export_audit",
            },
            {
                "id": "critical_snapshot",
                "label": "Snapshot auto si alerte critique",
                "enabled": True,
                "condition": "critical_ge",
                "threshold": 1,
                "action": "create_snapshot",
            },
            {
                "id": "tracker_incident",
                "label": "Incident auto si trackers >= 2",
                "enabled": True,
                "condition": "trackers_ge",
                "threshold": 2,
                "action": "log_incident",
            },
            {
                "id": "radio_incident",
                "label": "Incident auto si santé radio <= 45",
                "enabled": True,
                "condition": "health_le",
                "threshold": 45,
                "action": "log_incident",
            },
        ],
    },
    "lists": {
        "whitelist": [],
        "watchlist": [],
    },
    "ui": {
        "theme": "default",
        "show_banner": True,
    },
}


def _deep_merge_dict(base, override):
    if not isinstance(base, dict):
        return override
    if not isinstance(override, dict):
        return base

    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_json_config(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_runtime_config():
    data = dict(DEFAULT_RUNTIME_CONFIG)
    data = _deep_merge_dict(data, _load_json_config(EXAMPLE_CONFIG_FILE))
    data = _deep_merge_dict(data, _load_json_config(RUNTIME_CONFIG_FILE))
    return data


def get_runtime_section(name, default=None):
    cfg = load_runtime_config()
    value = cfg.get(name, default if default is not None else {})
    return value if isinstance(value, dict) else (default if default is not None else {})
