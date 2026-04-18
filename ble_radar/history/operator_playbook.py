"""Lightweight operator playbook recommendations for one device/case.

The module is intentionally explicit: one recommendation in, one compact result
out, driven by existing project signals when available.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_address(address: Any) -> str:
    return str(address or "").strip().upper()


def _has_incident_pack(
    investigation_profile: Optional[Dict[str, Any]],
    timeline_events: Optional[List[Dict[str, Any]]],
) -> bool:
    refs = (investigation_profile or {}).get("incident_refs", {})
    device_refs = refs.get("device_packs", []) or []
    legacy_refs = refs.get("incident_packs", []) or []
    if device_refs or legacy_refs:
        return True

    for ev in timeline_events or []:
        if str(ev.get("source", "")).lower() == "incident_pack":
            return True
        if str(ev.get("action", "")).lower() in {"incident_pack_generated", "generated"}:
            return True
    return False


def _case_status(case_record: Optional[Dict[str, Any]], investigation_profile: Optional[Dict[str, Any]]) -> str:
    if case_record and case_record.get("status"):
        return str(case_record.get("status", "")).strip().lower()
    profile_case = (investigation_profile or {}).get("case", {})
    return str(profile_case.get("status", "none")).strip().lower()


def _triage_fields(
    triage_row: Optional[Dict[str, Any]],
    investigation_profile: Optional[Dict[str, Any]],
) -> tuple[int, str, str]:
    if triage_row:
        score = _safe_int(triage_row.get("triage_score", 0), 0)
        bucket = str(triage_row.get("triage_bucket", "normal")).strip().lower()
        reason = str(triage_row.get("short_reason", "no signals"))
        return score, bucket, reason

    triage = (investigation_profile or {}).get("triage", {})
    score = _safe_int(triage.get("triage_score", 0), 0)
    bucket = str(triage.get("triage_bucket", "normal")).strip().lower()
    reason = str(triage.get("short_reason", "no signals"))
    return score, bucket, reason


def recommend_operator_playbook(
    address: Any,
    *,
    triage_row: Optional[Dict[str, Any]] = None,
    investigation_profile: Optional[Dict[str, Any]] = None,
    case_record: Optional[Dict[str, Any]] = None,
    timeline_events: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Return a compact playbook recommendation for one device/case.

    Returns keys:
      playbook_id, recommended_action, reason, priority, suggested_steps
    """
    addr = _normalize_address(address)
    if not addr:
        raise ValueError("address must not be empty")

    triage_score, triage_bucket, triage_reason = _triage_fields(triage_row, investigation_profile)
    status = _case_status(case_record, investigation_profile)
    pack_available = _has_incident_pack(investigation_profile, timeline_events)

    timeline_actions = {
        str(ev.get("action", "")).strip().lower()
        for ev in (timeline_events or [])
        if isinstance(ev, dict)
    }
    has_score_change = "score_change" in timeline_actions or "change_hint" in timeline_actions

    # Terminal cases first
    if status in {"resolved", "ignored"}:
        return {
            "playbook_id": "pb-close-monitor",
            "recommended_action": "Close and monitor for recurrence",
            "reason": f"Case status is {status}",
            "priority": "low",
            "suggested_steps": [
                "Confirm resolution notes are complete",
                "Keep device in passive watch mode",
                "Re-open only if critical signals recur",
            ],
        }

    # Highest urgency
    if triage_bucket == "critical" or triage_score >= 45:
        if not pack_available:
            return {
                "playbook_id": "pb-critical-pack",
                "recommended_action": "Escalate and generate incident pack",
                "reason": f"Critical triage ({triage_score}) and no incident pack available",
                "priority": "critical",
                "suggested_steps": [
                    "Assign case to investigating operator",
                    "Generate incident pack for evidence",
                    "Validate movement and timeline anomalies",
                    "Escalate to security lead",
                ],
            }
        return {
            "playbook_id": "pb-critical-investigate",
            "recommended_action": "Continue active investigation and escalation",
            "reason": f"Critical triage ({triage_score}) with incident artifacts available",
            "priority": "critical",
            "suggested_steps": [
                "Review latest incident pack and timeline",
                "Correlate with registry persistence and triage reason",
                "Add operator note and escalation decision",
            ],
        }

    # Review-level response
    if triage_bucket == "review" or status in {"new", "review"}:
        steps = [
            "Perform operator triage review",
            "Capture a short investigation note",
        ]
        if not pack_available:
            steps.append("Generate incident pack if uncertainty remains")
        if has_score_change:
            steps.append("Check score-change trend before final disposition")
        steps.append("Move case to investigating or ignored")

        return {
            "playbook_id": "pb-review-triage",
            "recommended_action": "Run review triage workflow",
            "reason": f"Review-level signals ({triage_score}) | {triage_reason}",
            "priority": "high",
            "suggested_steps": steps,
        }

    # Watch-level response
    if triage_bucket == "watch" or status in {"watch", "investigating"}:
        return {
            "playbook_id": "pb-watch-monitor",
            "recommended_action": "Monitor and schedule follow-up",
            "reason": f"Watch-level risk with status={status}",
            "priority": "medium",
            "suggested_steps": [
                "Track device across next sessions",
                "Add/update case note with latest context",
                "Promote to review if score increases",
            ],
        }

    # Default low-priority baseline
    return {
        "playbook_id": "pb-observe-baseline",
        "recommended_action": "Observe baseline activity",
        "reason": "No strong operator signals",
        "priority": "low",
        "suggested_steps": [
            "Keep in passive monitoring",
            "Re-assess if triage bucket increases",
        ],
    }
