"""Lightweight operator reopen policy / controlled case reopening system."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


_ALLOWED_SCOPE_TYPES = {"device", "case", "cluster", "campaign", "evidence_pack", "queue_item"}
_ALLOWED_TRIGGER_TYPES = {
    "pattern_recurred",
    "campaign_resurfaced",
    "similar_alert_returned",
    "monitoring_triggered",
    "specialist_requested_reopen",
    "closure_confidence_too_low",
    "new_evidence_attached",
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _slug(value: Any) -> str:
    return str(value or "unknown").replace(":", "").replace("/", "-").replace(" ", "_").lower()


def _find_scope_records(scope_id: str, rows: List[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
    sid = _norm(scope_id)
    if not sid:
        return []

    out: List[Dict[str, Any]] = []
    for row in rows:
        for key in keys:
            if _norm(row.get(key)) == sid:
                out.append(row)
                break
    return out


def _trigger_rank(trigger_type: str) -> int:
    return {
        "specialist_requested_reopen": 7,
        "closure_confidence_too_low": 6,
        "campaign_resurfaced": 5,
        "pattern_recurred": 4,
        "similar_alert_returned": 3,
        "monitoring_triggered": 2,
        "new_evidence_attached": 1,
    }.get(_norm(trigger_type), 0)


def _extract_trigger_candidates(
    *,
    monitoring_rows: List[Dict[str, Any]],
    feedback_rows: List[Dict[str, Any]],
    recommendation_rows: List[Dict[str, Any]],
    pattern_rows: List[Dict[str, Any]],
    alert_rows: List[Dict[str, Any]],
    campaign_rows: List[Dict[str, Any]],
    evidence_rows: List[Dict[str, Any]],
) -> List[str]:
    candidates: List[str] = []

    if pattern_rows:
        candidates.append("pattern_recurred")

    if any(_norm(c.get("status")) in {"recurring", "expanding", "new"} for c in campaign_rows):
        candidates.append("campaign_resurfaced")

    if alert_rows:
        candidates.append("similar_alert_returned")

    if any(_norm(r.get("monitoring_mode")) in {"watch_for_recurrence", "high_attention_post_closure"} for r in monitoring_rows):
        candidates.append("monitoring_triggered")

    if any(
        _norm(r.get("review_result")) in {"needs_more_data", "escalate_further", "confirmed"}
        for r in feedback_rows
    ):
        candidates.append("specialist_requested_reopen")

    if any(_norm(r.get("confidence_level")) in {"low", "uncertain"} for r in recommendation_rows):
        candidates.append("closure_confidence_too_low")

    if evidence_rows:
        candidates.append("new_evidence_attached")

    deduped = []
    seen = set()
    for trigger in candidates:
        if trigger in _ALLOWED_TRIGGER_TYPES and trigger not in seen:
            seen.add(trigger)
            deduped.append(trigger)

    return deduped


def _trigger_summary(trigger_type: str, trigger_candidates: List[str], queue_pressure: str) -> str:
    return (
        f"trigger={trigger_type}"
        f" | supporting={','.join(trigger_candidates[:3]) or 'none'}"
        f" | queue_pressure={queue_pressure or 'low'}"
    )


def _reopen_reason(trigger_type: str, closure_row: Dict[str, Any], feedback_rows: List[Dict[str, Any]]) -> str:
    disposition = _norm(closure_row.get("final_disposition") or "resolved")
    followup = _norm(closure_row.get("followup_mode") or "none")
    review_result = _norm((feedback_rows[0] if feedback_rows else {}).get("review_result") or "confirmed")

    if trigger_type == "specialist_requested_reopen":
        return f"specialist_feedback={review_result}"
    if trigger_type == "closure_confidence_too_low":
        return "low_confidence_recommendation_detected"
    if trigger_type == "campaign_resurfaced":
        return "campaign_activity_returned_post_closure"
    if trigger_type == "pattern_recurred":
        return "known_pattern_recurred_on_closed_scope"
    if trigger_type == "similar_alert_returned":
        return "new_alert_matches_previous_closed_scope"
    if trigger_type == "monitoring_triggered":
        return "post_closure_monitoring_signaled_reopen"
    if trigger_type == "new_evidence_attached":
        return "new_evidence_pack_attached_after_closure"
    return f"closure={disposition}|followup={followup}"


def _priority(trigger_type: str, queue_pressure: str, reopen_count: int) -> str:
    pressure = _norm(queue_pressure)

    if trigger_type in {"specialist_requested_reopen", "closure_confidence_too_low"}:
        return "critical"
    if trigger_type in {"campaign_resurfaced", "pattern_recurred"}:
        return "high"
    if pressure in {"high", "critical"} or reopen_count >= 2:
        return "high"
    if trigger_type in {"similar_alert_returned", "monitoring_triggered"}:
        return "medium"
    return "low"


def _target_queue_state(trigger_type: str, reopen_priority: str) -> str:
    if trigger_type == "specialist_requested_reopen":
        return "in_review"
    if trigger_type in {"closure_confidence_too_low", "campaign_resurfaced"}:
        return "ready"
    if reopen_priority in {"critical", "high"}:
        return "in_review"
    return "waiting"


def _reopen_count(*, outcomes_rows: List[Dict[str, Any]], monitoring_rows: List[Dict[str, Any]], session_journal: Dict[str, Any]) -> int:
    count = 0

    for row in outcomes_rows:
        if bool(row.get("reopened")):
            count += 1
            continue
        label = _norm(row.get("outcome_label"))
        if label in {"resolved_but_returned", "reopened", "reopen"}:
            count += 1

    for row in monitoring_rows:
        triggers = [str(x) for x in (row.get("reopen_triggers") or [])]
        if triggers:
            count += 1

    carry_over = list(session_journal.get("next_shift_priorities", []) or [])
    if any("carry-over" in _norm(x) or "carry over" in _norm(x) for x in carry_over):
        count += 1

    return max(count, 1)


def build_operator_reopen_records(
    reopen_scopes: Optional[List[Dict[str, Any]]] = None,
    *,
    closure_packages: Optional[List[Dict[str, Any]]] = None,
    post_closure_monitoring_policies: Optional[List[Dict[str, Any]]] = None,
    escalation_feedback: Optional[List[Dict[str, Any]]] = None,
    outcomes: Optional[List[Dict[str, Any]]] = None,
    pattern_library: Optional[List[Dict[str, Any]]] = None,
    queue_health_snapshot: Optional[Dict[str, Any]] = None,
    alerts_history: Optional[List[Dict[str, Any]]] = None,
    campaign_tracking: Optional[List[Dict[str, Any]]] = None,
    evidence_packs: Optional[List[Dict[str, Any]]] = None,
    session_journal: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build compact reopen records for one scope from existing project signals."""
    scope_rows = list(reopen_scopes or [])
    closure_rows = list(closure_packages or [])
    monitoring_rows = list(post_closure_monitoring_policies or [])
    feedback_rows = list(escalation_feedback or [])
    outcome_rows = list(outcomes or [])
    pattern_rows = list(pattern_library or [])
    alert_rows = list(alerts_history or [])
    campaign_rows = list(campaign_tracking or [])
    evidence_rows = list(evidence_packs or [])
    health = queue_health_snapshot if isinstance(queue_health_snapshot, dict) else {}
    journal = session_journal if isinstance(session_journal, dict) else {}

    stamp = str(generated_at or _now())

    reopen_rows: List[Dict[str, Any]] = []
    seen = set()

    for scope in scope_rows:
        scope_type = _norm(scope.get("scope_type") or "device")
        if scope_type not in _ALLOWED_SCOPE_TYPES:
            continue

        scope_id = str(scope.get("scope_id") or "-").strip()
        if not scope_id:
            continue

        key = (scope_type, _norm(scope_id))
        if key in seen:
            continue
        seen.add(key)

        scoped_closures = _find_scope_records(scope_id, closure_rows, ["scope_id"])
        if not scoped_closures:
            continue
        closure_row = scoped_closures[0]

        scoped_monitoring = _find_scope_records(scope_id, monitoring_rows, ["scope_id"])
        scoped_feedback = _find_scope_records(scope_id, feedback_rows, ["scope_id"])
        scoped_outcomes = _find_scope_records(scope_id, outcome_rows, ["scope_id"])
        scoped_patterns = _find_scope_records(scope_id, pattern_rows, ["scope_id", "pattern_id"])
        scoped_alerts = _find_scope_records(scope_id, alert_rows, ["scope_id", "device_address", "address", "device_id"])
        scoped_campaigns = _find_scope_records(scope_id, campaign_rows, ["scope_id", "campaign_id"])
        scoped_evidence = _find_scope_records(scope_id, evidence_rows, ["scope_id", "pack_id"])

        recommendation_rows = []
        for row in scoped_outcomes:
            if _norm(row.get("outcome_label")) in {"needs_more_review", "resolved_but_returned"}:
                recommendation_rows.append({"confidence_level": "low"})

        trigger_candidates = _extract_trigger_candidates(
            monitoring_rows=scoped_monitoring,
            feedback_rows=scoped_feedback,
            recommendation_rows=recommendation_rows,
            pattern_rows=scoped_patterns,
            alert_rows=scoped_alerts,
            campaign_rows=scoped_campaigns,
            evidence_rows=scoped_evidence,
        )

        if not trigger_candidates:
            continue

        trigger_type = sorted(trigger_candidates, key=_trigger_rank, reverse=True)[0]
        queue_pressure = _norm(health.get("queue_pressure") or "low")
        reopen_count = _reopen_count(
            outcomes_rows=scoped_outcomes,
            monitoring_rows=scoped_monitoring,
            session_journal=journal,
        )

        reopen_priority = _priority(trigger_type, queue_pressure, reopen_count)
        target_state = _target_queue_state(trigger_type, reopen_priority)

        carry_forward_context = {
            "monitoring_mode": str((scoped_monitoring[0] if scoped_monitoring else {}).get("monitoring_mode", "none")),
            "queue_pressure": queue_pressure or "low",
            "recent_alert_count": len(scoped_alerts),
            "campaign_status": str((scoped_campaigns[0] if scoped_campaigns else {}).get("status", "none")),
            "evidence_pack_count": len(scoped_evidence),
            "handoff_summary": str(journal.get("handoff_summary", ""))[:120],
        }

        reopen_rows.append(
            {
                "reopen_id": f"reopen-{scope_type}-{_slug(scope_id)}-{_slug(stamp)}",
                "scope_type": scope_type,
                "scope_id": scope_id,
                "closure_id": str(closure_row.get("closure_id") or f"closure-{scope_type}-{_slug(scope_id)}"),
                "trigger_type": trigger_type,
                "trigger_summary": _trigger_summary(trigger_type, trigger_candidates, queue_pressure),
                "reopen_reason": _reopen_reason(trigger_type, closure_row, scoped_feedback),
                "reopen_priority": reopen_priority,
                "target_queue_state": target_state,
                "carry_forward_context": carry_forward_context,
                "reopen_count": reopen_count,
                "reopened_at": stamp,
            }
        )

    reopen_rows.sort(
        key=lambda r: (
            {
                "critical": 4,
                "high": 3,
                "medium": 2,
                "low": 1,
            }.get(_norm(r.get("reopen_priority")), 0),
            _trigger_rank(str(r.get("trigger_type", ""))),
            str(r.get("reopened_at", "")),
        ),
        reverse=True,
    )

    return reopen_rows[:48]


def summarize_operator_reopen_records(
    reopen_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build compact dashboard sections for controlled reopen panel."""
    rows = list(reopen_rows or [])

    reopened_cases = [
        r for r in rows
        if _norm(r.get("scope_type")) in {"case", "device"}
    ][:10]

    recent_reopen_triggers = sorted(
        rows,
        key=lambda r: str(r.get("reopened_at", "")),
        reverse=True,
    )[:10]

    returned_to_queue = [
        r for r in rows
        if _norm(r.get("target_queue_state")) in {"ready", "in_review", "waiting"}
    ][:10]

    repeated_reopeners = [
        r for r in rows
        if int(r.get("reopen_count") or 0) >= 2
    ][:10]

    high_priority_reopens = [
        r for r in rows
        if _norm(r.get("reopen_priority")) in {"high", "critical"}
    ][:10]

    return {
        "reopen_records": rows[:12],
        "reopened_cases": reopened_cases,
        "recent_reopen_triggers": recent_reopen_triggers,
        "returned_to_queue": returned_to_queue,
        "repeated_reopeners": repeated_reopeners,
        "high_priority_reopens": high_priority_reopens,
    }
