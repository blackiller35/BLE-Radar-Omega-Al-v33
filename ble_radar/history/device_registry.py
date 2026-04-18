from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable

from ble_radar.config import HISTORY_DIR
from ble_radar.state import load_json, save_json

DEVICE_REGISTRY_FILE = HISTORY_DIR / "device_registry.json"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_address(address: Any) -> str:
    return str(address or "").strip().upper()


def _empty_record(address: str, seen_at: str) -> Dict[str, Any]:
    return {
        "address": address,
        "first_seen": seen_at,
        "last_seen": seen_at,
        "seen_count": 0,
        "session_count": 0,
        "last_session_id": "",
    }


def _normalize_registry(data: Any) -> Dict[str, Dict[str, Any]]:
    now = _now()
    if not isinstance(data, dict):
        return {}

    out: Dict[str, Dict[str, Any]] = {}
    for key, value in data.items():
        src = value if isinstance(value, dict) else {}
        address = _normalize_address(src.get("address") or key)
        if not address:
            continue

        seen_count = max(0, _safe_int(src.get("seen_count", 0), 0))
        session_count = max(0, _safe_int(src.get("session_count", 0), 0))
        first_seen = str(src.get("first_seen") or now)
        last_seen = str(src.get("last_seen") or first_seen)

        out[address] = {
            "address": address,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "seen_count": seen_count,
            "session_count": session_count,
            "last_session_id": str(src.get("last_session_id", "") or ""),
        }

    return out


def load_registry() -> Dict[str, Dict[str, Any]]:
    DEVICE_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DEVICE_REGISTRY_FILE.exists():
        save_json(DEVICE_REGISTRY_FILE, {})
        return {}
    return _normalize_registry(load_json(DEVICE_REGISTRY_FILE, {}))


def save_registry(registry: Dict[str, Dict[str, Any]]) -> None:
    DEVICE_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    save_json(DEVICE_REGISTRY_FILE, _normalize_registry(registry))


def update_registry_with_devices(
    devices: Iterable[Dict[str, Any]],
    registry: Dict[str, Dict[str, Any]] | None = None,
    session_id: str | None = None,
    seen_at: str | None = None,
) -> Dict[str, Dict[str, Any]]:
    current = _normalize_registry(registry if registry is not None else load_registry())
    stamp = str(seen_at or _now())
    sid = str(session_id).strip() if session_id is not None else ""
    batch_session_touched = set()

    for device in devices or []:
        if not isinstance(device, dict):
            continue

        address = _normalize_address(device.get("address"))
        if not address:
            continue

        row = current.get(address)
        if row is None:
            row = _empty_record(address, stamp)
            current[address] = row

        row["last_seen"] = stamp
        row["seen_count"] = _safe_int(row.get("seen_count", 0), 0) + 1

        if sid:
            if row.get("last_session_id") != sid:
                row["session_count"] = _safe_int(row.get("session_count", 0), 0) + 1
                row["last_session_id"] = sid
        elif address not in batch_session_touched:
            row["session_count"] = _safe_int(row.get("session_count", 0), 0) + 1
            batch_session_touched.add(address)

    return current
