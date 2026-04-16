from ble_radar.selectors import sort_by_score


def view_critical(devices):
    return [d for d in devices if d.get("alert_level") == "critique"]


def view_high_plus(devices):
    return [
        d for d in devices
        if d.get("alert_level") in ("critique", "élevé")
    ]


def view_trackers(devices):
    return [
        d for d in devices
        if d.get("profile") == "tracker_probable"
        or d.get("possible_suivi")
        or d.get("watch_hit")
    ]


def view_watch_hits(devices):
    return [d for d in devices if d.get("watch_hit")]


def view_new_devices(devices):
    return [d for d in devices if d.get("is_new_device")]


def view_nearby(devices):
    return [d for d in devices if d.get("persistent_nearby")]


def view_apple_like(devices):
    return [
        d for d in devices
        if d.get("vendor") == "Apple" or d.get("apple_prefix")
    ]


def view_random_mac(devices):
    return [d for d in devices if d.get("random_mac")]


def view_unknown_vendor(devices):
    return [d for d in devices if d.get("vendor", "Unknown") == "Unknown"]


def view_top_hot(devices, n=15):
    return sort_by_score(devices)[:n]


def summarize_views(devices):
    return {
        "critical": len(view_critical(devices)),
        "high_plus": len(view_high_plus(devices)),
        "trackers": len(view_trackers(devices)),
        "watch_hits": len(view_watch_hits(devices)),
        "new_devices": len(view_new_devices(devices)),
        "nearby": len(view_nearby(devices)),
        "apple_like": len(view_apple_like(devices)),
        "random_mac": len(view_random_mac(devices)),
        "unknown_vendor": len(view_unknown_vendor(devices)),
    }
