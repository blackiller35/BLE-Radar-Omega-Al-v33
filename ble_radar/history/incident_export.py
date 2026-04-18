"""Lightweight incident pack export — address-centric, no case-ID required.

Output layout for address AA:BB:CC:DD:EE:FF at stamp 2026-04-18_12-00-00::

    reports/device_packs/
        AABBCCDDEEFF_2026-04-18_12-00-00/
            pack.json
            summary.md

``build_device_pack`` is the sole public entry-point.  All arguments except
*address* are optional; the function degrades gracefully when context data is
missing.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ble_radar.config import REPORTS_DIR
from ble_radar.history.device_scoring import compute_device_score

DEVICE_PACKS_DIR = REPORTS_DIR / "device_packs"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _normalize_address(address: Any) -> str:
    return str(address or "").strip().upper()


def _slug(address: str) -> str:
    """Convert 'AA:BB:CC:DD:EE:FF' → 'AABBCCDDEEFF' for folder names."""
    return address.replace(":", "")


def _ensure_packs_dir() -> Path:
    DEVICE_PACKS_DIR.mkdir(parents=True, exist_ok=True)
    return DEVICE_PACKS_DIR


def _find_device(address: str, devices: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return first device whose address matches (case-insensitive)."""
    for d in devices:
        if _normalize_address(d.get("address")) == address:
            return d
    return None


def _movement_for_address(
    address: str,
    movement: Optional[Dict[str, Any]],
) -> Dict[str, str]:
    """Extract per-device movement status and score-change for *address*."""
    if not movement:
        return {"status": "unknown"}

    for d in movement.get("new", []):
        if _normalize_address(d.get("address")) == address:
            return {"status": "new"}

    for d in movement.get("disappeared", []):
        if _normalize_address(d.get("address")) == address:
            return {"status": "disappeared"}

    # score_changes checked before generic recurring — it is a subset of recurring
    # but carries extra delta information we want to surface.
    for sc in movement.get("score_changes", []):
        if _normalize_address(sc.get("address")) == address:
            return {
                "status": "recurring",
                "prev_score": sc.get("prev_score"),
                "curr_score": sc.get("curr_score"),
                "score_delta": sc.get("delta"),
            }

    for d in movement.get("recurring", []):
        if _normalize_address(d.get("address")) == address:
            return {"status": "recurring"}

    return {"status": "unknown"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_device_pack(
    address: Any,
    *,
    current_devices: Optional[List[Dict[str, Any]]] = None,
    registry: Optional[Dict[str, Any]] = None,
    watch_cases: Optional[Dict[str, Any]] = None,
    movement: Optional[Dict[str, Any]] = None,
    stamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a JSON + Markdown incident pack for *address*.

    Parameters
    ----------
    address:
        Device MAC address (case-insensitive).
    current_devices:
        Full device list from the current scan.  Used to pull identity fields.
    registry:
        Full registry dict from ``load_registry()``.
    watch_cases:
        Full cases dict from ``load_cases()``.
    movement:
        ``build_session_movement()`` output for the current session.
    stamp:
        Override the timestamp string (useful in tests).

    Returns
    -------
    dict with keys: ``pack_dir``, ``json_path``, ``md_path``, ``pack``.
    """
    addr = _normalize_address(address)
    if not addr:
        raise ValueError("address must not be empty")

    ts = stamp or _now_stamp()
    pack_dir = _ensure_packs_dir() / f"{_slug(addr)}_{ts}"
    pack_dir.mkdir(parents=True, exist_ok=True)

    # --- identity -----------------------------------------------------------
    device = _find_device(addr, current_devices or {})
    identity: Dict[str, Any] = {
        "address": addr,
        "name": device.get("name", "Inconnu") if device else "Inconnu",
        "vendor": device.get("vendor", "Unknown") if device else "Unknown",
        "profile": device.get("profile", "-") if device else "-",
        "rssi": device.get("rssi", None) if device else None,
        "alert_level": device.get("alert_level", "-") if device else "-",
        "final_score": device.get("final_score", 0) if device else 0,
        "flags": device.get("flags", []) if device else [],
    }

    # --- registry -----------------------------------------------------------
    reg_record = (registry or {}).get(addr, {})
    registry_fields: Dict[str, Any] = {
        "first_seen": reg_record.get("first_seen", "-"),
        "last_seen": reg_record.get("last_seen", "-"),
        "seen_count": reg_record.get("seen_count", 0),
        "session_count": reg_record.get("session_count", 0),
    }

    # --- score --------------------------------------------------------------
    device_score = compute_device_score(device or {}, reg_record)

    # --- watch/case ---------------------------------------------------------
    case_record = (watch_cases or {}).get(addr)
    case_fields: Optional[Dict[str, Any]] = (
        {
            "reason": case_record.get("reason", "-"),
            "status": case_record.get("status", "watch"),
            "created_at": case_record.get("created_at", "-"),
            "updated_at": case_record.get("updated_at", "-"),
        }
        if case_record
        else None
    )

    # --- movement -----------------------------------------------------------
    movement_summary = _movement_for_address(addr, movement)

    # --- assemble pack ------------------------------------------------------
    pack: Dict[str, Any] = {
        "address": addr,
        "pack_stamp": ts,
        "identity": identity,
        "registry": registry_fields,
        "device_score": device_score,
        "case": case_fields,
        "movement": movement_summary,
    }

    # --- write JSON ---------------------------------------------------------
    json_path = pack_dir / "pack.json"
    json_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- write Markdown summary ---------------------------------------------
    md_path = pack_dir / "summary.md"
    md_path.write_text(_render_markdown(pack), encoding="utf-8")

    return {
        "pack_dir": pack_dir,
        "json_path": json_path,
        "md_path": md_path,
        "pack": pack,
    }


def _render_markdown(pack: Dict[str, Any]) -> str:
    addr = pack["address"]
    ts = pack["pack_stamp"]
    identity = pack["identity"]
    registry = pack["registry"]
    score = pack["device_score"]
    case = pack.get("case")
    movement = pack.get("movement", {})

    lines: List[str] = [
        f"# Incident Pack — {addr}",
        f"**Generated:** {ts}",
        "",
        "## Identity",
        f"- **Name:** {identity.get('name', 'Inconnu')}",
        f"- **Address:** {addr}",
        f"- **Vendor:** {identity.get('vendor', 'Unknown')}",
        f"- **Profile:** {identity.get('profile', '-')}",
        f"- **RSSI:** {identity.get('rssi', 'n/a')}",
        f"- **Alert level:** {identity.get('alert_level', '-')}",
        f"- **Final score:** {identity.get('final_score', 0)}",
    ]

    flags = identity.get("flags", [])
    if flags:
        lines.append(f"- **Flags:** {', '.join(str(f) for f in flags)}")

    lines += [
        "",
        "## Registry",
        f"- **First seen:** {registry.get('first_seen', '-')}",
        f"- **Last seen:** {registry.get('last_seen', '-')}",
        f"- **Seen count:** {registry.get('seen_count', 0)}",
        f"- **Session count:** {registry.get('session_count', 0)}",
        "",
        "## Persistence Score",
        f"- **Score:** {score} / 100",
        "",
        "## Watch / Case",
    ]

    if case:
        lines += [
            f"- **Status:** {case.get('status', 'watch')}",
            f"- **Reason:** {case.get('reason', '-')}",
            f"- **Created:** {case.get('created_at', '-')}",
            f"- **Updated:** {case.get('updated_at', '-')}",
        ]
    else:
        lines.append("- No active watch/case record.")

    lines += [
        "",
        "## Session Movement",
        f"- **Status:** {movement.get('status', 'unknown')}",
    ]

    if "prev_score" in movement:
        lines.append(
            f"- **Score change:** {movement['prev_score']} → {movement['curr_score']}"
            f" (delta={movement['score_delta']})"
        )

    return "\n".join(lines) + "\n"
