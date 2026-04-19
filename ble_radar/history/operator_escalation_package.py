"""Lightweight operator escalation package / transmission system."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


_ALLOWED_SCOPE_TYPES = {"device", "case", "cluster", "campaign", "evidence_pack", "queue_item"}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _slug(value: Any) -> str:
    return str(value or "unknown").replace(":", "").replace("/", "-").replace(" ", "_").lower()


def _priority_from_reasons(reasons: List[str], queue_state: str, readiness_state: str) -> str:
    rset = set(reasons)
    if "high_risk_cluster" in rset or "blocked_long_too_long" in rset:
        return "critical"
    if "campaign_expanding" in rset or "repeated_reopen" in rset:
        return "high"
    if queue_state in {"blocked", "waiting"}:
        return "high"
    if readiness_state in {"ready_for_handoff", "ready_for_archive"}:
        return "medium"
    return "medium"


def _recommended_owner(scope_type: str, reasons: List[str], readiness_state: str) -> str:
    rset = set(reasons)
    if "ready_for_specialist_review" in rset:
        return "specialist_review_team"
    if scope_type in {"cluster", "campaign"}:
        return "campaign_specialist"
    if scope_type == "evidence_pack":
        return "forensics_analyst"
    if readiness_state in {"ready_for_handoff", "ready_for_archive"}:
        return "shift_lead"
    return "incident_operator"


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


def build_operator_escalation_packages(
    current_scopes: Optional[List[Dict[str, Any]]] = None,
    *,
    alerts: Optional[List[Dict[str, Any]]] = None,
    outcomes: Optional[List[Dict[str, Any]]] = None,
    recommendation_profiles: Optional[List[Dict[str, Any]]] = None,
    queue_items: Optional[List[Dict[str, Any]]] = None,
    queue_health_snapshot: Optional[Dict[str, Any]] = None,
    readiness_profiles: Optional[List[Dict[str, Any]]] = None,
    evidence_packs: Optional[List[Dict[str, Any]]] = None,
    campaigns: Optional[List[Dict[str, Any]]] = None,
    pattern_matches: Optional[List[Dict[str, Any]]] = None,
    session_journal: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build compact escalation packages for one scope each using existing signals."""
    scope_rows = list(current_scopes or [])
    alert_rows = list(alerts or [])
    outcome_rows = list(outcomes or [])
    rec_rows = list(recommendation_profiles or [])
    queue_rows = list(queue_items or [])
    readiness_rows = list(readiness_profiles or [])
    pack_rows = list(evidence_packs or [])
    campaign_rows = list(campaigns or [])
    match_rows = list(pattern_matches or [])
    health = queue_health_snapshot if isinstance(queue_health_snapshot, dict) else {}
    journal = session_journal if isinstance(session_journal, dict) else {}

    stamp = str(generated_at or _now())

    stale_ids = {
        _norm(r.get("item_id"))
        for r in (health.get("stale_items") or [])
        if _norm(r.get("item_id"))
    }

    packages: List[Dict[str, Any]] = []
    seen = set()

    for scope in scope_rows:
        scope_type = _norm(scope.get("scope_type") or "device")
        if scope_type not in _ALLOWED_SCOPE_TYPES:
            continue

        scope_id = str(scope.get("scope_id") or "-").strip()
        if not scope_id:
            continue

        scope_key = (scope_type, _norm(scope_id))
        if scope_key in seen:
            continue
        seen.add(scope_key)

        scope_queue = _find_scope_records(scope_id, queue_rows, ["scope_id", "item_id"]) if scope_type != "queue_item" else _find_scope_records(scope_id, queue_rows, ["item_id", "scope_id"])
        scope_outcomes = _find_scope_records(scope_id, outcome_rows, ["scope_id"])
        scope_ready = _find_scope_records(scope_id, readiness_rows, ["scope_id"])
        scope_recs = _find_scope_records(scope_id, rec_rows, ["scope_id"])
        scope_alerts = _find_scope_records(scope_id, alert_rows, ["scope_id", "device_address", "address"])
        scope_packs = _find_scope_records(scope_id, pack_rows, ["scope_id", "pack_id"])
        scope_campaign = _find_scope_records(scope_id, campaign_rows, ["campaign_id", "scope_id"])
        scope_matches = _find_scope_records(scope_id, match_rows, ["scope_id"])

        queue_state = _norm((scope_queue[0] if scope_queue else {}).get("queue_state") or scope.get("queue_state") or "new")
        readiness_state = _norm((scope_ready[0] if scope_ready else {}).get("readiness_state") or scope.get("readiness_state") or "not_ready")

        reasons: List[str] = []

        if scope_type == "cluster" and len(scope_alerts) >= 1:
            reasons.append("high_risk_cluster")

        reopened_count = len([
            r for r in scope_outcomes
            if _norm(r.get("outcome_label")) in {"reopened", "reopen", "reopened_after_followup"}
        ])
        if reopened_count >= 1:
            reasons.append("repeated_reopen")

        weak_conf_count = len([
            r for r in scope_recs
            if _norm(r.get("confidence_level")) in {"low", "uncertain"}
        ])
        if weak_conf_count >= 1:
            reasons.append("weak_recommendation_confidence")

        if queue_state in {"blocked", "waiting"} and (
            scope_type == "queue_item" and _norm(scope_id) in stale_ids
            or any(_norm(q.get("item_id")) in stale_ids for q in scope_queue)
        ):
            reasons.append("blocked_long_too_long")

        if readiness_state in {"ready_for_handoff", "ready_for_archive"}:
            reasons.append("ready_for_specialist_review")

        if scope_type == "campaign":
            c_status = _norm((scope_campaign[0] if scope_campaign else {}).get("status") or scope.get("status"))
            if c_status in {"expanding", "new"}:
                reasons.append("campaign_expanding")

        if weak_conf_count >= 1 and reopened_count >= 1:
            reasons.append("insufficient_resolution_confidence")

        # Keep reason set compact and deterministic.
        reason_set = []
        for reason in reasons:
            if reason not in reason_set:
                reason_set.append(reason)

        if not reason_set:
            continue

        priority = _priority_from_reasons(reason_set, queue_state, readiness_state)

        supporting_signals = [
            f"alerts={len(scope_alerts)}",
            f"outcomes={len(scope_outcomes)}",
            f"recommendations={len(scope_recs)}",
            f"queue_state={queue_state}",
            f"readiness={readiness_state}",
            f"evidence_packs={len(scope_packs)}",
            f"campaign_refs={len(scope_campaign)}",
            f"pattern_matches={len(scope_matches)}",
            f"queue_pressure={_norm(health.get('queue_pressure') or 'low')}",
        ]

        actions_already_taken: List[str] = []
        for r in scope_outcomes[:3]:
            action = str(r.get("source_action") or r.get("outcome_label") or "-").strip()
            if action and action != "-":
                actions_already_taken.append(action)

        for r in scope_recs[:2]:
            playbook = str(r.get("source_playbook") or r.get("playbook_id") or "").strip()
            if playbook:
                actions_already_taken.append(f"playbook:{playbook}")

        if not actions_already_taken:
            actions_already_taken.append("baseline_triage_review")

        open_risks = []
        if queue_state in {"blocked", "waiting"}:
            open_risks.append("queue_blockage")
        if weak_conf_count > 0:
            open_risks.append("low_recommendation_confidence")
        if reopened_count > 0:
            open_risks.append("reopen_cycle")
        if readiness_state in {"needs_more_data", "not_ready"}:
            open_risks.append("insufficient_readiness")
        if not scope_packs:
            open_risks.append("limited_evidence_context")

        next_owner = _recommended_owner(scope_type, reason_set, readiness_state)

        handoff_payload = {
            "summary": str(journal.get("handoff_summary") or "no_session_handoff_summary"),
            "next_shift_priorities": list(journal.get("next_shift_priorities", []) or [])[:5],
            "scope_snapshot": {
                "scope_type": scope_type,
                "scope_id": scope_id,
                "priority": priority,
                "reasons": reason_set,
            },
            "recommended_owner": next_owner,
        }

        packages.append(
            {
                "escalation_id": f"escalation-{scope_type}-{_slug(scope_id)}-{_slug(stamp)}",
                "scope_type": scope_type,
                "scope_id": scope_id,
                "escalation_reason": reason_set[0],
                "priority": priority,
                "supporting_signals": supporting_signals[:10],
                "actions_already_taken": actions_already_taken[:8],
                "open_risks": open_risks[:8],
                "recommended_next_owner": next_owner,
                "handoff_payload": handoff_payload,
                "created_at": stamp,
            }
        )

    packages.sort(
        key=lambda r: (
            {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(_norm(r.get("priority")), 0),
            str(r.get("created_at", "")),
        ),
        reverse=True,
    )

    return packages[:48]


def summarize_operator_escalation_packages(
    packages: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build compact dashboard sections for escalation package transmission panel."""
    rows = list(packages or [])

    escalation_packages = rows[:12]

    ready_to_escalate = [
        r for r in rows
        if _norm(r.get("priority")) in {"critical", "high"}
    ][:10]

    specialist_review_needed = [
        r for r in rows
        if _norm(r.get("recommended_next_owner")) in {"specialist_review_team", "campaign_specialist", "forensics_analyst"}
    ][:10]

    high_risk_open_items = [
        r for r in rows
        if "queue_blockage" in [str(x) for x in (r.get("open_risks") or [])]
        or _norm(r.get("priority")) == "critical"
    ][:10]

    recent_escalations = rows[:10]

    return {
        "escalation_packages": escalation_packages,
        "ready_to_escalate": ready_to_escalate,
        "specialist_review_needed": specialist_review_needed,
        "high_risk_open_items": high_risk_open_items,
        "recent_escalations": recent_escalations,
    }
