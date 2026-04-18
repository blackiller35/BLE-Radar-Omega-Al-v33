"""Lightweight operator timeline builder for a single device/case.

The timeline merges available signals into one chronological event list:
- registry updates
- case workflow events
- session movement snapshot
- triage snapshot/change candidates
- incident pack generation references

No heavy orchestration, no background jobs, no side effects.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ble_radar.config import REPORTS_DIR
from ble_radar.history.case_workflow import load_events


def _normalize_address(address: Any) -> str:
    return str(address or "").strip().upper()


def _slug(address: str) -> str:
    return address.replace(":", "")


def _parse_ts(value: Any) -> Optional[datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d_%H-%M-%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _fmt_ts(value: Any) -> str:
    return str(value or "").strip() or "n/a"


def _sort_key(event: Dict[str, Any]) -> tuple:
    dt = _parse_ts(event.get("timestamp"))
    if dt is None:
        return (1, datetime.min)
    return (0, dt)


def _registry_events(addr: str, registry: Optional[Dict[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    rec = (registry or {}).get(addr, {})
    if not rec:
        return []

    out: List[Dict[str, Any]] = []
    first_seen = rec.get("first_seen")
    last_seen = rec.get("last_seen")
    seen_count = rec.get("seen_count", 0)
    session_count = rec.get("session_count", 0)

    if first_seen:
        out.append({
            "timestamp": str(first_seen),
            "source": "registry",
            "action": "first_seen",
            "summary": f"First seen in registry (seen={seen_count}, sessions={session_count})",
        })

    if last_seen and str(last_seen) != str(first_seen):
        out.append({
            "timestamp": str(last_seen),
            "source": "registry",
            "action": "last_seen",
            "summary": f"Last seen updated (seen={seen_count}, sessions={session_count})",
        })

    return out


def _case_workflow_events(addr: str) -> List[Dict[str, Any]]:
    rows = load_events(addr)
    out: List[Dict[str, Any]] = []
    for row in rows:
        action = str(row.get("action", "event"))
        detail = str(row.get("detail", "")).strip()
        summary = action.replace("_", " ").strip().capitalize()
        if detail:
            summary += f": {detail}"
        out.append({
            "timestamp": str(row.get("timestamp", "")),
            "source": "case_workflow",
            "action": action,
            "summary": summary,
        })
    return out


def _movement_event(addr: str, movement: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not movement:
        return []

    for row in movement.get("new", []):
        if _normalize_address(row.get("address")) == addr:
            return [{
                "timestamp": "",
                "source": "session_movement",
                "action": "new",
                "summary": "Appears as new in current session",
            }]

    for row in movement.get("disappeared", []):
        if _normalize_address(row.get("address")) == addr:
            return [{
                "timestamp": "",
                "source": "session_movement",
                "action": "disappeared",
                "summary": "Marked as disappeared in current session",
            }]

    for row in movement.get("score_changes", []):
        if _normalize_address(row.get("address")) == addr:
            return [{
                "timestamp": "",
                "source": "session_movement",
                "action": "score_change",
                "summary": (
                    f"Score changed {row.get('prev_score', '?')} -> "
                    f"{row.get('curr_score', '?')} (delta={row.get('delta', '?')})"
                ),
            }]

    for row in movement.get("recurring", []):
        if _normalize_address(row.get("address")) == addr:
            return [{
                "timestamp": "",
                "source": "session_movement",
                "action": "recurring",
                "summary": "Seen as recurring in current session",
            }]

    return []


def _triage_events(addr: str, triage_results: Optional[List[Dict[str, Any]]], movement: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    row = None
    for item in triage_results or []:
        if _normalize_address(item.get("address")) == addr:
            row = item
            break

    if not row:
        return out

    score = row.get("triage_score", 0)
    bucket = row.get("triage_bucket", "normal")
    reason = row.get("short_reason", "no signals")

    out.append({
        "timestamp": "",
        "source": "triage",
        "action": "snapshot",
        "summary": f"Triage snapshot: {bucket.upper()} score={score} ({reason})",
    })

    # Change hint when movement score delta is available.
    for sc in (movement or {}).get("score_changes", []):
        if _normalize_address(sc.get("address")) == addr:
            delta = sc.get("delta", 0)
            out.append({
                "timestamp": "",
                "source": "triage",
                "action": "change_hint",
                "summary": f"Triage change hint from score delta={delta}",
            })
            break

    return out


def _incident_pack_events(addr: str, root: Optional[Path] = None) -> List[Dict[str, Any]]:
    base = root or (REPORTS_DIR / "device_packs")
    if not base.exists():
        return []

    prefix = f"{_slug(addr)}_"
    out: List[Dict[str, Any]] = []
    for p in base.iterdir():
        if not p.is_dir() or not p.name.startswith(prefix):
            continue
        stamp = p.name[len(prefix):]
        out.append({
            "timestamp": stamp,
            "source": "incident_pack",
            "action": "generated",
            "summary": f"Incident pack generated: {p.name}",
        })

    return out


def build_operator_timeline(
    address: Any,
    *,
    registry: Optional[Dict[str, Dict[str, Any]]] = None,
    movement: Optional[Dict[str, Any]] = None,
    triage_results: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build a compact unified timeline for one device/case address.

    Returns a dict:
        {
          "address": "AA:..",
          "events": [ ... chronological events ... ],
          "compact": ["2026-... | registry | ...", ...],
        }

    Events are sorted in chronological order when timestamps are available.
    Events without timestamp are appended after dated events.
    """
    addr = _normalize_address(address)
    if not addr:
        raise ValueError("address must not be empty")

    events: List[Dict[str, Any]] = []
    events.extend(_registry_events(addr, registry))
    events.extend(_case_workflow_events(addr))
    events.extend(_movement_event(addr, movement))
    events.extend(_triage_events(addr, triage_results, movement))
    events.extend(_incident_pack_events(addr))

    events.sort(key=_sort_key)

    compact = [
        f"{_fmt_ts(e.get('timestamp'))} | {e.get('source', '?')} | {e.get('summary', '')}"
        for e in events
    ]

    return {
        "address": addr,
        "events": events,
        "compact": compact,
    }


def recent_timeline_events(timeline: Dict[str, Any], limit: int = 8) -> List[Dict[str, Any]]:
    """Return recent events in reverse chronological order (best effort)."""
    events = list(timeline.get("events", []))
    events.sort(key=_sort_key, reverse=True)
    return events[: max(0, int(limit))]
