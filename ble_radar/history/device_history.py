from __future__ import annotations
from typing import Any, Dict, List


def _safe_int(value: Any, default: int = -999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def new_device_record(device: Dict[str, Any], session_id: str, seen_at: str) -> Dict[str, Any]:
    name = device.get("name") or "Unknown"
    vendor = device.get("vendor") or "Unknown"
    rssi = _safe_int(device.get("rssi"))

    return {
        "address": device.get("address", ""),
        "name": name,
        "aliases": [name] if name != "Unknown" else [],
        "vendor": vendor,
        "vendors_seen": [vendor] if vendor != "Unknown" else [],
        "first_seen": seen_at,
        "last_seen": seen_at,
        "times_seen": 1,
        "session_count": 1,
        "sessions_seen": [session_id],
        "avg_rssi": rssi,
        "max_rssi": rssi,
        "min_rssi": rssi,
        "last_rssi": rssi,
        "presence_buckets": [seen_at[:13]],
    }


def update_device_record(record: Dict[str, Any], device: Dict[str, Any], session_id: str, seen_at: str) -> Dict[str, Any]:
    name = device.get("name") or "Unknown"
    vendor = device.get("vendor") or "Unknown"
    rssi = _safe_int(device.get("rssi"))

    aliases = _safe_list(record.get("aliases"))
    if name != "Unknown" and name not in aliases:
        aliases.append(name)

    vendors_seen = _safe_list(record.get("vendors_seen"))
    if vendor != "Unknown" and vendor not in vendors_seen:
        vendors_seen.append(vendor)

    sessions_seen = _safe_list(record.get("sessions_seen"))
    if session_id not in sessions_seen:
        sessions_seen.append(session_id)

    buckets = _safe_list(record.get("presence_buckets"))
    bucket = seen_at[:13]
    if bucket not in buckets:
        buckets.append(bucket)

    old_avg = _safe_int(record.get("avg_rssi"))
    times_seen = _safe_int(record.get("times_seen"), 0) + 1
    avg_rssi = int(((old_avg * max(times_seen - 1, 0)) + rssi) / max(times_seen, 1))

    record.update({
        "name": name if name != "Unknown" else record.get("name", "Unknown"),
        "aliases": aliases,
        "vendor": vendor if vendor != "Unknown" else record.get("vendor", "Unknown"),
        "vendors_seen": vendors_seen,
        "last_seen": seen_at,
        "times_seen": times_seen,
        "session_count": len(sessions_seen),
        "sessions_seen": sessions_seen,
        "avg_rssi": avg_rssi,
        "max_rssi": max(_safe_int(record.get("max_rssi")), rssi),
        "min_rssi": min(_safe_int(record.get("min_rssi")), rssi),
        "last_rssi": rssi,
        "presence_buckets": buckets,
    })
    return record
