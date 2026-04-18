from __future__ import annotations
from typing import Any, Dict


def _safe_int(value: Any, default: int = -999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def proximity_zone(rssi: Any) -> str:
    value = _safe_int(rssi)
    if value >= -55:
        return "immediate"
    if value >= -67:
        return "near"
    if value >= -80:
        return "mid"
    return "far"


def proximity_summary(device: Dict[str, Any]) -> Dict[str, Any]:
    rssi = _safe_int(device.get("rssi"))
    zone = proximity_zone(rssi)
    confidence = "low"
    if rssi >= -67:
        confidence = "high"
    elif rssi >= -80:
        confidence = "medium"

    return {
        "zone": zone,
        "confidence": confidence,
        "distance_hint": {
            "immediate": "very close",
            "near": "close",
            "mid": "moderate",
            "far": "distant",
        }[zone],
    }
