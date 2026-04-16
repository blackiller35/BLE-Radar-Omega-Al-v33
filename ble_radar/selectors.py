def sort_by_score(devices):
    return sorted(
        devices,
        key=lambda d: (
            d.get("final_score", d.get("score", 0)),
            d.get("follow_score", 0),
            d.get("seen_count", 0),
        ),
        reverse=True,
    )


def only_alerts(devices, min_level="moyen"):
    levels = {"faible": 0, "moyen": 1, "élevé": 2, "critique": 3}
    threshold = levels.get(min_level, 1)
    return [
        d for d in devices
        if levels.get(d.get("alert_level", "faible"), 0) >= threshold
    ]


def only_trackers(devices):
    return [
        d for d in devices
        if d.get("profile") == "tracker_probable"
        or d.get("possible_suivi")
        or d.get("watch_hit")
    ]


def only_watch_hits(devices):
    return [d for d in devices if d.get("watch_hit")]


def only_vendor(devices, vendor_name: str):
    vendor_name = str(vendor_name).strip().lower()
    return [d for d in devices if str(d.get("vendor", "")).lower() == vendor_name]


def only_profile(devices, profile_name: str):
    profile_name = str(profile_name).strip().lower()
    return [d for d in devices if str(d.get("profile", "")).lower() == profile_name]


def top_n(devices, n=10):
    return sort_by_score(devices)[:n]


def group_counts(devices, key_name: str):
    counts = {}
    for d in devices:
        key = d.get(key_name, "Unknown")
        counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)
