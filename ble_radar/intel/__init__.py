
from .risk_tags import compute_risk_tags

def get_vendor_summary(devices):
    counts = {}
    for d in devices or []:
        vendor = (
            d.get("vendor")
            or d.get("vendor_name")
            or d.get("manufacturer")
            or "Unknown"
        )
        vendor = str(vendor).strip() or "Unknown"
        counts[vendor] = counts.get(vendor, 0) + 1

    return [
        {"vendor": v, "count": c}
        for v, c in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    ]

def get_tracker_candidates(devices):
    rows = []
    for d in devices or []:
        tags = compute_risk_tags(d)
        if "NEAR_TRACKING" in tags or "PERSISTENT_UNKNOWN" in tags:
            rows.append({
                "address": d.get("address", ""),
                "name": d.get("name", "Unknown"),
                "risk_tags": tags,
                "rssi": d.get("rssi"),
                "seen_count": d.get("seen_count", 0),
            })
    return rows

def build_intel(devices):
    devices = devices or []
    return {
        "devices": devices,
        "vendor_summary": get_vendor_summary(devices),
        "tracker_candidates": get_tracker_candidates(devices),
    }

def compare_device_sets(old, new):
    old = old or []
    new = new or []

    old_keys = {str(d.get("address","")).upper() for d in old if d.get("address")}
    new_keys = {str(d.get("address","")).upper() for d in new if d.get("address")}

    return {
        "new": list(new_keys - old_keys),
        "gone": list(old_keys - new_keys),
        "same": list(old_keys & new_keys),
    }
