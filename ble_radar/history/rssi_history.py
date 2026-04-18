from __future__ import annotations
from typing import Any, Dict, List


def _safe_int(value: Any, default: int = -999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def append_rssi_point(history: List[Dict[str, Any]], seen_at: str, rssi: Any) -> List[Dict[str, Any]]:
    history = history[:] if isinstance(history, list) else []
    history.append({"seen_at": seen_at, "rssi": _safe_int(rssi)})
    return history[-200:]


def rssi_stats(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not history:
        return {
            "count": 0,
            "avg_rssi": -999,
            "max_rssi": -999,
            "min_rssi": -999,
            "last_rssi": -999,
            "rssi_shift": 0,
        }

    values = [_safe_int(p.get("rssi")) for p in history]
    return {
        "count": len(values),
        "avg_rssi": int(sum(values) / len(values)),
        "max_rssi": max(values),
        "min_rssi": min(values),
        "last_rssi": values[-1],
        "rssi_shift": values[-1] - values[-2] if len(values) >= 2 else 0,
    }
