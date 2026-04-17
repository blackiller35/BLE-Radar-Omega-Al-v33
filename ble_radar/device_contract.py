from copy import deepcopy


DEFAULT_DEVICE = {
    "name": "Inconnu",
    "address": "-",
    "vendor": "Unknown",
    "profile": "general_ble",
    "rssi": 0,
    "risk_score": 0,
    "follow_score": 0,
    "confidence_score": 0,
    "final_score": 0,
    "alert_level": "faible",
    "classification": "",
    "reason_short": "normal",
    "seen_count": 0,
    "near_count": 0,
    "possible_suivi": False,
    "persistent_nearby": False,
    "whitelisted": False,
    "watched": False,
    "watch_hit": False,
    "random_mac": False,
    "apple_prefix": False,
    "is_new_device": False,
    "flags": [],
}

REQUIRED_DEVICE_KEYS = tuple(DEFAULT_DEVICE.keys())


def normalize_device(device: dict | None) -> dict:
    base = deepcopy(DEFAULT_DEVICE)
    if device:
        base.update(device)

    flags = base.get("flags", [])
    if not isinstance(flags, list):
        flags = list(flags) if flags else []
    base["flags"] = flags

    if not base.get("reason_short"):
        base["reason_short"] = "normal"

    return base


def normalize_devices(devices: list[dict]) -> list[dict]:
    return [normalize_device(d) for d in devices]


def score_breakdown(device: dict) -> dict:
    d = normalize_device(device)
    return {
        "risk_score": int(d.get("risk_score", 0) or 0),
        "follow_score": int(d.get("follow_score", 0) or 0),
        "confidence_score": int(d.get("confidence_score", 0) or 0),
        "final_score": int(d.get("final_score", 0) or 0),
    }


def explain_device(device: dict) -> dict:
    d = normalize_device(device)
    scores = score_breakdown(d)

    summary = (
        f"risk={scores['risk_score']} | "
        f"follow={scores['follow_score']} | "
        f"confidence={scores['confidence_score']} | "
        f"final={scores['final_score']} | "
        f"reason={d['reason_short']}"
    )

    return {
        "name": d["name"],
        "address": d["address"],
        "alert_level": d["alert_level"],
        "reason_short": d["reason_short"],
        "flags": d["flags"],
        "scores": scores,
        "summary": summary,
    }
