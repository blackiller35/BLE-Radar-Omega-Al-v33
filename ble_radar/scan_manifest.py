from __future__ import annotations

import json
from pathlib import Path

from ble_radar.device_contract import normalize_device


SCAN_MANIFESTS_DIR = Path("reports/manifests")


def _ensure_manifests_dir() -> Path:
    SCAN_MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    return SCAN_MANIFESTS_DIR


def _safe_int(value, default=0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def build_scan_manifest(devices: list[dict], stamp: str, extra_meta: dict | None = None) -> dict:
    items = [normalize_device(d) for d in devices]

    critical = sum(1 for d in items if d.get("alert_level") == "critique")
    high = sum(1 for d in items if d.get("alert_level") == "élevé")
    medium = sum(1 for d in items if d.get("alert_level") == "moyen")
    low = sum(1 for d in items if d.get("alert_level") == "faible")

    watch_hits = sum(1 for d in items if d.get("watch_hit"))
    trackers = sum(
        1
        for d in items
        if d.get("possible_suivi")
        or d.get("watch_hit")
        or "tracker" in str(d.get("profile", "")).lower()
    )

    vendors = {}
    for d in items:
        vendor = str(d.get("vendor", "Unknown"))
        vendors[vendor] = vendors.get(vendor, 0) + 1

    top_vendors = sorted(vendors.items(), key=lambda x: (-x[1], x[0]))[:5]

    top_devices = sorted(items, key=lambda d: _safe_int(d.get("final_score", 0)), reverse=True)[:5]
    top_devices_summary = [
        {
            "name": d.get("name", "Inconnu"),
            "address": d.get("address", "-"),
            "vendor": d.get("vendor", "Unknown"),
            "final_score": _safe_int(d.get("final_score", 0)),
            "alert_level": d.get("alert_level", "faible"),
            "reason_short": d.get("reason_short", "normal"),
        }
        for d in top_devices
    ]

    return {
        "stamp": stamp,
        "device_count": len(items),
        "alerts": {
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
        },
        "watch_hits": watch_hits,
        "tracker_candidates": trackers,
        "top_vendors": top_vendors,
        "top_devices": top_devices_summary,
        "extra_meta": extra_meta or {},
    }


def save_scan_manifest(manifest: dict, root: Path | None = None) -> Path:
    target_root = Path(root) if root else _ensure_manifests_dir()
    target_root.mkdir(parents=True, exist_ok=True)

    stamp = manifest.get("stamp", "unknown")
    path = target_root / f"scan_manifest_{stamp}.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_scan_manifest(path: str | Path) -> dict:
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def list_scan_manifests(root: Path | None = None) -> list[Path]:
    target_root = Path(root) if root else _ensure_manifests_dir()
    if not target_root.exists():
        return []

    items = [p for p in target_root.glob("scan_manifest_*.json") if p.is_file()]
    items.sort(key=lambda p: p.name, reverse=True)
    return items
