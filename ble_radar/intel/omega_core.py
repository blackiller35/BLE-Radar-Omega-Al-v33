"""OMEGA Core Intel Engine."""

from __future__ import annotations

from ble_radar.intel.risk_tags import build_risk_tags, risk_level_from_tags
from ble_radar.intel.threat_context import build_threat_context

try:
    from ble_radar.intel.live_alerts import build_live_alert
except ImportError:

    def build_live_alert(device, context):
        return None


_CONFIDENCE_BY_LEVEL = {
    "low": 0.35,
    "medium": 0.65,
    "high": 0.9,
}


def build_omega_intel(device: dict) -> dict:
    tags = build_risk_tags(device)
    tag_level = risk_level_from_tags(tags)
    context = build_threat_context({**device, "risk_tags": tags})
    alert = build_live_alert(device, context)

    threat_level = context.get("severity") or tag_level
    confidence = _CONFIDENCE_BY_LEVEL.get(threat_level, 0.35)

    lowered = f"{device.get('name', '')} {device.get('vendor', '')}".lower()
    device_type = "general_ble"

    if any(
        word in lowered for word in ("tile", "airtag", "smarttag", "tracker", "beacon")
    ):
        device_type = "tracking_or_beacon"
    elif "RANDOMIZED_BLE_ADDRESS" in tags:
        device_type = "randomized_ble"
    elif "HIGH_ACTIVITY" in tags:
        device_type = "high_activity_ble"

    return {
        "address": context.get("address", device.get("address", "-")),
        "name": context.get("name", device.get("name", "Unknown")),
        "vendor": context.get("vendor", device.get("vendor", "Unknown")),
        "threat_level": threat_level,
        "confidence": confidence,
        "device_type": device_type,
        "risk_tags": tags,
        "reasons": context.get("reasons", []),
        "recommended_actions": context.get("recommended_actions", []),
        "summary": context.get("summary", ""),
        "live_alert": alert,
        "has_live_alert": alert is not None,
    }


def build_omega_intel_batch(devices: list[dict]) -> list[dict]:
    return [build_omega_intel(d) for d in devices or []]


def summarize_omega_intel(rows: list[dict]) -> dict:
    rows = rows or []
    high = [r for r in rows if r.get("threat_level") == "high"]
    medium = [r for r in rows if r.get("threat_level") == "medium"]
    live = [r for r in rows if r.get("has_live_alert")]

    return {
        "total": len(rows),
        "high": len(high),
        "medium": len(medium),
        "live_alerts": len(live),
        "top": rows[:5],
    }
