from ble_radar.config import FULL_SCAN_SECONDS, load_runtime_config
from ble_radar.scanner import run_scan
from ble_radar.intel import build_intel, compare_device_sets
from ble_radar.state import (
    load_last_scan,
    save_last_scan,
    persist_live_observations,
)
from ble_radar.reports import save_all_reports
from ble_radar.selectors import sort_by_score


def run_engine_scan(seconds=None):
    cfg = load_runtime_config()
    if seconds is None:
        seconds = int(cfg.get("scan_timeout", FULL_SCAN_SECONDS))
    raw = run_scan(seconds)
    devices = build_intel(raw)
    return sort_by_score(devices)


def run_engine_cycle(seconds=None, persist=True, save_reports=True, save_last=True):
    cfg = load_runtime_config()
    if seconds is None:
        seconds = int(cfg.get("scan_timeout", FULL_SCAN_SECONDS))
    devices = run_engine_scan(seconds)
    previous = load_last_scan()
    comparison = compare_device_sets(devices, previous)

    paths = None
    if persist:
        persist_live_observations(devices)

    if save_reports:
        paths = save_all_reports(devices)

    if save_last:
        save_last_scan(devices)

    return {
        "devices": devices,
        "previous": previous,
        "comparison": comparison,
        "paths": paths,
    }


def summarize_engine_result(result: dict) -> dict:
    devices = result.get("devices", [])
    comparison = result.get("comparison", {})

    critical = [d for d in devices if d.get("alert_level") == "critique"]
    high = [d for d in devices if d.get("alert_level") == "élevé"]
    medium = [d for d in devices if d.get("alert_level") == "moyen"]
    trackers = [
        d for d in devices
        if d.get("profile") == "tracker_probable"
        or d.get("possible_suivi")
        or d.get("watch_hit")
    ]

    return {
        "total": len(devices),
        "critical": len(critical),
        "high": len(high),
        "medium": len(medium),
        "trackers": len(trackers),
        "added": len(comparison.get("added", [])),
        "removed": len(comparison.get("removed", [])),
        "common": len(comparison.get("common", [])),
    }
