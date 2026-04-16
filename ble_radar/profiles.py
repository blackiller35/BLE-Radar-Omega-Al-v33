from ble_radar.config import STATE_DIR
from ble_radar.state import load_json, save_json

PROFILE_STATE_FILE = STATE_DIR / "profile_mode.json"

PRESETS = {
    "balanced": {
        "key": "balanced",
        "label": "Balanced",
        "scan_seconds": 5,
        "live_seconds": 3,
        "alert_floor": "moyen",
        "description": "Profil standard équilibré.",
    },
    "paranoid": {
        "key": "paranoid",
        "label": "Paranoid",
        "scan_seconds": 7,
        "live_seconds": 2,
        "alert_floor": "faible",
        "description": "Plus sensible, plus agressif sur la détection.",
    },
    "tracker_hunt": {
        "key": "tracker_hunt",
        "label": "Tracker Hunt",
        "scan_seconds": 6,
        "live_seconds": 2,
        "alert_floor": "faible",
        "description": "Optimisé pour trackers, watch hits et proximité.",
    },
    "quiet": {
        "key": "quiet",
        "label": "Quiet",
        "scan_seconds": 4,
        "live_seconds": 4,
        "alert_floor": "élevé",
        "description": "Moins de bruit, remonte surtout le plus important.",
    },
}

if not PROFILE_STATE_FILE.exists():
    save_json(PROFILE_STATE_FILE, {"active": "balanced"})


def load_profile_key() -> str:
    data = load_json(PROFILE_STATE_FILE, {"active": "balanced"})
    key = str(data.get("active", "balanced"))
    if key not in PRESETS:
        key = "balanced"
    return key


def set_profile_key(key: str):
    key = str(key).strip()
    if key not in PRESETS:
        key = "balanced"
    save_json(PROFILE_STATE_FILE, {"active": key})
    return get_active_profile()


def get_active_profile() -> dict:
    return PRESETS[load_profile_key()]


def list_profiles():
    return [PRESETS[k] for k in PRESETS]
