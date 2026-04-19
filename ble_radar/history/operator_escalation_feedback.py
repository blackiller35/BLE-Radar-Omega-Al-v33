"""Lightweight operator escalation feedback / specialist return system."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


_ALLOWED_SCOPE_TYPES = {"device", "case", "cluster", "campaign", "evidence_pack", "queue_item"}


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

    found = []
    for row in rows:
        for key in keys:
            if _norm(row.get(key)) == sid:
                found.append(row)
                break
    return found


def _select_review_result(
    *,
    escalation_reason: str,
    priority: str,
    open_risks: List[str],
    readiness_state: str,
    outcome_labels: List[str],
    weak_conf_count: int,
    pattern_match_count: int,
    queue_state: str,
) -> str:
    if readiness_state in {"needs_more_data", "not_ready"} or "insufficient_readiness" in open_risks:
        return "needs_more_data"

    if any(lbl in {"false_positive", "close_as_false_positive"} for lbl in outcome_labels):
        return "close_as_false_positive"

    if (
        escalation_reason in {"high_risk_cluster", "campaign_expanding"}
        and priority in {"critical", "high"}
        and ("queue_blockage" in open_risks or pattern_match_count > 0)
    ):
        return "escalate_further"

    if (
        readiness_state == "ready_for_archive"
        or any(lbl in {"resolved_cleanly", "stabilized", "close_as_resolved"} for lbl in outcome_labels)
    ) and weak_conf_count == 0:
        return "close_as_resolved"

    if priority == "medium" and queue_state in {"in_review", "resolved", "monitoring"} and not open_risks:
        return "monitor_only"

    return "confirmed"


def _return_queue_state(review_result: str) -> str:
    if review_result == "needs_more_data":
        return "in_review"
    if review_result == "monitor_only":
        return "monitoring"
    if review_result == "close_as_resolved":
        return "resolved"
    if review_result == "close_as_false_positive":
        return "closed_false_positive"
    if review_result == "escalate_further":
        return "escalated"
    return "in_review"


def _closure_recommendation(review_result: str) -> str:
    if review_result in {"close_as_resolved", "close_as_false_positive"}:
        return "close_now"
    if review_result == "monitor_only":
        return "close_after_monitoring"
    return "keep_open"


def _requested_followup(review_result: str) -> List[str]:
    if review_result == "needs_more_data":
        return ["collect additional evidence", "refresh review readiness"]
    if review_result == "escalate_further":
        return ["handoff to specialist tier 2", "update escalation package"]
    if review_result == "monitor_only":
        return ["monitor scope for next shift"]
    if review_result in {"close_as_resolved", "close_as_false_positive"}:
        return ["finalize closure workflow"]
    return ["apply specialist guidance", "update queue notes"]


def build_operator_escalation_feedback_records(
    escalation_packages: Optional[List[Dict[str, Any]]] = None,
    *,
    readiness_profiles: Optional[List[Dict[str, Any]]] = None,
    outcomes: Optional[List[Dict[str, Any]]] = None,
    recommendation_profiles: Optional[List[Dict[str, Any]]] = None,
    queue_items: Optional[List[Dict[str, Any]]] = None,
    queue_health_snapshot: Optional[Dict[str, Any]] = None,
    evidence_packs: Optional[List[Dict[str, Any]]] = None,
    session_journal: Optional[Dict[str, Any]] = None,
    pattern_matches: Optional[List[Dict[str, Any]]] = None,
    generated_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build compact specialist-return feedback records for escalation packages."""
    packages = list(escalation_packages or [])
    readiness_rows = list(readiness_profiles or [])
    outcome_rows = list(outcomes or [])
    rec_rows = list(recommendation_profiles or [])
    queue_rows = list(queue_items or [])
    pack_rows = list(evidence_packs or [])
    match_rows = list(pattern_matches or [])
    health = queue_health_snapshot if isinstance(queue_health_snapshot, dict) else {}
    journal = session_journal if isinstance(session_journal, dict) else {}

    stamp = str(generated_at or _now())

    feedback_rows: List[Dict[str, Any]] = []

    for pkg in packages:
        scope_type = _norm(pkg.get("scope_type") or "device")
        if scope_type not in _ALLOWED_SCOPE_TYPES:
            continue

        scope_id = str(pkg.get("scope_id") or "-").strip()
        if not scope_id:
            continue

        escalation_id = str(pkg.get("escalation_id") or f"escalation-{scope_type}-{_slug(scope_id)}")
        escalation_reason = _norm(pkg.get("escalation_reason") or "needs_more_data")
        priority = _norm(pkg.get("priority") or "medium")
        open_risks = [str(x) for x in (pkg.get("open_risks") or [])]

        scope_ready = _find_scope_records(scope_id, readiness_rows, ["scope_id"])
        scope_outcomes = _find_scope_records(scope_id, outcome_rows, ["scope_id"])
        scope_recs = _find_scope_records(scope_id, rec_rows, ["scope_id"])
        scope_queue = _find_scope_records(scope_id, queue_rows, ["scope_id", "item_id"])
        scope_packs = _find_scope_records(scope_id, pack_rows, ["scope_id", "pack_id"])
        scope_matches = _find_scope_records(scope_id, match_rows, ["scope_id"])

        readiness_state = _norm((scope_ready[0] if scope_ready else {}).get("readiness_state") or "not_ready")
        queue_state = _norm((scope_queue[0] if scope_queue else {}).get("queue_state") or "in_review")
        outcome_labels = [_norm(r.get("outcome_label")) for r in scope_outcomes]
        weak_conf_count = len([r for r in scope_recs if _norm(r.get("confidence_level")) in {"low", "uncertain"}])

        review_result = _select_review_result(
            escalation_reason=escalation_reason,
            priority=priority,
            open_risks=open_risks,
            readiness_state=readiness_state,
            outcome_labels=outcome_labels,
            weak_conf_count=weak_conf_count,
            pattern_match_count=len(scope_matches),
            queue_state=queue_state,
        )

        requested_followup = _requested_followup(review_result)
        return_queue_state = _return_queue_state(review_result)
        closure_recommendation = _closure_recommendation(review_result)

        specialist_notes = (
            f"reason={escalation_reason} | readiness={readiness_state} | "
            f"queue_state={queue_state} | outcomes={len(scope_outcomes)} | weak_conf={weak_conf_count}"
        )
        decision_summary = (
            f"Specialist result={review_result} for {scope_type}:{scope_id} "
            f"(priority={priority}, pattern_matches={len(scope_matches)}, evidence_packs={len(scope_packs)})"
        )

        feedback_rows.append(
            {
                "feedback_id": f"feedback-{_slug(escalation_id)}-{_slug(stamp)}",
                "escalation_id": escalation_id,
                "scope_type": scope_type,
                "scope_id": scope_id,
                "review_result": review_result,
                "decision_summary": decision_summary,
                "specialist_notes": specialist_notes,
                "requested_followup": requested_followup,
                "return_queue_state": return_queue_state,
                "closure_recommendation": closure_recommendation,
                "received_at": stamp,
            }
        )

    feedback_rows.sort(
        key=lambda r: (
            {
                "escalate_further": 6,
                "needs_more_data": 5,
                "confirmed": 4,
                "monitor_only": 3,
                "close_as_resolved": 2,
                "close_as_false_positive": 1,
            }.get(_norm(r.get("review_result")), 0),
            str(r.get("received_at", "")),
        ),
        reverse=True,
    )

    return feedback_rows[:48]


def summarize_operator_escalation_feedback(
    feedback_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build compact dashboard sections for escalation feedback panel."""
    rows = list(feedback_rows or [])

    escalation_feedback = rows[:12]

    returned_for_followup = [
        r for r in rows
        if _norm(r.get("review_result")) in {"confirmed", "needs_more_data", "escalate_further"}
    ][:10]

    specialist_decisions = [
        {
            "feedback_id": str(r.get("feedback_id", "-")),
            "scope_type": str(r.get("scope_type", "-")),
            "scope_id": str(r.get("scope_id", "-")),
            "review_result": str(r.get("review_result", "-")),
            "decision_summary": str(r.get("decision_summary", "-")),
        }
        for r in rows[:10]
    ]

    ready_to_close = [
        r for r in rows
        if _norm(r.get("review_result")) in {"close_as_resolved", "close_as_false_positive"}
    ][:10]

    needs_more_data = [
        r for r in rows
        if _norm(r.get("review_result")) == "needs_more_data"
    ][:10]

    return {
        "escalation_feedback": escalation_feedback,
        "returned_for_followup": returned_for_followup,
        "specialist_decisions": specialist_decisions,
        "ready_to_close": ready_to_close,
        "needs_more_data": needs_more_data,
    }
