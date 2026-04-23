from __future__ import annotations


def build_risk_tags(device: dict) -> list[str]:
    address = str(device.get("address", "")).strip().lower()
    hits = int(device.get("hits", 0) or 0)

    tags: list[str] = []

    def add(tag: str):
        if tag not in tags:
            tags.append(tag)

    # Activity levels
    if hits >= 3000:
        add("PERSISTENT_DEVICE")
        add("HIGH_ACTIVITY")
    elif hits >= 1000:
        add("ACTIVE_DEVICE")
    elif hits >= 250:
        add("OBSERVED_DEVICE")

    # Randomized BLE detection
    if address:
        first_byte = address.split(":")[0]
        if first_byte in {"06", "16", "17", "26", "3e", "4e", "51", "59"}:
            add("RANDOMIZED_BLE_ADDRESS")

    # Advanced tags
    if "PERSISTENT_DEVICE" in tags and "RANDOMIZED_BLE_ADDRESS" in tags:
        add("TRACKING_SUSPECT")

    if "HIGH_ACTIVITY" in tags and "RANDOMIZED_BLE_ADDRESS" in tags:
        add("PRIORITY_REVIEW")

    return tags


def risk_level_from_tags(tags: list[str]) -> str:
    tags_set = set(tags)

    if "TRACKING_SUSPECT" in tags_set or "PRIORITY_REVIEW" in tags_set:
        return "high"
    if "PERSISTENT_DEVICE" in tags_set or "HIGH_ACTIVITY" in tags_set:
        return "medium"
    return "low"
