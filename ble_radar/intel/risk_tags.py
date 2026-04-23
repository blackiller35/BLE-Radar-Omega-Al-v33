def compute_risk_tags(device: dict) -> list[str]:
    tags: list[str] = []

    rssi = device.get("rssi", -100)
    seen_count = device.get("seen_count", 0)
    name = (device.get("name") or "").lower()

    if rssi > -60:
        tags.append("STRONG_SIGNAL")

    if seen_count >= 5:
        tags.append("PERSISTENT_UNKNOWN")

    if seen_count >= 3 and rssi > -70:
        tags.append("NEAR_TRACKING")

    if any(x in name for x in ["tv", "iot", "camera", "esp", "smart"]):
        tags.append("UNTRUSTED_IOT")

    return tags
