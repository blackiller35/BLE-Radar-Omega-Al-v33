"""OMEGA Intel Map - defensive BLE intelligence layer."""

from __future__ import annotations


def normalize_tags(tags) -> set[str]:
    return {str(t).upper().strip() for t in (tags or []) if str(t).strip()}


def signal_bucket(rssi) -> str:
    try:
        value = int(rssi)
    except (TypeError, ValueError):
        return "unknown"

    if value >= -50:
        return "very_close"
    if value >= -70:
        return "near"
    if value >= -85:
        return "medium"
    return "far"


def build_omega_intel_map(device: dict) -> dict:
    name = str(device.get("name") or "").strip()
    address = str(device.get("address") or device.get("mac") or "").strip()
    vendor = str(device.get("vendor") or "Unknown").strip()
    rssi = device.get("rssi")
    hits = int(device.get("hits", device.get("seen_count", 0)) or 0)
    tags = normalize_tags(device.get("risk_tags") or device.get("tags"))

    if not name or name.lower() in {"unknown", "n/a", "none"}:
        tags.add("WEAK_DEVICE_PROFILE")

    if vendor.lower() == "unknown" and not name:
        tags.add("UNTRUSTED_IOT")

    if hits >= 5:
        tags.add("PERSISTENT_DEVICE")

    bucket = signal_bucket(rssi)

    if bucket in {"very_close", "near"} and "RANDOMIZED_BLE_ADDRESS" in tags:
        tags.add("TRACKING_SUSPECT")

    risk = "low"
    if "TRACKING_SUSPECT" in tags:
        risk = "high"
    elif {"PERSISTENT_DEVICE", "UNTRUSTED_IOT", "WEAK_DEVICE_PROFILE"} & tags:
        risk = "medium"

    reasons = []
    if "TRACKING_SUSPECT" in tags:
        reasons.append("randomized or tracking-like BLE behavior")
    if "PERSISTENT_DEVICE" in tags:
        reasons.append("device observed repeatedly")
    if "WEAK_DEVICE_PROFILE" in tags:
        reasons.append("device identity is weak or missing")
    if "UNTRUSTED_IOT" in tags:
        reasons.append("unknown IoT-like device profile")
    if bucket in {"very_close", "near"}:
        reasons.append(f"signal proximity: {bucket}")

    if risk == "high":
        action = "Review sightings, compare with known devices, and monitor future appearances."
    elif risk == "medium":
        action = "Monitor recurrence and enrich device identity before escalation."
    else:
        action = "No immediate action required; keep baseline monitoring active."

    return {
        "identity": {
            "name": name or "Unknown",
            "address": address,
            "vendor": vendor,
        },
        "signal": {
            "rssi": rssi,
            "bucket": bucket,
        },
        "history": {
            "hits": hits,
            "persistent": "PERSISTENT_DEVICE" in tags,
        },
        "risk": {
            "level": risk,
            "tags": sorted(tags),
            "reasons": reasons or ["no suspicious BLE indicators"],
        },
        "context": {
            "summary": f"{risk.upper()} BLE context for {name or address or 'unknown device'}",
            "operator_note": "; ".join(reasons) if reasons else "baseline behavior",
        },
        "recommended_action": action,
    }


def build_omega_intel_maps(devices: list[dict]) -> list[dict]:
    return [build_omega_intel_map(device) for device in devices]
