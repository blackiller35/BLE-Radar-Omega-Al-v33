"""Lightweight operator closure package / final resolution system."""
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


def _final_disposition(
    *,
    review_result: str,
    escalation_reason: str,
    queue_state: str,
    readiness_state: str,
    outcome_labels: List[str],
) -> str:
    if review_result == "close_as_false_positive" or "false_positive" in outcome_labels:
        return "false_positive"
    if review_result == "monitor_only":
        return "monitor_only"
    if review_result == "close_as_resolved" or "resolved_cleanly" in outcome_labels or "stabilized" in outcome_labels:
        if escalation_reason:
            return "closed_after_escalation"
        return "resolved"
    if review_result == "escalate_further":
        return "resolved_with_followup"
    if readiness_state in {"ready_for_archive"} and queue_state in {"resolved", "closed", "archived"}:
        return "archived_for_reference"
    if queue_state in {"resolved", "closed"}:
        return "resolved"
    return "resolved_with_followup"


def _final_risk_level(disposition: str, weak_conf_count: int, queue_state: str, open_risks_count: int) -> str:
    if disposition in {"false_positive", "archived_for_reference"}:
        return "low"
    if disposition in {"resolved", "closed_after_escalation"} and weak_conf_count == 0 and open_risks_count == 0:
        return "low"
    if queue_state in {"blocked", "waiting"} or weak_conf_count > 0 or open_risks_count > 1:
        return "high"
    return "medium"


def _followup_mode(disposition: str, review_result: str, open_risks_count: int) -> str:
    if disposition in {"false_positive", "archived_for_reference"}:
        return "none"
    if review_result in {"needs_more_data", "escalate_further"}:
        return "specialist_followup"
    if disposition in {"monitor_only", "resolved_with_followup"} or open_risks_count > 0:
        return "monitor"
    return "none"


def _archive_recommendation(disposition: str, final_risk: str, readiness_state: str) -> str:
    if disposition in {"false_positive", "archived_for_reference"}:
        return "archive_now"
    if disposition in {"resolved", "closed_after_escalation"} and final_risk == "low":
        return "archive_after_brief_hold"
    if readiness_state == "ready_for_archive":
        return "archive_candidate"
    return "keep_active"


def build_operator_closure_packages(
    closure_scopes: Optional[List[Dict[str, Any]]] = None,
    *,
    escalation_feedback: Optional[List[Dict[str, Any]]] = None,
    escalation_packages: Optional[List[Dict[str, Any]]] = None,
    readiness_profiles: Optional[List[Dict[str, Any]]] = None,
    outcomes: Optional[List[Dict[str, Any]]] = None,
    recommendation_profiles: Optional[List[Dict[str, Any]]] = None,
    queue_items: Optional[List[Dict[str, Any]]] = None,
    queue_health_snapshot: Optional[Dict[str, Any]] = None,
    evidence_packs: Optional[List[Dict[str, Any]]] = None,
    pattern_matches: Optional[List[Dict[str, Any]]] = None,
    session_journal: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build compact closure packages for one scope from existing operator signals."""
    scope_rows = list(closure_scopes or [])
    feedback_rows = list(escalation_feedback or [])
    escalation_rows = list(escalation_packages or [])
    readiness_rows = list(readiness_profiles or [])
    outcome_rows = list(outcomes or [])
    rec_rows = list(recommendation_profiles or [])
    queue_rows = list(queue_items or [])
    pack_rows = list(evidence_packs or [])
    match_rows = list(pattern_matches or [])
    health = queue_health_snapshot if isinstance(queue_health_snapshot, dict) else {}
    journal = session_journal if isinstance(session_journal, dict) else {}

    stamp = str(generated_at or _now())

    closures: List[Dict[str, Any]] = []
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

        scope_feedback = _find_scope_records(scope_id, feedback_rows, ["scope_id"])
        scope_escalation = _find_scope_records(scope_id, escalation_rows, ["scope_id"])
        scope_ready = _find_scope_records(scope_id, readiness_rows, ["scope_id"])
        scope_outcomes = _find_scope_records(scope_id, outcome_rows, ["scope_id"])
        scope_recs = _find_scope_records(scope_id, rec_rows, ["scope_id"])
        scope_queue = _find_scope_records(scope_id, queue_rows, ["scope_id", "item_id"])
        scope_packs = _find_scope_records(scope_id, pack_rows, ["scope_id", "pack_id"])
        scope_matches = _find_scope_records(scope_id, match_rows, ["scope_id"])

        if not scope_feedback and not scope_escalation:
            continue

        last_feedback = scope_feedback[0] if scope_feedback else {}
        last_escalation = scope_escalation[0] if scope_escalation else {}
        readiness_state = _norm((scope_ready[0] if scope_ready else {}).get("readiness_state") or "not_ready")
        queue_state = _norm((scope_queue[0] if scope_queue else {}).get("queue_state") or "in_review")

        review_result = _norm(last_feedback.get("review_result") or "confirmed")
        escalation_reason = _norm(last_escalation.get("escalation_reason") or "")
        outcome_labels = [_norm(r.get("outcome_label")) for r in scope_outcomes]
        weak_conf_count = len([r for r in scope_recs if _norm(r.get("confidence_level")) in {"low", "uncertain"}])
        open_risks = [str(x) for x in (last_escalation.get("open_risks") or [])]

        disposition = _final_disposition(
            review_result=review_result,
            escalation_reason=escalation_reason,
            queue_state=queue_state,
            readiness_state=readiness_state,
            outcome_labels=outcome_labels,
        )

        final_risk = _final_risk_level(
            disposition,
            weak_conf_count,
            queue_state,
            len(open_risks),
        )
        followup_mode = _followup_mode(disposition, review_result, len(open_risks))
        archive_reco = _archive_recommendation(disposition, final_risk, readiness_state)

        key_supporting_signals = [
            f"review_result={review_result}",
            f"escalation_reason={escalation_reason or 'none'}",
            f"readiness={readiness_state}",
            f"queue_state={queue_state}",
            f"outcomes={len(scope_outcomes)}",
            f"weak_confidence={weak_conf_count}",
            f"evidence_packs={len(scope_packs)}",
            f"pattern_matches={len(scope_matches)}",
            f"queue_pressure={_norm(health.get('queue_pressure') or 'low')}",
        ]

        actions_taken = []
        actions_taken.extend([str(x) for x in (last_escalation.get("actions_already_taken") or []) if str(x).strip()][:4])
        actions_taken.extend([str(x) for x in (last_feedback.get("requested_followup") or []) if str(x).strip()][:3])
        if not actions_taken:
            actions_taken.append("baseline_resolution_review")

        resolution_summary = (
            f"Disposition={disposition} for {scope_type}:{scope_id} | "
            f"review={review_result} | risk={final_risk} | followup={followup_mode}"
        )

        closures.append(
            {
                "closure_id": f"closure-{scope_type}-{_slug(scope_id)}-{_slug(stamp)}",
                "scope_type": scope_type,
                "scope_id": scope_id,
                "final_disposition": disposition,
                "resolution_summary": resolution_summary,
                "key_supporting_signals": key_supporting_signals[:10],
                "actions_taken": actions_taken[:8],
                "final_risk_level": final_risk,
                "followup_mode": followup_mode,
                "archive_recommendation": archive_reco,
                "closed_at": stamp,
            }
        )

    closures.sort(
        key=lambda r: (
            {
                "resolved_with_followup": 6,
                "closed_after_escalation": 5,
                "resolved": 4,
                "monitor_only": 3,
                "archived_for_reference": 2,
                "false_positive": 1,
            }.get(_norm(r.get("final_disposition")), 0),
            str(r.get("closed_at", "")),
        ),
        reverse=True,
    )

    return closures[:48]


def summarize_operator_closure_packages(
    closures: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build compact dashboard sections for closure package panel."""
    rows = list(closures or [])

    closure_packages = rows[:12]
    recently_closed = rows[:10]

    closed_after_escalation = [
        r for r in rows
        if _norm(r.get("final_disposition")) == "closed_after_escalation"
    ][:10]

    resolved_vs_false_positive = {
        "resolved": len([r for r in rows if _norm(r.get("final_disposition")) in {"resolved", "resolved_with_followup", "closed_after_escalation"}]),
        "false_positive": len([r for r in rows if _norm(r.get("final_disposition")) == "false_positive"]),
    }

    followup_still_needed = [
        r for r in rows
        if _norm(r.get("followup_mode")) in {"monitor", "specialist_followup"}
    ][:10]

    return {
        "closure_packages": closure_packages,
        "recently_closed": recently_closed,
        "closed_after_escalation": closed_after_escalation,
        "resolved_vs_false_positive": resolved_vs_false_positive,
        "followup_still_needed": followup_still_needed,
    }
