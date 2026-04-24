def build_risk_tags(device: dict) -> list[str]:
    tags = []

    confidence = float(device.get("confidence", 0) or 0)
    hits = int(device.get("hits", device.get("seen_count", 0)) or 0)
    name = str(device.get("name", "")).lower()
    address = str(device.get("address", "")).lower()

    if confidence > 0.8:
        tags.append("HIGH_CONFIDENCE")

    if hits >= 3000:
        tags.append("PERSISTENT_DEVICE")
        tags.append("HIGH_ACTIVITY")

    if address.startswith(("02:", "06:", "0a:", "0e:", "12:", "16:", "1a:", "1e:", "22:", "26:", "2a:", "2e:", "32:", "36:", "3a:", "3e:")):
        tags.append("RANDOMIZED_BLE_ADDRESS")

    if "PERSISTENT_DEVICE" in tags and "RANDOMIZED_BLE_ADDRESS" in tags:
        tags.append("TRACKING_SUSPECT")
        tags.append("PRIORITY_REVIEW")

    if name and "iphone" not in name and "samsung" not in name:
        tags.append("UNKNOWN_VENDOR")

    if device.get("has_live_alert"):
        tags.append("LIVE_ALERT")

    return tags


def compute_risk_tags(device: dict) -> list[str]:
    return build_risk_tags(device)


def risk_level_from_tags(tags: list[str]) -> str:
    high_tags = {"HIGH_CONFIDENCE", "LIVE_ALERT", "TRACKING_SUSPECT", "PRIORITY_REVIEW"}
    medium_tags = {"PERSISTENT_DEVICE", "HIGH_ACTIVITY", "UNKNOWN_VENDOR", "RANDOMIZED_BLE_ADDRESS", "TRACKING_SUSPECT", "PRIORITY_REVIEW"}

    if any(tag in high_tags for tag in tags):
        return "high"
    if any(tag in medium_tags for tag in tags):
        return "medium"
    return "low"
