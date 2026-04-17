from __future__ import annotations

from pathlib import Path

from ble_radar.scan_manifest import load_scan_manifest, list_scan_manifests
from ble_radar.session_catalog import session_row_from_manifest


def _delta(current: int, previous: int) -> int:
    return int(current) - int(previous)


def compare_session_rows(previous: dict, current: dict) -> dict:
    return {
        "previous_stamp": str(previous.get("stamp", "unknown")),
        "current_stamp": str(current.get("stamp", "unknown")),
        "device_count_delta": _delta(current.get("device_count", 0), previous.get("device_count", 0)),
        "critical_delta": _delta(current.get("critical", 0), previous.get("critical", 0)),
        "high_delta": _delta(current.get("high", 0), previous.get("high", 0)),
        "medium_delta": _delta(current.get("medium", 0), previous.get("medium", 0)),
        "low_delta": _delta(current.get("low", 0), previous.get("low", 0)),
        "watch_hits_delta": _delta(current.get("watch_hits", 0), previous.get("watch_hits", 0)),
        "tracker_candidates_delta": _delta(current.get("tracker_candidates", 0), previous.get("tracker_candidates", 0)),
        "previous_top_vendor": str(previous.get("top_vendor", "Unknown")),
        "current_top_vendor": str(current.get("top_vendor", "Unknown")),
        "previous_top_device": str(previous.get("top_device_name", "Inconnu")),
        "current_top_device": str(current.get("top_device_name", "Inconnu")),
    }


def compare_manifest_dicts(previous_manifest: dict, current_manifest: dict) -> dict:
    previous_row = session_row_from_manifest(previous_manifest)
    current_row = session_row_from_manifest(current_manifest)
    return compare_session_rows(previous_row, current_row)


def latest_session_diff(root: Path | None = None) -> dict:
    paths = list_scan_manifests(root)
    if len(paths) < 2:
        return {
            "previous_stamp": "unknown",
            "current_stamp": "unknown",
            "device_count_delta": 0,
            "critical_delta": 0,
            "high_delta": 0,
            "medium_delta": 0,
            "low_delta": 0,
            "watch_hits_delta": 0,
            "tracker_candidates_delta": 0,
            "previous_top_vendor": "Unknown",
            "current_top_vendor": "Unknown",
            "previous_top_device": "Inconnu",
            "current_top_device": "Inconnu",
            "has_diff": False,
        }

    current_manifest = load_scan_manifest(paths[0])
    previous_manifest = load_scan_manifest(paths[1])
    diff = compare_manifest_dicts(previous_manifest, current_manifest)
    diff["has_diff"] = True
    return diff


def summary_lines(diff: dict) -> list[str]:
    if not diff.get("has_diff", True):
        return [
            "BLE Radar Omega AI - Session Diff",
            "No comparable sessions available.",
        ]

    return [
        "BLE Radar Omega AI - Session Diff",
        f"Previous: {diff['previous_stamp']}",
        f"Current: {diff['current_stamp']}",
        f"Device delta: {diff['device_count_delta']}",
        f"Critical delta: {diff['critical_delta']}",
        f"High delta: {diff['high_delta']}",
        f"Medium delta: {diff['medium_delta']}",
        f"Low delta: {diff['low_delta']}",
        f"Watch hits delta: {diff['watch_hits_delta']}",
        f"Tracker candidates delta: {diff['tracker_candidates_delta']}",
        f"Top vendor: {diff['previous_top_vendor']} -> {diff['current_top_vendor']}",
        f"Top device: {diff['previous_top_device']} -> {diff['current_top_device']}",
    ]
