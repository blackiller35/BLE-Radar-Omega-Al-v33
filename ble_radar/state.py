import json
from pathlib import Path

from ble_radar.config import (
    WHITELIST_FILE,
    WATCHLIST_FILE,
    LIVE_HISTORY_FILE,
    LAST_SCAN_FILE,
    SCAN_HISTORY_FILE,
    TRENDS_FILE,
    LEGACY_WHITELIST_FILE,
    LEGACY_WATCHLIST_FILE,
    LEGACY_LIVE_HISTORY_FILE,
    LEGACY_LAST_SCAN_FILE,
)


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _normalize_named_list(data):
    if not isinstance(data, list):
        return []
    out = []
    seen = set()
    for item in data:
        if isinstance(item, dict):
            address = str(item.get("address", "")).upper()
            name = str(item.get("name", ""))
        else:
            address = str(item).upper()
            name = ""
        key = (address, name)
        if not address or key in seen:
            continue
        seen.add(key)
        out.append({"address": address, "name": name})
    return out


def _migrate_if_needed():
    if not WHITELIST_FILE.exists() and LEGACY_WHITELIST_FILE.exists():
        save_json(WHITELIST_FILE, _normalize_named_list(load_json(LEGACY_WHITELIST_FILE, [])))
    if not WATCHLIST_FILE.exists() and LEGACY_WATCHLIST_FILE.exists():
        save_json(WATCHLIST_FILE, _normalize_named_list(load_json(LEGACY_WATCHLIST_FILE, [])))
    if not LIVE_HISTORY_FILE.exists() and LEGACY_LIVE_HISTORY_FILE.exists():
        save_json(LIVE_HISTORY_FILE, load_json(LEGACY_LIVE_HISTORY_FILE, {}))
    if not LAST_SCAN_FILE.exists() and LEGACY_LAST_SCAN_FILE.exists():
        save_json(LAST_SCAN_FILE, load_json(LEGACY_LAST_SCAN_FILE, []))

    for path, default in (
        (WHITELIST_FILE, []),
        (WATCHLIST_FILE, []),
        (LIVE_HISTORY_FILE, {}),
        (LAST_SCAN_FILE, []),
        (SCAN_HISTORY_FILE, []),
        (TRENDS_FILE, {}),
    ):
        if not path.exists():
            save_json(path, default)


_migrate_if_needed()


def load_whitelist():
    return _normalize_named_list(load_json(WHITELIST_FILE, []))


def save_whitelist(data):
    save_json(WHITELIST_FILE, _normalize_named_list(data))


def load_watchlist():
    return _normalize_named_list(load_json(WATCHLIST_FILE, []))


def save_watchlist(data):
    save_json(WATCHLIST_FILE, _normalize_named_list(data))


def load_live_history():
    data = load_json(LIVE_HISTORY_FILE, {})
    return data if isinstance(data, dict) else {}


def save_live_history(data):
    save_json(LIVE_HISTORY_FILE, data)


def load_last_scan():
    data = load_json(LAST_SCAN_FILE, [])
    return data if isinstance(data, list) else []


def save_last_scan(devices):
    save_json(LAST_SCAN_FILE, devices)


def load_scan_history():
    data = load_json(SCAN_HISTORY_FILE, [])
    return data if isinstance(data, list) else []


def save_scan_history(data):
    save_json(SCAN_HISTORY_FILE, data)


def append_scan_history(devices, stamp: str):
    history = load_scan_history()
    history.append({
        "stamp": stamp,
        "count": len(devices),
        "critical": sum(1 for d in devices if d.get("alert_level") == "critique"),
        "high": sum(1 for d in devices if d.get("alert_level") == "élevé"),
        "medium": sum(1 for d in devices if d.get("alert_level") == "moyen"),
        "devices": devices[:60],
    })
    history = history[-50:]
    save_scan_history(history)
    return history


def save_trends(data):
    save_json(TRENDS_FILE, data)


def load_trends():
    data = load_json(TRENDS_FILE, {})
    return data if isinstance(data, dict) else {}


def list_match(device, named_list):
    addr = str(device.get("address", "-")).upper()
    name = str(device.get("name", "Inconnu"))
    for item in named_list:
        if item.get("address", "").upper() == addr:
            return True
        if item.get("name") and item.get("name") == name:
            return True
    return False


def persist_live_observations(devices):
    hist = load_live_history()

    for d in devices:
        addr = str(d.get("address", "-")).upper()
        if not addr or addr == "-":
            continue

        row = hist.get(addr, {
            "name": d.get("name", "Inconnu"),
            "seen_count": 0,
            "near_count": 0,
            "last_rssi": -100,
            "last_alert_level": "faible",
            "last_profile": "unknown",
            "possible_suivi": False,
        })

        row["name"] = d.get("name", "Inconnu")
        row["seen_count"] = int(row.get("seen_count", 0)) + 1
        row["last_rssi"] = d.get("rssi", -100)
        row["last_alert_level"] = d.get("alert_level", "faible")
        row["last_profile"] = d.get("profile", "unknown")

        if d.get("rssi", -100) > -65:
            row["near_count"] = int(row.get("near_count", 0)) + 1

        if d.get("possible_suivi") or d.get("follow_score", 0) >= 45:
            row["possible_suivi"] = True

        hist[addr] = row

    save_live_history(hist)
    return hist


def build_trends():
    history = load_scan_history()
    last = history[-8:]

    counts = [x.get("count", 0) for x in last]
    criticals = [x.get("critical", 0) for x in last]
    highs = [x.get("high", 0) for x in last]
    mediums = [x.get("medium", 0) for x in last]

    data = {
        "scan_count": len(history),
        "last_counts": counts,
        "last_critical": criticals,
        "last_high": highs,
        "last_medium": mediums,
    }
    save_trends(data)
    return data
