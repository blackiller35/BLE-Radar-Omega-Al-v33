"""Lightweight watch/case tracking — persists to history/cases.json.

Each entry is keyed by normalised MAC address:
  {
    "AA:BB:CC:DD:EE:FF": {
      "address":    "AA:BB:CC:DD:EE:FF",
      "reason":     "tracker candidate",
      "status":     "watch",
      "created_at": "2026-04-18 12:00:00",
      "updated_at": "2026-04-18 12:00:00"
    },
    ...
  }
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from ble_radar.config import HISTORY_DIR
from ble_radar.state import load_json, save_json

CASES_FILE = HISTORY_DIR / "cases.json"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _normalize_address(address: Any) -> str:
    return str(address or "").strip().upper()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_cases() -> Dict[str, Dict[str, Any]]:
    """Return the full cases dict keyed by normalised address."""
    data = load_json(CASES_FILE, {})
    if not isinstance(data, dict):
        return {}
    return data


def save_cases(cases: Dict[str, Dict[str, Any]]) -> None:
    """Persist the cases dict to disk."""
    save_json(CASES_FILE, cases)


def upsert_case(
    address: Any,
    reason: str,
    status: str = "watch",
) -> Dict[str, Any]:
    """Create or update a watch/case entry for *address*.

    - If the address is new, ``created_at`` is set to now.
    - If it already exists, ``created_at`` is preserved.
    - ``updated_at`` is always refreshed.
    """
    addr = _normalize_address(address)
    if not addr:
        raise ValueError("address must not be empty")

    cases = load_cases()
    now = _now()

    existing = cases.get(addr, {})
    record: Dict[str, Any] = {
        "address": addr,
        "reason": str(reason),
        "status": str(status),
        "created_at": existing.get("created_at", now),
        "updated_at": now,
    }

    cases[addr] = record
    save_cases(cases)
    return record


def get_case(address: Any) -> Optional[Dict[str, Any]]:
    """Return the case record for *address*, or ``None`` if not found."""
    addr = _normalize_address(address)
    return load_cases().get(addr)
