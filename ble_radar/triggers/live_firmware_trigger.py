from __future__ import annotations


UNKNOWN_VALUES = {"", "unknown", "n/a", "none", "null"}


def _norm(value) -> str:
    return str(value or "").strip().lower()


def should_trigger_firmware_analysis(device: dict) -> bool:
    """Return True when a BLE device deserves firmware/operator review."""
    name = _norm(device.get("name"))
    vendor = _norm(device.get("vendor"))
    tags = {_norm(tag) for tag in device.get("tags", [])}
    score = int(device.get("score") or device.get("risk_score") or device.get("threat_score") or 0)
    rssi = int(device.get("rssi") or -100)

    unknown_identity = name in UNKNOWN_VALUES or vendor in UNKNOWN_VALUES
    suspicious_tags = {
        "persistent_unknown",
        "untrusted_iot",
        "weak_device_profile",
        "tracking",
        "neartracking",
        "firmware_high_risk",
        "firmware_medium_risk",
    }

    return (
        unknown_identity
        or score >= 60
        or rssi >= -45
        or bool(tags & suspicious_tags)
    )


def build_live_firmware_trigger(device: dict) -> dict:
    """Build operator-facing firmware trigger context for a BLE device."""
    triggered = should_trigger_firmware_analysis(device)

    reasons = []
    name = _norm(device.get("name"))
    vendor = _norm(device.get("vendor"))
    tags = {_norm(tag) for tag in device.get("tags", [])}
    score = int(device.get("score") or device.get("risk_score") or device.get("threat_score") or 0)
    rssi = int(device.get("rssi") or -100)

    if name in UNKNOWN_VALUES or vendor in UNKNOWN_VALUES:
        reasons.append("unknown device identity/vendor")
    if score >= 60:
        reasons.append("high BLE risk score")
    if rssi >= -45:
        reasons.append("close-proximity signal")
    if tags:
        for tag in sorted(tags):
            if tag in {
                "persistent_unknown",
                "untrusted_iot",
                "weak_device_profile",
                "tracking",
                "neartracking",
                "firmware_high_risk",
                "firmware_medium_risk",
            }:
                reasons.append(f"suspicious tag: {tag.upper()}")

    return {
        "triggered": triggered,
        "device": {
            "name": device.get("name") or "Unknown",
            "address": device.get("address") or device.get("mac") or "",
            "vendor": device.get("vendor") or "Unknown",
        },
        "recommended_action": (
            "Run local firmware reverse analysis if a firmware image is available."
            if triggered
            else "No firmware action required; continue baseline monitoring."
        ),
        "reasons": reasons or ["baseline BLE behavior"],
    }


def build_live_firmware_triggers(devices: list[dict]) -> list[dict]:
    return [build_live_firmware_trigger(device) for device in devices]
