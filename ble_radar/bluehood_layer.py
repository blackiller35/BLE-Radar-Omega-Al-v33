from __future__ import annotations
from typing import Any, Dict, List

from ble_radar.history.device_history import new_device_record, update_device_record
from ble_radar.history.rssi_history import append_rssi_point, rssi_stats
from ble_radar.history.presence_timeline import build_presence_timeline
from ble_radar.analysis.proximity import proximity_summary
from ble_radar.analysis.correlation import build_correlation_pairs, top_correlated
from ble_radar.watchlist.watchlist import load_watchlist, match_watchlist


def enrich_devices_for_session(
    devices: List[Dict[str, Any]],
    registry: Dict[str, Dict[str, Any]],
    session_id: str,
    seen_at: str,
    watchlist_path: str = "data/watchlist/watchlist.json",
) -> Dict[str, Any]:
    registry = dict(registry or {})
    watchlist = load_watchlist(watchlist_path)
    enriched: List[Dict[str, Any]] = []

    for device in devices:
        address = device.get("address") or ""
        if not address:
            continue

        existing = registry.get(address)
        if existing is None:
            record = new_device_record(device, session_id, seen_at)
            is_new = True
        else:
            record = update_device_record(existing, device, session_id, seen_at)
            is_new = False

        history = record.get("rssi_history", [])
        history = append_rssi_point(history, seen_at, device.get("rssi"))
        record["rssi_history"] = history
        record["rssi_stats"] = rssi_stats(history)
        record["proximity"] = proximity_summary(device)
        record["watch"] = match_watchlist(device, watchlist)
        record["is_new"] = is_new

        registry[address] = record

        enriched.append({
            **device,
            "is_new": is_new,
            "history": {
                "first_seen": record.get("first_seen"),
                "last_seen": record.get("last_seen"),
                "times_seen": record.get("times_seen"),
                "session_count": record.get("session_count"),
                "avg_rssi": record.get("avg_rssi"),
            },
            "rssi_stats": record.get("rssi_stats", {}),
            "proximity": record.get("proximity", {}),
            "watch": record.get("watch", {}),
        })

    pairs = build_correlation_pairs(enriched)
    return {
        "registry": registry,
        "devices_enriched": enriched,
        "presence_timeline": build_presence_timeline(list(registry.values())),
        "top_correlated": top_correlated(pairs),
        "watch_hits": [d for d in enriched if d.get("watch", {}).get("matched")],
    }
