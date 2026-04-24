"""OMEGA BLE fingerprint classification helpers."""

from __future__ import annotations

APPLE_COMPANY_ID = "0x004c"


def _norm(value: object) -> str:
    return str(value or "").strip().lower()


def classify_ble_device(device: dict) -> dict:
    """Classify a BLE device from simple observed behavior.

    Expected optional keys:
    - name
    - vendor
    - company_id
    - has_active_connection
    - notification_rate
    - services
    """

    name = _norm(device.get("name"))
    vendor = _norm(device.get("vendor"))
    company_id = _norm(device.get("company_id"))
    services = [_norm(s) for s in device.get("services", []) or []]

    active = bool(device.get("has_active_connection", False))
    notification_rate = float(device.get("notification_rate", 0) or 0)

    tags: list[str] = []
    confidence = 35
    category = "unknown_ble"
    summary = "Appareil BLE non catégorisé."

    if active and notification_rate >= 5:
        tags.append("ACTIVE_DEVICE")
        confidence += 25

    if "mx master" in name or "logitech" in vendor:
        category = "mouse_keyboard"
        tags.extend(["HID_DEVICE", "LOGITECH_DEVICE"])
        confidence += 35
        summary = "Périphérique HID actif probable: souris/clavier BLE."

    elif active and any("hid" in s or "human interface" in s for s in services):
        category = "mouse_keyboard"
        tags.append("HID_DEVICE")
        confidence += 30
        summary = "Périphérique HID BLE actif probable."

    elif company_id == APPLE_COMPANY_ID and not active:
        category = "possible_airtag"
        tags.extend(["APPLE_BLE", "PASSIVE_BROADCAST"])
        confidence += 25
        summary = "Broadcast Apple passif: compatible AirTag ou appareil Apple BLE."

    elif active and notification_rate >= 10:
        category = "active_iot_or_sensor"
        tags.append("TALKATIVE_BLE")
        confidence += 20
        summary = "Appareil BLE actif avec flux de notifications élevé."

    if not active and notification_rate == 0:
        tags.append("PASSIVE_BROADCAST")

    return {
        "category": category,
        "tags": sorted(set(tags)),
        "confidence": min(confidence, 100),
        "summary": summary,
    }
