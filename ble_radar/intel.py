from ble_radar.analyzer import analyze_devices
from ble_radar.vendors import guess_vendor
from ble_radar.config import ALERT_MEDIUM, ALERT_HIGH, ALERT_CRITICAL
from ble_radar.state import (
    load_whitelist,
    load_watchlist,
    load_live_history,
    load_last_scan,
    list_match,
)

AUDIO_HINTS = ("buds", "pods", "headset", "audio", "speaker", "ear")
WATCH_HINTS = ("watch", "band", "fit", "fitbit")
PHONE_HINTS = ("iphone", "phone", "pixel", "galaxy", "android")
TRACKER_HINTS = ("airtag", "tag", "tile", "mate", "tracker")


def clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


def infer_profile(name: str, vendor: str, flags: list[str], watch_hit: bool) -> str:
    low = (name or "").lower()

    if watch_hit:
        return "watchlist_hit"
    if any(x in low for x in TRACKER_HINTS):
        return "tracker_probable"
    if any(x in low for x in AUDIO_HINTS):
        return "audio_accessory"
    if any(x in low for x in WATCH_HINTS):
        return "watch"
    if any(x in low for x in PHONE_HINTS):
        return "phone"
    if vendor == "Tile":
        return "tracker_probable"
    if "random" in flags and vendor == "Unknown":
        return "unknown_random"
    return "general_ble"


def build_intel(raw_devices):
    base = analyze_devices(raw_devices)
    whitelist = load_whitelist()
    watchlist = load_watchlist()
    live_history = load_live_history()
    previous = {str(x.get("address", "-")).upper(): x for x in load_last_scan()}

    enriched = []

    for d in base:
        item = dict(d)
        addr = str(item.get("address", "-")).upper()
        name = str(item.get("name", "Inconnu"))
        rssi = int(item.get("rssi", -100))
        vendor = guess_vendor(addr, name)
        hist = live_history.get(addr, {})

        old_seen = int(hist.get("seen_count", 0))
        old_near = int(hist.get("near_count", 0))
        seen_count = old_seen + 1
        near_count = old_near + (1 if rssi > -65 else 0)

        item["vendor"] = vendor
        item["whitelisted"] = list_match(item, whitelist)
        item["watched"] = list_match(item, watchlist)
        item["watch_hit"] = item["watched"]
        item["is_new_device"] = addr not in previous
        item["seen_count"] = seen_count
        item["near_count"] = near_count
        item["persistent_nearby"] = near_count >= 2 and rssi > -70

        reason_full = []

        if item.get("random_mac"):
            reason_full.append("mac aléatoire probable")
        if item.get("apple_prefix"):
            reason_full.append("préfixe Apple détecté")
        if seen_count >= 2:
            reason_full.append(f"réapparition x{seen_count}")
        if item["persistent_nearby"]:
            reason_full.append("proximité persistante")
        if item["watch_hit"]:
            reason_full.append("présent dans la watchlist")
        if name == "Inconnu":
            reason_full.append("nom inconnu")
        if vendor != "Unknown":
            reason_full.append(f"vendor estimé: {vendor}")

        risk_score = int(item.get("score", 0))
        follow_score = 0
        confidence_score = 40

        if seen_count >= 2:
            follow_score += min(seen_count * 6, 24)
            confidence_score += 8
        if item["persistent_nearby"]:
            follow_score += 16
            risk_score += 10
        if item.get("random_mac"):
            risk_score += 10
            follow_score += 8
        if item.get("apple_prefix"):
            risk_score += 6
        if item["watch_hit"]:
            risk_score += 18
            follow_score += 18
            confidence_score += 12
        if rssi > -60:
            risk_score += 8
            follow_score += 8
        if vendor != "Unknown":
            confidence_score += 10
        if not item["is_new_device"]:
            follow_score += 8

        flags = []
        if item.get("random_mac"):
            flags.append("random")
        if item.get("apple_prefix"):
            flags.append("apple")
        if item["persistent_nearby"]:
            flags.append("near")
        if item["watch_hit"]:
            flags.append("watch")
        if item["is_new_device"]:
            flags.append("new")

        profile = infer_profile(name, vendor, flags, item["watch_hit"])

        if profile == "tracker_probable":
            risk_score += 12
            follow_score += 12
            confidence_score += 8
            reason_full.append("profil tracker probable")
        elif profile == "audio_accessory":
            risk_score -= 8
            reason_full.append("profil audio probable")
        elif profile == "watch":
            risk_score -= 6
            reason_full.append("profil montre probable")
        elif profile == "phone":
            risk_score -= 10
            reason_full.append("profil téléphone probable")
        elif profile == "unknown_random":
            risk_score += 10
            reason_full.append("appareil aléatoire inconnu")

        if item["whitelisted"]:
            risk_score -= 35
            follow_score -= 30
            confidence_score += 5
            reason_full.append("appareil whitelisté")

        risk_score = clamp(risk_score)
        follow_score = clamp(follow_score)
        confidence_score = clamp(confidence_score)

        final_score = clamp(round(risk_score * 0.45 + follow_score * 0.45 + confidence_score * 0.10))

        if item["whitelisted"]:
            alert_level = "faible"
        elif final_score >= ALERT_CRITICAL:
            alert_level = "critique"
        elif final_score >= ALERT_HIGH:
            alert_level = "élevé"
        elif final_score >= ALERT_MEDIUM:
            alert_level = "moyen"
        else:
            alert_level = "faible"

        possible_suivi = follow_score >= 45 or item["persistent_nearby"] or item["watch_hit"]
        if hist.get("possible_suivi"):
            possible_suivi = True

        if alert_level in ("critique", "élevé"):
            classification = "suspect"
        elif alert_level == "moyen":
            classification = "à surveiller"
        else:
            classification = "normal"

        item["risk_score"] = risk_score
        item["follow_score"] = follow_score
        item["confidence_score"] = confidence_score
        item["final_score"] = final_score
        item["threat_score"] = final_score
        item["alert_level"] = alert_level
        item["classification"] = classification
        item["possible_suivi"] = possible_suivi
        item["profile"] = profile
        item["flags"] = flags
        item["reason_full"] = reason_full
        item["reason_short"] = ", ".join(reason_full[:3]) if reason_full else "normal"

        enriched.append(item)

    return sorted(enriched, key=lambda x: x.get("final_score", 0), reverse=True)


def get_alert_devices(devices, min_level="moyen"):
    levels = {"faible": 0, "moyen": 1, "élevé": 2, "critique": 3}
    threshold = levels.get(min_level, 1)
    return [d for d in devices if levels.get(d.get("alert_level", "faible"), 0) >= threshold]


def get_tracker_candidates(devices):
    return [
        d for d in devices
        if d.get("possible_suivi")
        or d.get("watch_hit")
        or d.get("profile") == "tracker_probable"
    ]


def get_vendor_summary(devices):
    counts = {}
    for d in devices:
        vendor = d.get("vendor", "Unknown")
        counts[vendor] = counts.get(vendor, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)


def compare_device_sets(current_devices, previous_devices):
    old = {str(x.get("address", "-")).upper(): x for x in previous_devices}
    new = {str(x.get("address", "-")).upper(): x for x in current_devices}
    return {
        "added": [new[a] for a in new if a not in old],
        "removed": [old[a] for a in old if a not in new],
        "common": [new[a] for a in new if a in old],
    }
