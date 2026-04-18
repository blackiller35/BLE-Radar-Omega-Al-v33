"""Lightweight operator briefing / shift handoff builder.

Builds a compact summary from already-computed operator signals.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _pick_top_priorities(triage_results: Optional[List[Dict[str, Any]]], limit: int = 5) -> List[Dict[str, Any]]:
    rows = list(triage_results or [])
    rows.sort(key=lambda r: _safe_int(r.get("triage_score", 0), 0), reverse=True)
    out = []
    for row in rows[: max(0, int(limit))]:
        out.append({
            "address": str(row.get("address", "")).strip().upper(),
            "name": str(row.get("name", "Inconnu")),
            "triage_bucket": str(row.get("triage_bucket", "normal")),
            "triage_score": _safe_int(row.get("triage_score", 0), 0),
            "reason": str(row.get("short_reason", "no signals")),
        })
    return out


def _recent_auto_actions(
    rule_summary: Optional[Dict[str, Any]],
    rule_log_events: Optional[List[Dict[str, Any]]],
    limit: int = 5,
) -> List[Dict[str, Any]]:
    rows = []
    for r in (rule_summary or {}).get("auto_applied", []) or []:
        rows.append({
            "address": str(r.get("address", "")).strip().upper(),
            "rule_id": str(r.get("rule_id", "-")),
            "recommended_action": str(r.get("recommended_action", "-")),
            "reason": str(r.get("reason", "-")),
        })

    if rows:
        return rows[: max(0, int(limit))]

    # Fallback to persisted local automation events.
    for ev in (rule_log_events or [])[::-1]:
        if not ev.get("auto_applied"):
            continue
        rows.append({
            "address": str(ev.get("address", "")).strip().upper(),
            "rule_id": str(ev.get("rule_id", "-")),
            "recommended_action": str(ev.get("recommended_action", "-")),
            "reason": str(ev.get("reason", "-")),
        })
        if len(rows) >= limit:
            break

    return rows


def _timeline_highlights(events: Optional[List[Dict[str, Any]]], limit: int = 5) -> List[str]:
    out = []
    for e in (events or [])[: max(0, int(limit))]:
        ts = str(e.get("timestamp") or "n/a")
        src = str(e.get("source", "?"))
        summary = str(e.get("summary", "-"))
        out.append(f"{ts} | {src} | {summary}")
    return out


def _suggested_next_steps(
    *,
    pending_confirmations_count: int,
    top_priorities: List[Dict[str, Any]],
    playbook_recommendations: Optional[List[Dict[str, Any]]],
    investigation_profile: Optional[Dict[str, Any]],
    open_cases_count: int,
    investigating_count: int,
) -> List[str]:
    steps: List[str] = []

    if pending_confirmations_count > 0:
        steps.append(f"Review {pending_confirmations_count} pending confirmations first")

    if top_priorities:
        p = top_priorities[0]
        steps.append(
            f"Prioritize {p.get('address', '?')} ({p.get('triage_bucket', 'normal')}/{p.get('triage_score', 0)})"
        )

    if playbook_recommendations:
        rec = playbook_recommendations[0]
        steps.append(f"Execute playbook action: {rec.get('recommended_action', 'n/a')}")

    if investigation_profile:
        case = investigation_profile.get("case", {}) if isinstance(investigation_profile, dict) else {}
        status = str(case.get("status", "none"))
        if status not in {"none", "resolved", "ignored"}:
            steps.append(f"Update investigation notes for case status={status}")

    if open_cases_count > 0:
        steps.append(f"Review open cases backlog ({open_cases_count})")

    if investigating_count > 0:
        steps.append(f"Sync investigating cases ({investigating_count}) before handoff")

    if not steps:
        steps.append("Maintain passive monitoring and reassess on next scan")

    # keep concise for handoff
    return steps[:5]


def build_operator_briefing(
    *,
    triage_results: Optional[List[Dict[str, Any]]] = None,
    investigation_profile: Optional[Dict[str, Any]] = None,
    workflow_summary: Optional[Dict[str, Any]] = None,
    timeline_events: Optional[List[Dict[str, Any]]] = None,
    playbook_recommendations: Optional[List[Dict[str, Any]]] = None,
    rule_summary: Optional[Dict[str, Any]] = None,
    rule_log_events: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build a compact shift handoff briefing dictionary."""
    top_priorities = _pick_top_priorities(triage_results, limit=5)

    open_cases_count = len((workflow_summary or {}).get("open", []) or [])
    investigating_count = len((workflow_summary or {}).get("investigating", []) or [])
    pending_confirmations_count = len((rule_summary or {}).get("pending_confirmations", []) or [])

    recent_auto_actions = _recent_auto_actions(rule_summary, rule_log_events, limit=5)
    recent_timeline_highlights = _timeline_highlights(timeline_events, limit=5)

    suggested_next_steps = _suggested_next_steps(
        pending_confirmations_count=pending_confirmations_count,
        top_priorities=top_priorities,
        playbook_recommendations=playbook_recommendations,
        investigation_profile=investigation_profile,
        open_cases_count=open_cases_count,
        investigating_count=investigating_count,
    )

    return {
        "top_priorities": top_priorities,
        "open_cases_count": open_cases_count,
        "investigating_count": investigating_count,
        "pending_confirmations_count": pending_confirmations_count,
        "recent_auto_actions": recent_auto_actions,
        "recent_timeline_highlights": recent_timeline_highlights,
        "suggested_next_steps": suggested_next_steps,
    }
