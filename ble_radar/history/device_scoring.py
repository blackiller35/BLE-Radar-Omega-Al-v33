"""
Simple, explainable device score based purely on registry persistence data.

Score components (total 0–100):
  seen_score    — up to 40 pts.  min(seen_count, 20) * 2
  session_score — up to 40 pts.  min(session_count, 10) * 4
  recency_score — up to 20 pts.  20 if seen within 24 h, 10 if within 7 days, 0 otherwise
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def compute_device_score(
    device: Dict[str, Any],
    registry_record: Dict[str, Any] | None,
    _now: datetime | None = None,
) -> int:
    """Return a persistence-based score in [0, 100] for *device* using *registry_record*.

    Parameters
    ----------
    device:
        The current scan device dict (used for address context only; score is
        purely registry-driven so the dashboard stays self-consistent).
    registry_record:
        The matching entry from the local device registry, or None / {}.
    _now:
        Override "now" for deterministic testing.
    """
    rec = registry_record or {}
    now = _now if _now is not None else datetime.now()

    seen_count = max(0, _safe_int(rec.get("seen_count", 0)))
    session_count = max(0, _safe_int(rec.get("session_count", 0)))
    last_seen_str = str(rec.get("last_seen") or "")

    seen_score = min(seen_count, 20) * 2        # 0–40
    session_score = min(session_count, 10) * 4   # 0–40

    recency_score = 0
    if last_seen_str and last_seen_str != "-":
        try:
            last_seen_dt = datetime.strptime(last_seen_str, "%Y-%m-%d %H:%M:%S")
            age_hours = (now - last_seen_dt).total_seconds() / 3600
            if age_hours <= 24:
                recency_score = 20
            elif age_hours <= 168:   # 7 days
                recency_score = 10
        except ValueError:
            pass

    return min(seen_score + session_score + recency_score, 100)
