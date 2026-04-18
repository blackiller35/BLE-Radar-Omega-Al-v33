"""Lightweight investigation workspace profile for one device address.

The profile builder is intentionally small and explicit. It combines existing
project signals when available and degrades gracefully when some context is
missing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ble_radar.config import REPORTS_DIR
from ble_radar.history.device_scoring import compute_device_score
from ble_radar.history.triage import compute_triage
from ble_radar.incident_pack import list_incident_packs


def _normalize_address(address: Any) -> str:
    return str(address or "").strip().upper()


def _slug(address: str) -> str:
    return address.replace(":", "")


def _find_device(address: str, devices: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for dev in devices:
        if _normalize_address(dev.get("address")) == address:
            return dev
    return None


def _movement_for_address(address: str, movement: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not movement:
        return {"status": "unknown"}

    for item in movement.get("new", []):
        if _normalize_address(item.get("address")) == address:
            return {"status": "new"}

    for item in movement.get("disappeared", []):
        if _normalize_address(item.get("address")) == address:
            return {"status": "disappeared"}

    for item in movement.get("score_changes", []):
        if _normalize_address(item.get("address")) == address:
            return {
                "status": "recurring",
                "prev_score": item.get("prev_score"),
                "curr_score": item.get("curr_score"),
                "score_delta": item.get("delta"),
            }

    for item in movement.get("recurring", []):
        if _normalize_address(item.get("address")) == address:
            return {"status": "recurring"}

    return {"status": "unknown"}


def _recent_device_pack_refs(address: str, limit: int = 3) -> List[str]:
    root = REPORTS_DIR / "device_packs"
    if not root.exists():
        return []

    prefix = f"{_slug(address)}_"
    rows = [p for p in root.iterdir() if p.is_dir() and p.name.startswith(prefix)]
    rows.sort(key=lambda p: p.name, reverse=True)
    return [p.name for p in rows[:limit]]


def _recent_incident_pack_refs(limit: int = 3) -> List[str]:
    try:
        return [p.name for p in list_incident_packs()[:limit]]
    except Exception:
        return []


def build_investigation_profile(
    address: Any,
    *,
    devices: Optional[List[Dict[str, Any]]] = None,
    registry: Optional[Dict[str, Dict[str, Any]]] = None,
    watch_cases: Optional[Dict[str, Dict[str, Any]]] = None,
    movement: Optional[Dict[str, Any]] = None,
    triage_results: Optional[List[Dict[str, Any]]] = None,
    registry_scores: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """Build a compact investigation profile for one device address."""
    addr = _normalize_address(address)
    if not addr:
        raise ValueError("address must not be empty")

    current_device = _find_device(addr, devices or [])
    reg_rec = (registry or {}).get(addr, {})
    case_rec = (watch_cases or {}).get(addr)
    movement_summary = _movement_for_address(addr, movement)

    if registry_scores and addr in registry_scores:
        registry_score = int(registry_scores[addr])
    else:
        registry_score = compute_device_score(current_device or {}, reg_rec)

    triage_row = None
    for row in triage_results or []:
        if _normalize_address(row.get("address")) == addr:
            triage_row = row
            break

    if triage_row is None:
        triage_row = compute_triage(
            current_device or {},
            registry_record=reg_rec,
            case_record=case_rec,
            movement_status=movement_summary.get("status"),
            registry_score=registry_score,
        )

    identity = {
        "address": addr,
        "name": (current_device or {}).get("name", "Inconnu"),
        "vendor": (current_device or {}).get("vendor", "Unknown"),
        "profile": (current_device or {}).get("profile", "-"),
        "alert_level": (current_device or {}).get("alert_level", "-"),
        "watch_hit": bool((current_device or {}).get("watch_hit", False)),
    }

    refs = {
        "device_packs": _recent_device_pack_refs(addr),
        "incident_packs": _recent_incident_pack_refs(),
    }

    return {
        "address": addr,
        "identity": identity,
        "registry": {
            "first_seen": reg_rec.get("first_seen", "-"),
            "last_seen": reg_rec.get("last_seen", "-"),
            "seen_count": reg_rec.get("seen_count", 0),
            "session_count": reg_rec.get("session_count", 0),
            "registry_score": registry_score,
        },
        "triage": {
            "triage_score": triage_row.get("triage_score", 0),
            "triage_bucket": triage_row.get("triage_bucket", "normal"),
            "short_reason": triage_row.get("short_reason", "no signals"),
        },
        "case": {
            "status": (case_rec or {}).get("status", "none"),
            "reason": (case_rec or {}).get("reason", "-"),
            "updated_at": (case_rec or {}).get("updated_at", "-"),
        },
        "movement": movement_summary,
        "incident_refs": refs,
        "summary": {
            "headline": f"{identity['name']} | {addr}",
            "priority": f"{triage_row.get('triage_bucket', 'normal')}:{triage_row.get('triage_score', 0)}",
        },
    }
