from __future__ import annotations

from pathlib import Path

from ble_radar.scan_manifest import list_scan_manifests, load_scan_manifest


def _coerce_pair(item):
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        return str(item[0]), int(item[1])
    return "Unknown", 0


def session_row_from_manifest(manifest: dict) -> dict:
    alerts = manifest.get("alerts", {}) or {}
    top_vendors = manifest.get("top_vendors", []) or []
    top_devices = manifest.get("top_devices", []) or []

    vendor_name, vendor_count = _coerce_pair(top_vendors[0]) if top_vendors else ("Unknown", 0)
    top_device = top_devices[0] if top_devices else {}

    return {
        "stamp": str(manifest.get("stamp", "unknown")),
        "device_count": int(manifest.get("device_count", 0) or 0),
        "critical": int(alerts.get("critical", 0) or 0),
        "high": int(alerts.get("high", 0) or 0),
        "medium": int(alerts.get("medium", 0) or 0),
        "low": int(alerts.get("low", 0) or 0),
        "watch_hits": int(manifest.get("watch_hits", 0) or 0),
        "tracker_candidates": int(manifest.get("tracker_candidates", 0) or 0),
        "top_vendor": vendor_name,
        "top_vendor_count": vendor_count,
        "top_device_name": str(top_device.get("name", "Inconnu")),
        "top_device_score": int(top_device.get("final_score", 0) or 0),
        "top_device_alert": str(top_device.get("alert_level", "faible")),
    }


def build_session_catalog(root: Path | None = None, limit: int | None = None) -> list[dict]:
    paths = list_scan_manifests(root)
    if limit is not None:
        paths = paths[:limit]

    rows = []
    for path in paths:
        try:
            manifest = load_scan_manifest(path)
            rows.append(session_row_from_manifest(manifest))
        except Exception:
            continue

    return rows


def latest_session_overview(root: Path | None = None) -> dict:
    rows = build_session_catalog(root=root, limit=1)
    if rows:
        return rows[0]

    return {
        "stamp": "unknown",
        "device_count": 0,
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "watch_hits": 0,
        "tracker_candidates": 0,
        "top_vendor": "Unknown",
        "top_vendor_count": 0,
        "top_device_name": "Inconnu",
        "top_device_score": 0,
        "top_device_alert": "faible",
    }


def summary_lines(rows: list[dict]) -> list[str]:
    lines = ["BLE Radar Omega AI - Session Catalog"]
    if not rows:
        lines.append("No sessions available.")
        return lines

    lines.append(f"Sessions: {len(rows)}")
    for row in rows:
        lines.append(
            f"- {row['stamp']} | devices={row['device_count']} | "
            f"critical={row['critical']} | high={row['high']} | medium={row['medium']} | "
            f"watch_hits={row['watch_hits']} | trackers={row['tracker_candidates']} | "
            f"top_vendor={row['top_vendor']} | top_device={row['top_device_name']} ({row['top_device_score']})"
        )
    return lines
