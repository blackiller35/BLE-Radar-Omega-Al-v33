"""Lightweight operator outcome tracking / feedback loop system."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


_VALID_LABELS = {
    "resolved_cleanly",
    "resolved_but_returned",
    "needs_more_review",
    "false_positive",
    "stabilized",
    "escalated",
}


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


def _rule_rows_for_scope(rule_results: List[Dict[str, Any]], scope_id: str) -> List[Dict[str, Any]]:
    sid = _norm(scope_id)
    return [
        r
        for r in (rule_results or [])
        if _norm(r.get("address") or r.get("scope_id")) == sid
    ]


def _alerts_for_scope(alerts: List[Dict[str, Any]], scope_id: str) -> List[Dict[str, Any]]:
    sid = _norm(scope_id)
    return [
        a
        for a in (alerts or [])
        if _norm(a.get("device_address") or a.get("address") or a.get("scope_id")) == sid
    ]


def _queue_state_after(
    *,
    scope_type: str,
    state_before: str,
    has_pending: bool,
    has_critical_alert: bool,
    campaign_status: str,
    evidence_risk: str,
) -> str:
    state = str(state_before or "new").strip().lower()
    c_status = str(campaign_status or "").strip().lower()
    e_risk = str(evidence_risk or "").strip().lower()

    if state in {"resolved", "archived"}:
        return "resolved"
    if has_pending:
        return "waiting"
    if has_critical_alert:
        return "in_review"
    if scope_type == "campaign":
        if c_status in {"closed", "cooling_down"}:
            return "resolved"
        if c_status in {"stable", "recurring"}:
            return "in_review"
    if scope_type == "evidence_pack":
        if e_risk in {"low", "medium"}:
            return "resolved"
    if state == "blocked":
        return "in_review"
    if state == "ready":
        return "in_review"
    return state


def _effectiveness(label: str, reopened: bool, has_pending: bool, has_critical_alert: bool) -> int:
    base = {
        "resolved_cleanly": 88,
        "resolved_but_returned": 36,
        "needs_more_review": 44,
        "false_positive": 72,
        "stabilized": 74,
        "escalated": 62,
    }.get(label, 50)

    if reopened:
        base -= 15
    if has_pending:
        base -= 10
    if has_critical_alert:
        base -= 8

    return max(5, min(base, 100))


def _label_and_resolution(
    *,
    scope_type: str,
    state_before: str,
    state_after: str,
    case_status: str,
    has_pending: bool,
    has_critical_alert: bool,
    campaign_status: str,
    evidence_risk: str,
    queue_pressure: str,
) -> tuple[str, str, bool]:
    before = str(state_before or "new").strip().lower()
    after = str(state_after or "new").strip().lower()
    case_s = str(case_status or "").strip().lower()
    c_status = str(campaign_status or "").strip().lower()
    e_risk = str(evidence_risk or "").strip().lower()
    pressure = str(queue_pressure or "low").strip().lower()

    reopened = before in {"resolved", "archived"} and (
        has_critical_alert
        or has_pending
        or pressure in {"high", "critical"}
        or case_s in {"review", "investigating"}
    )

    if reopened:
        return "resolved_but_returned", "reopened", True

    if case_s == "ignored":
        return "false_positive", "closed", False

    if before in {"blocked", "waiting"} or has_pending:
        return "needs_more_review", "needs_action", False

    if has_critical_alert:
        return "escalated", "escalated", False

    if scope_type == "campaign" and c_status in {"stable", "cooling_down", "closed"}:
        return "stabilized", "monitoring", False

    if scope_type == "evidence_pack" and e_risk in {"low", "medium"} and after == "resolved":
        return "resolved_cleanly", "closed", False

    if after in {"resolved", "archived"}:
        return "resolved_cleanly", "closed", False

    return "stabilized", "monitoring", False


def _mk_outcome(
    *,
    scope_type: str,
    scope_id: str,
    source_action: str,
    source_playbook: str,
    queue_state_before: str,
    queue_state_after: str,
    resolution_state: str,
    outcome_label: str,
    effectiveness: int,
    reopened: bool,
    created_at: str,
) -> Dict[str, Any]:
    label = outcome_label if outcome_label in _VALID_LABELS else "needs_more_review"
    return {
        "outcome_id": f"outcome-{scope_type}-{_slug(scope_id)}-{_slug(created_at)}",
        "scope_type": str(scope_type),
        "scope_id": str(scope_id),
        "source_action": str(source_action or "Review operator context"),
        "source_playbook": str(source_playbook or ""),
        "queue_state_before": str(queue_state_before or "new"),
        "queue_state_after": str(queue_state_after or "new"),
        "resolution_state": str(resolution_state or "needs_action"),
        "outcome_label": label,
        "effectiveness": _safe_int(effectiveness, 0),
        "reopened": bool(reopened),
        "created_at": str(created_at),
    }


def build_operator_outcomes(
    queue_items: Optional[List[Dict[str, Any]]] = None,
    *,
    workflow_summary: Optional[Dict[str, Any]] = None,
    playbook_recommendations: Optional[List[Dict[str, Any]]] = None,
    rule_results: Optional[List[Dict[str, Any]]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
    campaigns: Optional[List[Dict[str, Any]]] = None,
    evidence_packs: Optional[List[Dict[str, Any]]] = None,
    queue_health_snapshot: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build compact operator outcomes across supported scopes.

    Supported scope types: device, case, cluster, campaign, evidence_pack, queue_item.
    """
    rows = list(queue_items or [])
    pb_rows = list(playbook_recommendations or [])
    rr_rows = list(rule_results or [])
    alert_rows = list(alerts or [])
    campaign_rows = list(campaigns or [])
    pack_rows = list(evidence_packs or [])
    wf = workflow_summary if isinstance(workflow_summary, dict) else {}
    health = queue_health_snapshot if isinstance(queue_health_snapshot, dict) else {}

    stamp = str(generated_at or _now())

    playbook_by_scope: Dict[str, Dict[str, Any]] = {}
    for p in pb_rows:
        sid = _norm(p.get("address") or p.get("scope_id"))
        if sid:
            playbook_by_scope[sid] = p

    case_status_by_addr: Dict[str, str] = {}
    for group_name in ("needs_action", "investigating", "resolved", "open"):
        for row in (wf.get(group_name, []) or []):
            addr = _norm(row.get("address") or row.get("scope_id"))
            if addr:
                case_status_by_addr[addr] = str(row.get("status", group_name))

    campaign_by_id = {str(c.get("campaign_id", "")).strip(): c for c in campaign_rows}
    pack_by_id = {str(p.get("pack_id", "")).strip(): p for p in pack_rows}

    outcomes: List[Dict[str, Any]] = []

    for item in rows:
        scope_type = str(item.get("scope_type", "device")).strip().lower()
        scope_id = str(item.get("scope_id", "-")).strip()
        before = str(item.get("queue_state", "new")).strip().lower()

        pb = playbook_by_scope.get(_norm(scope_id), {})
        rule_rows = _rule_rows_for_scope(rr_rows, scope_id)
        scope_alerts = _alerts_for_scope(alert_rows, scope_id)

        has_pending = any(bool(r.get("requires_confirmation")) for r in rule_rows)
        has_critical_alert = any(str(a.get("severity", "")).lower() == "critical" for a in scope_alerts)

        c_row = campaign_by_id.get(scope_id, {}) if scope_type == "campaign" else {}
        p_row = pack_by_id.get(scope_id, {}) if scope_type == "evidence_pack" else {}

        case_status = case_status_by_addr.get(_norm(scope_id), "none")
        campaign_status = str(c_row.get("status", ""))
        evidence_risk = str(p_row.get("risk_level", ""))

        after = _queue_state_after(
            scope_type=scope_type,
            state_before=before,
            has_pending=has_pending,
            has_critical_alert=has_critical_alert,
            campaign_status=campaign_status,
            evidence_risk=evidence_risk,
        )

        label, resolution_state, reopened = _label_and_resolution(
            scope_type=scope_type,
            state_before=before,
            state_after=after,
            case_status=case_status,
            has_pending=has_pending,
            has_critical_alert=has_critical_alert,
            campaign_status=campaign_status,
            evidence_risk=evidence_risk,
            queue_pressure=str(health.get("queue_pressure", "low")),
        )

        eff = _effectiveness(label, reopened, has_pending, has_critical_alert)

        outcomes.append(
            _mk_outcome(
                scope_type=scope_type,
                scope_id=scope_id,
                source_action=str(pb.get("recommended_action") or item.get("recommended_action") or "Review operator context"),
                source_playbook=str(pb.get("playbook_id", "")),
                queue_state_before=before,
                queue_state_after=after,
                resolution_state=resolution_state,
                outcome_label=label,
                effectiveness=eff,
                reopened=reopened,
                created_at=str(item.get("updated_at") or stamp),
            )
        )

    # Queue-item outcomes from queue health stale/bottleneck context (feedback loop layer).
    stale_rows = list(health.get("stale_items", []) or [])[:8]
    for row in stale_rows:
        item_id = str(row.get("item_id", "queue-item"))
        q_state = str(row.get("queue_state", "waiting")).strip().lower()
        reopened = q_state in {"resolved", "archived"}
        label = "needs_more_review" if not reopened else "resolved_but_returned"
        resolution = "needs_action" if not reopened else "reopened"
        eff = _effectiveness(label, reopened, has_pending=False, has_critical_alert=False)

        outcomes.append(
            _mk_outcome(
                scope_type="queue_item",
                scope_id=item_id,
                source_action=str(health.get("recommended_followup", "Run queue health follow-up")),
                source_playbook="",
                queue_state_before=q_state,
                queue_state_after="in_review",
                resolution_state=resolution,
                outcome_label=label,
                effectiveness=eff,
                reopened=reopened,
                created_at=stamp,
            )
        )

    outcomes.sort(
        key=lambda r: (
            bool(r.get("reopened")),
            -_safe_int(r.get("effectiveness"), 0),
            str(r.get("created_at", "")),
        ),
        reverse=True,
    )

    return outcomes[:48]


def summarize_operator_outcomes(outcomes: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Build compact dashboard groups for operator outcome feedback loop panel."""
    rows = list(outcomes or [])

    action_agg: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        action = str(row.get("source_action", "-")).strip() or "-"
        bucket = action_agg.setdefault(action, {"source_action": action, "count": 0, "total_effectiveness": 0})
        bucket["count"] += 1
        bucket["total_effectiveness"] += _safe_int(row.get("effectiveness"), 0)

    most_effective_actions = []
    for item in action_agg.values():
        count = max(_safe_int(item.get("count", 0), 0), 1)
        avg = int(item.get("total_effectiveness", 0) / count)
        most_effective_actions.append(
            {
                "source_action": item.get("source_action"),
                "count": count,
                "avg_effectiveness": avg,
            }
        )

    most_effective_actions.sort(
        key=lambda x: (_safe_int(x.get("avg_effectiveness"), 0), _safe_int(x.get("count"), 0)),
        reverse=True,
    )

    reopened_items = [r for r in rows if bool(r.get("reopened"))][:10]

    weak_recommendations = [
        r for r in rows
        if _safe_int(r.get("effectiveness"), 0) < 50
        or str(r.get("outcome_label", "")) in {"needs_more_review", "resolved_but_returned"}
    ][:12]

    return {
        "operator_outcomes": rows[:16],
        "most_effective_actions": most_effective_actions[:8],
        "reopened_items": reopened_items,
        "weak_recommendations": weak_recommendations,
    }
