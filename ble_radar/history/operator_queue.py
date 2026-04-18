"""Lightweight operator queue / case board system.

Builds compact operator work items from existing project signals.
"""
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


def _norm_addr(value: Any) -> str:
    return str(value or "").strip().upper()


def _priority_label(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _queue_state(
    *,
    pending_confirmations: int = 0,
    risk_level: str = "low",
    status: str = "",
    has_blockers: bool = False,
) -> str:
    s = str(status or "").strip().lower()
    r = str(risk_level or "low").strip().lower()

    if s in {"resolved", "closed", "archived"}:
        return "resolved"
    if has_blockers:
        return "blocked"
    if pending_confirmations > 0:
        return "waiting"
    if s in {"investigating", "review"}:
        return "in_review"
    if r in {"critical", "high"}:
        return "ready"
    return "new"


def _owner_hint(scope_type: str, risk_level: str, pending_confirmations: int) -> str:
    if pending_confirmations > 0:
        return "Operator + Supervisor"
    if str(risk_level).lower() == "critical":
        return "Senior Operator"
    if scope_type in {"campaign", "cluster"}:
        return "Threat Analyst"
    if scope_type == "evidence_pack":
        return "Review Officer"
    return "Operator"


def _mk_item(
    *,
    scope_type: str,
    scope_id: str,
    queue_state: str,
    priority: str,
    owner_hint: str,
    reason_summary: str,
    recommended_action: str,
    blocking_factors: List[str],
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> Dict[str, Any]:
    c_at = str(created_at or _now())
    u_at = str(updated_at or c_at)
    sid = str(scope_id or "unknown").replace(":", "").replace("/", "-").lower()
    return {
        "item_id": f"q-{scope_type}-{sid}",
        "scope_type": scope_type,
        "scope_id": scope_id,
        "queue_state": queue_state,
        "priority": priority,
        "owner_hint": owner_hint,
        "reason_summary": reason_summary,
        "recommended_action": recommended_action,
        "blocking_factors": blocking_factors[:4],
        "created_at": c_at,
        "updated_at": u_at,
    }


def _alerts_for_address(alerts: List[Dict[str, Any]], address: str) -> List[Dict[str, Any]]:
    addr = _norm_addr(address)
    return [
        a for a in (alerts or [])
        if _norm_addr(a.get("device_address") or a.get("address")) == addr
    ]


def _build_device_item(
    address: str,
    triage_row: Dict[str, Any],
    *,
    watch_cases: Dict[str, Dict[str, Any]],
    pending_by_address: Dict[str, int],
    alerts: List[Dict[str, Any]],
    briefing: Optional[Dict[str, Any]] = None,
    stamp: Optional[str] = None,
) -> Dict[str, Any]:
    addr = _norm_addr(address)
    score = _safe_int(triage_row.get("triage_score", 0), 0)
    bucket = str(triage_row.get("triage_bucket", "normal")).strip().lower()
    case_status = str((watch_cases or {}).get(addr, {}).get("status", "none"))
    pending = _safe_int((pending_by_address or {}).get(addr, 0), 0)

    addr_alerts = _alerts_for_address(alerts, addr)
    sev_rank = 0
    for a in addr_alerts:
        sev = str(a.get("severity", "low")).lower()
        sev_rank = max(sev_rank, {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(sev, 1))

    risk_score = score + (sev_rank * 12) + (8 if bucket == "critical" else 0)
    priority = _priority_label(risk_score)

    blocking = []
    if pending > 0:
        blocking.append(f"{pending} pending confirmations")

    state = _queue_state(
        pending_confirmations=pending,
        risk_level=priority,
        status=case_status,
        has_blockers=bool(blocking),
    )

    reason = f"triage={bucket}:{score} | alerts={len(addr_alerts)} | case={case_status}"
    if briefing and briefing.get("suggested_next_steps"):
        reason += f" | briefing_steps={len(briefing.get('suggested_next_steps', []))}"

    return _mk_item(
        scope_type="device",
        scope_id=addr,
        queue_state=state,
        priority=priority,
        owner_hint=_owner_hint("device", priority, pending),
        reason_summary=reason,
        recommended_action="Review device context and apply playbook action",
        blocking_factors=blocking,
        created_at=stamp,
        updated_at=stamp,
    )


def build_operator_queue(
    *,
    triage_results: Optional[List[Dict[str, Any]]] = None,
    workflow_summary: Optional[Dict[str, Any]] = None,
    pending_confirmations: Optional[List[Dict[str, Any]]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
    briefing: Optional[Dict[str, Any]] = None,
    clusters: Optional[List[Dict[str, Any]]] = None,
    campaigns: Optional[List[Dict[str, Any]]] = None,
    evidence_packs: Optional[List[Dict[str, Any]]] = None,
    watch_cases: Optional[Dict[str, Dict[str, Any]]] = None,
    stamp: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build compact queue items for device/case/cluster/campaign/evidence_pack scopes."""
    triage_rows = list(triage_results or [])
    case_rows = dict(watch_cases or {})
    cluster_rows = list(clusters or [])
    campaign_rows = list(campaigns or [])
    pack_rows = list(evidence_packs or [])
    alert_rows = list(alerts or [])

    pending_by_address: Dict[str, int] = {}
    for row in (pending_confirmations or []):
        addr = _norm_addr(row.get("address"))
        if not addr:
            continue
        pending_by_address[addr] = pending_by_address.get(addr, 0) + 1

    items: List[Dict[str, Any]] = []

    # Device-scope queue from triage priorities.
    for row in triage_rows[:6]:
        addr = _norm_addr(row.get("address"))
        if not addr:
            continue
        items.append(
            _build_device_item(
                addr,
                row,
                watch_cases=case_rows,
                pending_by_address=pending_by_address,
                alerts=alert_rows,
                briefing=briefing,
                stamp=stamp,
            )
        )

    # Case-scope queue from workflow needs action / investigating.
    wf = workflow_summary if isinstance(workflow_summary, dict) else {}
    case_candidates = []
    case_candidates.extend(wf.get("needs_action", []) or [])
    case_candidates.extend(wf.get("investigating", []) or [])
    seen_case_addr = set()
    for row in case_candidates[:6]:
        addr = _norm_addr(row.get("address"))
        if not addr or addr in seen_case_addr:
            continue
        seen_case_addr.add(addr)

        status = str(row.get("status", case_rows.get(addr, {}).get("status", "new")))
        pending = _safe_int(pending_by_address.get(addr, 0), 0)
        blocking = [f"{pending} pending confirmations"] if pending > 0 else []

        state = _queue_state(
            pending_confirmations=pending,
            risk_level="high" if status in {"investigating", "review"} else "medium",
            status=status,
            has_blockers=bool(blocking),
        )

        items.append(
            _mk_item(
                scope_type="case",
                scope_id=addr,
                queue_state=state,
                priority="high" if status in {"investigating", "review"} else "medium",
                owner_hint=_owner_hint("case", "high", pending),
                reason_summary=f"workflow status={status}",
                recommended_action="Advance case workflow to next action",
                blocking_factors=blocking,
                created_at=stamp,
                updated_at=stamp,
            )
        )

    # Cluster-scope queue.
    for c in cluster_rows[:4]:
        scope_id = str(c.get("cluster_id", "cluster-unknown"))
        risk = str(c.get("risk_level", "low")).lower()
        members = _safe_int(c.get("member_count", 0), 0)

        state = _queue_state(
            risk_level=risk,
            status="in_review" if risk in {"critical", "high"} else "new",
            has_blockers=False,
        )
        if risk in {"critical", "high"}:
            state = "ready"

        items.append(
            _mk_item(
                scope_type="cluster",
                scope_id=scope_id,
                queue_state=state,
                priority=risk if risk in {"critical", "high", "medium", "low"} else "medium",
                owner_hint=_owner_hint("cluster", risk, 0),
                reason_summary=f"members={members} | {str(c.get('reason_summary', '-'))}",
                recommended_action=str(c.get("recommended_followup", "Review cluster coordination")),
                blocking_factors=[],
                created_at=stamp,
                updated_at=stamp,
            )
        )

    # Campaign-scope queue.
    for c in campaign_rows[:4]:
        scope_id = str(c.get("campaign_id", "campaign-unknown"))
        risk = str(c.get("risk_level", "low")).lower()
        status = str(c.get("status", "new")).lower()

        queue_state = "new"
        if status in {"resolved", "closed", "archived"}:
            queue_state = "resolved"
        elif status in {"expanding", "new"}:
            queue_state = "ready"
        elif status in {"recurring", "stable"}:
            queue_state = "in_review"
        elif status == "cooling_down":
            queue_state = "waiting"

        items.append(
            _mk_item(
                scope_type="campaign",
                scope_id=scope_id,
                queue_state=queue_state,
                priority=risk if risk in {"critical", "high", "medium", "low"} else "medium",
                owner_hint=_owner_hint("campaign", risk, 0),
                reason_summary=f"campaign_status={status} | trend={str(c.get('activity_trend', '-'))}",
                recommended_action=str(c.get("recommended_followup", "Review campaign lifecycle")),
                blocking_factors=[],
                created_at=stamp,
                updated_at=stamp,
            )
        )

    # Evidence pack-scope queue.
    for p in pack_rows[:6]:
        scope_id = str(p.get("pack_id", "pack-unknown"))
        risk = str(p.get("risk_level", "low")).lower()
        scope_type = str(p.get("scope_type", "device"))

        queue_state = "ready" if risk in {"critical", "high"} else "in_review"
        if scope_type == "campaign" and risk in {"critical", "high"}:
            queue_state = "ready"

        items.append(
            _mk_item(
                scope_type="evidence_pack",
                scope_id=scope_id,
                queue_state=queue_state,
                priority=risk if risk in {"critical", "high", "medium", "low"} else "medium",
                owner_hint=_owner_hint("evidence_pack", risk, 0),
                reason_summary=str(p.get("summary", "Evidence dossier available")),
                recommended_action=str(p.get("recommended_followup", "Review dossier and validate actions")),
                blocking_factors=[],
                created_at=str(p.get("generated_at", stamp or _now())),
                updated_at=stamp,
            )
        )

    # Stable ordering for case board readability.
    priority_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    state_rank = {
        "blocked": 6,
        "ready": 5,
        "in_review": 4,
        "waiting": 3,
        "new": 2,
        "resolved": 1,
        "archived": 0,
    }
    items.sort(
        key=lambda x: (
            state_rank.get(str(x.get("queue_state", "new")), 2),
            priority_rank.get(str(x.get("priority", "low")), 1),
        ),
        reverse=True,
    )

    return items[:48]


def summarize_operator_queue(items: Optional[List[Dict[str, Any]]] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Build compact dashboard groups for operator queue/case board panel."""
    rows = list(items or [])

    needs_review = [
        r for r in rows
        if str(r.get("queue_state", "")).lower() in {"in_review", "waiting"}
    ][:10]

    blocked = [
        r for r in rows
        if str(r.get("queue_state", "")).lower() == "blocked"
    ][:10]

    ready_now = [
        r for r in rows
        if str(r.get("queue_state", "")).lower() == "ready"
    ][:10]

    recently_resolved = [
        r for r in rows
        if str(r.get("queue_state", "")).lower() in {"resolved", "archived"}
    ][:10]

    return {
        "operator_queue": rows[:16],
        "needs_review": needs_review,
        "blocked_items": blocked,
        "ready_now": ready_now,
        "recently_resolved": recently_resolved,
    }
