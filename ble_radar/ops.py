from statistics import mean
import unicodedata

SCAN_MODES = {
    "quick": {"label": "Rapide", "seconds": 3},
    "normal": {"label": "Normal", "seconds": 5},
    "deep": {"label": "Profond", "seconds": 8},
}


def get_scan_mode(key: str):
    key = str(key or "normal").strip().lower()
    return SCAN_MODES.get(key, SCAN_MODES["normal"])


def radio_health(devices):
    if not devices:
        return {
            "score": 100,
            "label": "calme",
            "avg_rssi": -100,
            "unknown_vendor": 0,
            "random_mac": 0,
            "alerts": 0,
            "trackers": 0,
        }

    avg_rssi = round(mean(
        d.get("rssi", -100)
        for d in devices
        if isinstance(d.get("rssi", -100), (int, float))
    ), 2)

    critical = sum(1 for d in devices if d.get("alert_level") == "critique")
    high = sum(1 for d in devices if d.get("alert_level") == "élevé")
    medium = sum(1 for d in devices if d.get("alert_level") == "moyen")
    alerts = critical + high + medium
    unknown_vendor = sum(1 for d in devices if d.get("vendor", "Unknown") == "Unknown")
    random_mac = sum(1 for d in devices if d.get("random_mac"))
    trackers = sum(1 for d in devices if d.get("profile") == "tracker_probable" or d.get("possible_suivi") or d.get("watch_hit"))
    near = sum(1 for d in devices if d.get("persistent_nearby"))

    score = 100
    score -= critical * 16
    score -= high * 10
    score -= medium * 4
    score -= min(unknown_vendor * 2, 12)
    score -= min(random_mac * 2, 12)
    score -= min(trackers * 4, 20)
    score -= min(near * 2, 10)

    if avg_rssi > -68:
        score -= 8
    if avg_rssi > -60:
        score -= 6

    score = max(0, min(100, int(score)))

    if score >= 85:
        label = "calme"
    elif score >= 65:
        label = "surveillance"
    elif score >= 40:
        label = "dense"
    else:
        label = "instable"

    return {
        "score": score,
        "label": label,
        "avg_rssi": avg_rssi,
        "unknown_vendor": unknown_vendor,
        "random_mac": random_mac,
        "alerts": alerts,
        "trackers": trackers,
    }


def compare_scan_sets(current_devices, previous_devices):
    old = {str(x.get("address", "-")).upper(): x for x in previous_devices}
    new = {str(x.get("address", "-")).upper(): x for x in current_devices}

    return {
        "added": [new[a] for a in new if a not in old],
        "removed": [old[a] for a in old if a not in new],
        "common": [new[a] for a in new if a in old],
    }


def changed_alerts(current_devices, previous_devices):
    old = {str(x.get("address", "-")).upper(): x for x in previous_devices}
    changed = []

    for d in current_devices:
        addr = str(d.get("address", "-")).upper()
        if addr not in old:
            continue

        prev = old[addr]
        curr_alert = d.get("alert_level", "faible")
        prev_alert = prev.get("alert_level", "faible")
        curr_score = int(d.get("final_score", d.get("score", 0)))
        prev_score = int(prev.get("final_score", prev.get("score", 0)))

        if curr_alert != prev_alert or abs(curr_score - prev_score) >= 10:
            changed.append({
                "current": d,
                "previous": prev,
            })

    return sorted(
        changed,
        key=lambda x: x["current"].get("final_score", x["current"].get("score", 0)),
        reverse=True,
    )


def tracker_rank(devices):
    ranked = [
        d for d in devices
        if d.get("profile") == "tracker_probable"
        or d.get("possible_suivi")
        or d.get("watch_hit")
    ]
    return sorted(
        ranked,
        key=lambda d: (
            d.get("watch_hit", False),
            d.get("follow_score", 0),
            d.get("final_score", d.get("score", 0)),
            d.get("seen_count", 0),
        ),
        reverse=True,
    )


def normalize_text(text) -> str:
    text = str(text or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def match_device_text(device: dict, query: str) -> bool:
    q = normalize_text(query)
    if not q:
        return False

    hay = " ".join([
        str(device.get("name", "")),
        str(device.get("address", "")),
        str(device.get("vendor", "")),
        str(device.get("profile", "")),
        str(device.get("reason_short", "")),
    ]).lower()

    return q in hay
