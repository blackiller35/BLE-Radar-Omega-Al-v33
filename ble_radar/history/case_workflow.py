"""Lightweight operator case workflow system.

Storage layout (two JSON files under HISTORY_DIR):
  history/cases.json        — case records (built by ble_radar.history.cases)
  history/case_events.json  — append-only event log

Status lifecycle:
  new → watch → review → investigating → resolved | ignored

Next-action suggestion table:
  new          → "Assign to operator or escalate to review"
  watch        → "Monitor for additional signals"
  review       → "Triage and decide: investigate or ignore"
  investigating → "Record findings and close when done"
  resolved     → "Archive or re-open if signals recur"
  ignored      → "Re-open if signals recur"
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ble_radar.config import HISTORY_DIR
from ble_radar.history.cases import load_cases, save_cases
from ble_radar.state import load_json, save_json

CASE_EVENTS_FILE = HISTORY_DIR / "case_events.json"

# Valid statuses — ordered for display convenience
VALID_STATUSES = ("new", "watch", "review", "investigating", "resolved", "ignored")

OPEN_STATUSES = ("new", "watch", "review", "investigating")
NEEDS_ACTION_STATUSES = ("new", "review", "investigating")

NEXT_ACTION: Dict[str, str] = {
    "new":           "Assign to operator or escalate to review",
    "watch":         "Monitor for additional signals",
    "review":        "Triage and decide: investigate or ignore",
    "investigating": "Record findings and close when done",
    "resolved":      "Archive or re-open if signals recur",
    "ignored":       "Re-open if signals recur",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _normalize_address(address: Any) -> str:
    return str(address or "").strip().upper()


def _load_events() -> List[Dict[str, Any]]:
    data = load_json(CASE_EVENTS_FILE, [])
    return data if isinstance(data, list) else []


def _save_events(events: List[Dict[str, Any]]) -> None:
    save_json(CASE_EVENTS_FILE, events)


def _append_event(address: str, action: str, detail: str = "") -> Dict[str, Any]:
    event: Dict[str, Any] = {
        "address": address,
        "action": action,
        "detail": detail,
        "timestamp": _now(),
    }
    events = _load_events()
    events.append(event)
    _save_events(events)
    return event


# ---------------------------------------------------------------------------
# Public API — event log
# ---------------------------------------------------------------------------

def log_event(address: Any, action: str, detail: str = "") -> Dict[str, Any]:
    """Append one event to the case event log and return it.

    Parameters
    ----------
    address:
        Device MAC address; normalised to uppercase.
    action:
        Short action label, e.g. ``"case_created"``, ``"status_changed"``,
        ``"note_added"``, ``"incident_pack_generated"``, ``"case_resolved"``.
    detail:
        Optional human-readable detail string.
    """
    addr = _normalize_address(address)
    if not addr:
        raise ValueError("address must not be empty")
    return _append_event(addr, str(action), str(detail))


def load_events(address: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Return all events, optionally filtered by *address*."""
    events = _load_events()
    if address is None:
        return events
    addr = _normalize_address(address)
    return [e for e in events if e.get("address") == addr]


# ---------------------------------------------------------------------------
# Public API — status transitions
# ---------------------------------------------------------------------------

def transition_case(address: Any, new_status: str, note: str = "") -> Dict[str, Any]:
    """Change the status of a case and log the transition.

    Creates the case record with status ``"new"`` first if it does not yet
    exist.  Raises ``ValueError`` for invalid statuses.
    """
    addr = _normalize_address(address)
    if not addr:
        raise ValueError("address must not be empty")
    ns = str(new_status).strip().lower()
    if ns not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{new_status}'. Must be one of: {VALID_STATUSES}")

    cases = load_cases()
    existing = cases.get(addr, {})
    prev_status = existing.get("status", "new")
    now = _now()

    record: Dict[str, Any] = {
        "address": addr,
        "reason": existing.get("reason", ""),
        "status": ns,
        "created_at": existing.get("created_at", now),
        "updated_at": now,
    }
    cases[addr] = record
    save_cases(cases)

    detail = f"{prev_status} → {ns}"
    if note:
        detail += f" | note: {note}"
    if ns == "resolved":
        log_event(addr, "case_resolved", detail)
    else:
        log_event(addr, "status_changed", detail)

    return record


# ---------------------------------------------------------------------------
# Public API — case views for the dashboard
# ---------------------------------------------------------------------------

def case_workflow_summary(cases: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a compact workflow summary from the case store.

    Returns
    -------
    dict with keys:
        open          — list of open case records
        investigating — subset of open cases with status "investigating"
        needs_action  — cases with status in NEEDS_ACTION_STATUSES
        resolved      — resolved cases (most recent 5)
        total         — int count of all cases
    """
    if cases is None:
        cases = load_cases()

    all_records = list(cases.values())
    # sort by updated_at descending
    all_records.sort(key=lambda r: r.get("updated_at", ""), reverse=True)

    open_cases = [r for r in all_records if r.get("status") in OPEN_STATUSES]
    investigating = [r for r in all_records if r.get("status") == "investigating"]
    needs_action = [r for r in all_records if r.get("status") in NEEDS_ACTION_STATUSES]
    resolved = [r for r in all_records if r.get("status") == "resolved"][:5]

    return {
        "open": open_cases,
        "investigating": investigating,
        "needs_action": needs_action,
        "resolved": resolved,
        "total": len(all_records),
    }


def next_action(case_record: Dict[str, Any]) -> str:
    """Return a suggested next action string for *case_record*."""
    status = str(case_record.get("status", "new")).strip().lower()
    return NEXT_ACTION.get(status, "No action defined.")
