import unicodedata

from ble_radar.state import load_scan_history


def normalize_text(text) -> str:
    if text is None:
        return ""
    text = str(text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def tokenize(text: str) -> list[str]:
    cleaned = normalize_text(text)
    for ch in ["/", ",", ";", ":", "|", "(", ")", "[", "]"]:
        cleaned = cleaned.replace(ch, " ")
    return [t for t in cleaned.split() if t]


def flatten_device(device: dict) -> str:
    parts = [
        device.get("name", ""),
        device.get("address", ""),
        device.get("vendor", ""),
        device.get("profile", ""),
        device.get("classification", ""),
        device.get("alert_level", ""),
        device.get("reason_short", ""),
    ]

    reason_full = device.get("reason_full", [])
    if isinstance(reason_full, list):
        parts.extend(reason_full)

    flags = device.get("flags", [])
    if isinstance(flags, list):
        parts.extend(flags)

    return normalize_text(" ".join(str(x) for x in parts if x))


def device_search_score(query: str, device: dict) -> int:
    q = normalize_text(query)
    if not q:
        return int(device.get("final_score", device.get("score", 0)))

    tokens = tokenize(query)
    hay = flatten_device(device)

    addr = normalize_text(device.get("address", ""))
    name = normalize_text(device.get("name", ""))
    vendor = normalize_text(device.get("vendor", ""))
    profile = normalize_text(device.get("profile", ""))
    alert = normalize_text(device.get("alert_level", ""))
    classification = normalize_text(device.get("classification", ""))
    reason = normalize_text(device.get("reason_short", ""))

    score = 0

    if q == addr:
        score += 150
    if q == name:
        score += 100
    if q == vendor:
        score += 80
    if q == profile:
        score += 70

    for token in tokens:
        if token in addr:
            score += 60
        if token in name:
            score += 40
        if token in vendor:
            score += 28
        if token in profile:
            score += 28
        if token in alert:
            score += 28
        if token in classification:
            score += 18
        if token in reason:
            score += 12
        if token in hay:
            score += 10

        if token in ("critique", "critical") and alert == "critique":
            score += 40
        if token in ("eleve", "élevé", "high") and alert == "élevé":
            score += 35
        if token in ("moyen", "medium") and alert == "moyen":
            score += 25
        if token in ("tracker", "tag", "airtag", "tile") and profile == "tracker_probable":
            score += 35
        if token in ("watchlist", "watch") and device.get("watch_hit"):
            score += 30
        if token in ("apple",) and vendor == "Apple":
            score += 25
        if token in ("random",) and device.get("random_mac"):
            score += 20
        if token in ("new", "nouveau") and device.get("is_new_device"):
            score += 18
        if token in ("near", "proche") and device.get("persistent_nearby"):
            score += 18

    score += min(int(device.get("final_score", device.get("score", 0))) // 5, 20)
    return score


def search_devices(devices: list[dict], query: str, limit: int = 20) -> list[dict]:
    scored = []
    for d in devices:
        score = device_search_score(query, d)
        if score > 0:
            row = dict(d)
            row["_search_score"] = score
            scored.append(row)

    scored.sort(
        key=lambda x: (
            x.get("_search_score", 0),
            x.get("final_score", x.get("score", 0)),
            x.get("seen_count", 0),
        ),
        reverse=True,
    )
    return scored[:limit]


def search_scan_history(query: str, history: list[dict] | None = None, limit: int = 25) -> list[dict]:
    if history is None:
        history = load_scan_history()

    out = []
    for scan in history:
        stamp = scan.get("stamp") or scan.get("timestamp") or "-"
        for device in scan.get("devices", []):
            score = device_search_score(query, device)
            if score > 0:
                out.append({
                    "stamp": stamp,
                    "score": score,
                    "device": device,
                })

    out.sort(
        key=lambda x: (
            x.get("score", 0),
            x["device"].get("final_score", x["device"].get("score", 0)),
            x["device"].get("seen_count", 0),
        ),
        reverse=True,
    )
    return out[:limit]


def build_suggestions(devices: list[dict]) -> list[str]:
    vendors = []
    profiles = []
    alerts = []

    seen_vendor = set()
    seen_profile = set()
    seen_alert = set()

    for d in devices:
        vendor = d.get("vendor", "Unknown")
        profile = d.get("profile", "general_ble")
        alert = d.get("alert_level", "faible")

        if vendor not in seen_vendor:
            vendors.append(vendor)
            seen_vendor.add(vendor)
        if profile not in seen_profile:
            profiles.append(profile)
            seen_profile.add(profile)
        if alert not in seen_alert:
            alerts.append(alert)
            seen_alert.add(alert)

    suggestions = []
    suggestions.extend([f"vendor {v}" for v in vendors[:5]])
    suggestions.extend([f"profile {p}" for p in profiles[:5]])
    suggestions.extend([f"alert {a}" for a in alerts[:4]])
    suggestions.extend([
        "apple",
        "tracker",
        "watchlist",
        "random",
        "proche",
        "nouveau",
    ])
    return suggestions[:16]


def explain_device(device: dict) -> list[str]:
    lines = [
        f"Nom: {device.get('name', 'Inconnu')}",
        f"Adresse: {device.get('address', '-')}",
        f"Vendor: {device.get('vendor', 'Unknown')}",
        f"Profil: {device.get('profile', 'general_ble')}",
        f"RSSI: {device.get('rssi', '-')}",
        f"Risk score: {device.get('risk_score', 0)}",
        f"Follow score: {device.get('follow_score', 0)}",
        f"Confidence score: {device.get('confidence_score', 0)}",
        f"Final score: {device.get('final_score', 0)}",
        f"Alerte: {device.get('alert_level', 'faible')}",
        f"Seen count: {device.get('seen_count', 0)}",
        f"Near count: {device.get('near_count', 0)}",
        f"Flags: {', '.join(device.get('flags', [])) if device.get('flags') else '-'}",
    ]

    reason_full = device.get("reason_full", [])
    if isinstance(reason_full, list) and reason_full:
        lines.append("Raisons détaillées:")
        for r in reason_full:
            lines.append(f"- {r}")
    else:
        lines.append(f"Raison: {device.get('reason_short', 'normal')}")

    return lines


def compare_last_two_scans(history: list[dict] | None = None):
    if history is None:
        history = load_scan_history()

    if len(history) < 2:
        return None

    previous = history[-2]
    current = history[-1]

    prev_devices = previous.get("devices", [])
    curr_devices = current.get("devices", [])

    old = {str(x.get("address", "-")).upper(): x for x in prev_devices}
    new = {str(x.get("address", "-")).upper(): x for x in curr_devices}

    return {
        "previous_stamp": previous.get("stamp") or previous.get("timestamp") or "-",
        "current_stamp": current.get("stamp") or current.get("timestamp") or "-",
        "added": [new[a] for a in new if a not in old],
        "removed": [old[a] for a in old if a not in new],
        "common": [new[a] for a in new if a in old],
    }
