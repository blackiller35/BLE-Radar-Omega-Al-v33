"""Lightweight operator session journal / shift continuity system."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _norm(value: Any) -> str:
    return str(value or "").strip().upper()


def _slug(value: Any) -> str:
    return str(value or "unknown").replace(":", "").replace("/", "-").replace(" ", "_").lower()


def _parse_dt(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d_%H-%M-%S",
        "%Y-%m-%d_%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    )
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _fmt(dt: Optional[datetime], fallback: str) -> str:
    if not dt:
        return str(fallback)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def build_operator_session_journal(
    *,
    queue_items: Optional[List[Dict[str, Any]]] = None,
    campaigns: Optional[List[Dict[str, Any]]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
    outcomes: Optional[List[Dict[str, Any]]] = None,
    readiness_profiles: Optional[List[Dict[str, Any]]] = None,
    evidence_packs: Optional[List[Dict[str, Any]]] = None,
    queue_health_snapshot: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build one compact operator session journal from existing operator signals."""
    queue_rows = list(queue_items or [])
    campaign_rows = list(campaigns or [])
    alert_rows = list(alerts or [])
    outcome_rows = list(outcomes or [])
    readiness_rows = list(readiness_profiles or [])
    pack_rows = list(evidence_packs or [])
    health = queue_health_snapshot if isinstance(queue_health_snapshot, dict) else {}

    now_str = str(generated_at or _now())
    now_dt = _parse_dt(now_str) or datetime.now()

    touched_ids = set()
    started_candidates: List[datetime] = []
    ended_candidates: List[datetime] = []

    for row in queue_rows:
        touched_ids.add(f"{str(row.get('scope_type', '-'))}:{str(row.get('scope_id', '-'))}")
        started_candidates.append(_parse_dt(row.get("created_at")) or now_dt)
        ended_candidates.append(_parse_dt(row.get("updated_at")) or now_dt)

    for row in outcome_rows:
        touched_ids.add(f"{str(row.get('scope_type', '-'))}:{str(row.get('scope_id', '-'))}")
        ended_candidates.append(_parse_dt(row.get("created_at")) or now_dt)

    for row in readiness_rows:
        touched_ids.add(f"{str(row.get('scope_type', '-'))}:{str(row.get('scope_id', '-'))}")
        ended_candidates.append(_parse_dt(row.get("created_at")) or now_dt)

    for row in pack_rows:
        touched_ids.add(f"{str(row.get('scope_type', '-'))}:{str(row.get('scope_id', '-'))}")
        ended_candidates.append(_parse_dt(row.get("generated_at")) or now_dt)

    started_at = _fmt(min(started_candidates) if started_candidates else now_dt, now_str)
    ended_at = _fmt(max(ended_candidates) if ended_candidates else now_dt, now_str)

    campaigns_updated = len([
        c for c in campaign_rows
        if str(c.get("status", "")).lower() in {"new", "expanding", "stable", "recurring", "cooling_down", "closed"}
    ])

    alerts_reviewed = len(alert_rows)
    outcomes_recorded = len(outcome_rows)

    readiness_changes = len([
        r for r in readiness_rows
        if str(r.get("readiness_state", "")).lower() in {
            "ready_for_review",
            "ready_for_handoff",
            "ready_for_archive",
            "needs_more_data",
            "not_ready",
        }
    ])

    carry_over = [
        row for row in queue_rows
        if str(row.get("queue_state", "")).lower() in {"blocked", "waiting", "in_review"}
    ]
    stale_count = len(health.get("stale_items", []) or [])

    handoff_summary = (
        f"Touched={len(touched_ids)} | carry_over={len(carry_over)} | outcomes={outcomes_recorded} "
        f"| readiness_changes={readiness_changes} | queue_pressure={str(health.get('queue_pressure', 'low'))}"
    )

    next_shift_priorities: List[str] = []
    if carry_over:
        next_shift_priorities.append(f"Carry-over queue items: {len(carry_over)}")
    if stale_count > 0:
        next_shift_priorities.append(f"Resolve stale queue items: {stale_count}")
    if alerts_reviewed > 0:
        next_shift_priorities.append(f"Re-check reviewed alerts: {alerts_reviewed}")
    if readiness_changes > 0:
        next_shift_priorities.append(f"Validate readiness transitions: {readiness_changes}")
    if campaigns_updated > 0:
        next_shift_priorities.append(f"Track campaign updates: {campaigns_updated}")
    if not next_shift_priorities:
        next_shift_priorities.append("Maintain routine operator cadence")

    return {
        "session_id": f"opsession-{_slug(started_at)}-{_slug(ended_at)}",
        "started_at": started_at,
        "ended_at": ended_at,
        "items_touched": len(touched_ids),
        "campaigns_updated": campaigns_updated,
        "alerts_reviewed": alerts_reviewed,
        "outcomes_recorded": outcomes_recorded,
        "readiness_changes": readiness_changes,
        "handoff_summary": handoff_summary,
        "next_shift_priorities": next_shift_priorities[:8],
    }


def summarize_operator_session_journal(
    session_journal: Optional[Dict[str, Any]] = None,
    *,
    queue_items: Optional[List[Dict[str, Any]]] = None,
    outcomes: Optional[List[Dict[str, Any]]] = None,
    readiness_profiles: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build compact dashboard sections for session continuity panel."""
    journal = dict(session_journal or {})
    queue_rows = list(queue_items or [])
    outcome_rows = list(outcomes or [])
    readiness_rows = list(readiness_profiles or [])

    shift_activity = {
        "items_touched": _safe_int(journal.get("items_touched"), 0),
        "campaigns_updated": _safe_int(journal.get("campaigns_updated"), 0),
        "alerts_reviewed": _safe_int(journal.get("alerts_reviewed"), 0),
        "outcomes_recorded": _safe_int(journal.get("outcomes_recorded"), 0),
        "readiness_changes": _safe_int(journal.get("readiness_changes"), 0),
    }

    carry_over_items = [
        row for row in queue_rows
        if str(row.get("queue_state", "")).lower() in {"blocked", "waiting", "in_review"}
    ][:10]

    handoff_ready = [
        row for row in readiness_rows
        if str(row.get("readiness_state", "")).lower() in {"ready_for_handoff", "ready_for_archive"}
    ][:8]

    outcome_handoffs = [
        row for row in outcome_rows
        if str(row.get("outcome_label", "")).lower() in {"resolved_cleanly", "stabilized"}
    ][:8]

    recent_handoffs = []
    for row in handoff_ready:
        recent_handoffs.append(
            {
                "scope_type": str(row.get("scope_type", "-")),
                "scope_id": str(row.get("scope_id", "-")),
                "reason": str(row.get("readiness_state", "ready_for_handoff")),
            }
        )
    for row in outcome_handoffs:
        recent_handoffs.append(
            {
                "scope_type": str(row.get("scope_type", "-")),
                "scope_id": str(row.get("scope_id", "-")),
                "reason": str(row.get("outcome_label", "resolved_cleanly")),
            }
        )

    return {
        "current_session_journal": journal,
        "shift_activity": shift_activity,
        "carry_over_items": carry_over_items,
        "next_shift_priorities": list(journal.get("next_shift_priorities", []) or [])[:8],
        "recent_handoffs": recent_handoffs[:10],
    }
