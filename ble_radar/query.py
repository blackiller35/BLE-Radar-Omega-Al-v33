import unicodedata

from ble_radar.selectors import sort_by_score


def normalize_text(text) -> str:
    if text is None:
        return ""
    text = str(text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def tokenize(text: str) -> list[str]:
    cleaned = normalize_text(text)
    for ch in ["/", ",", ";", ":", "|", "(", ")", "[", "]", "{", "}"]:
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


def match_score(query: str, device: dict) -> int:
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
        score += 110
    if q == vendor:
        score += 90
    if q == profile:
        score += 80

    for token in tokens:
        if token in addr:
            score += 70
        if token in name:
            score += 45
        if token in vendor:
            score += 28
        if token in profile:
            score += 28
        if token in alert:
            score += 24
        if token in classification:
            score += 20
        if token in reason:
            score += 14
        if token in hay:
            score += 10

        if token in ("critique", "critical") and alert == "critique":
            score += 35
        if token in ("eleve", "élevé", "high") and alert == "élevé":
            score += 30
        if token in ("moyen", "medium") and alert == "moyen":
            score += 22
        if token in ("tracker", "tag", "airtag", "tile") and profile == "tracker_probable":
            score += 34
        if token in ("watch", "watchlist") and device.get("watch_hit"):
            score += 28
        if token == "apple" and vendor == "Apple":
            score += 24
        if token == "random" and device.get("random_mac"):
            score += 20
        if token in ("new", "nouveau") and device.get("is_new_device"):
            score += 18
        if token in ("near", "proche") and device.get("persistent_nearby"):
            score += 18

    score += min(int(device.get("final_score", device.get("score", 0))) // 5, 20)
    return score


def query_devices(devices: list[dict], query: str, limit: int = 20) -> list[dict]:
    scored = []
    for d in devices:
        s = match_score(query, d)
        if s > 0:
            row = dict(d)
            row["_query_score"] = s
            scored.append(row)

    scored.sort(
        key=lambda x: (
            x.get("_query_score", 0),
            x.get("final_score", x.get("score", 0)),
            x.get("seen_count", 0),
        ),
        reverse=True,
    )
    return scored[:limit]


def query_history(history: list[dict], query: str, limit: int = 25) -> list[dict]:
    out = []
    for scan in history:
        stamp = scan.get("stamp") or scan.get("timestamp") or "-"
        for device in scan.get("devices", []):
            s = match_score(query, device)
            if s > 0:
                out.append({
                    "stamp": stamp,
                    "score": s,
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


def suggest_queries(devices: list[dict]) -> list[str]:
    devices = sort_by_score(devices)

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

    out = []
    out.extend([f"vendor {v}" for v in vendors[:5]])
    out.extend([f"profile {p}" for p in profiles[:5]])
    out.extend([f"alert {a}" for a in alerts[:4]])
    out.extend([
        "apple",
        "tracker",
        "watchlist",
        "random",
        "proche",
        "nouveau",
    ])
    return out[:16]
