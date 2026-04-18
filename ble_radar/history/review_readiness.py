"""Lightweight review readiness / readiness gate system."""
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


def _state_from_score(score: int, has_evidence: bool, queue_state: str, outcome_labels: List[str]) -> str:
    q_state = str(queue_state or "new").strip().lower()
    labels = {str(x).strip().lower() for x in (outcome_labels or [])}

    if not has_evidence and score < 45:
        return "not_ready"
    if score < 55 or q_state in {"blocked", "waiting"}:
        return "needs_more_data"
    if score >= 85 and ("resolved_cleanly" in labels or "stabilized" in labels):
        return "ready_for_archive"
    if score >= 72 and ("resolved_cleanly" in labels or "stabilized" in labels):
        return "ready_for_handoff"
    return "ready_for_review"


def _recommended_disposition(state: str) -> str:
    if state == "ready_for_archive":
        return "archive"
    if state == "ready_for_handoff":
        return "handoff"
    if state == "ready_for_review":
        return "review"
    if state == "needs_more_data":
        return "collect_more_evidence"
    return "hold"


def build_review_readiness_profiles(
    queue_items: Optional[List[Dict[str, Any]]] = None,
    *,
    evidence_packs: Optional[List[Dict[str, Any]]] = None,
    queue_health_snapshot: Optional[Dict[str, Any]] = None,
    outcomes: Optional[List[Dict[str, Any]]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
    timeline_events: Optional[List[Dict[str, Any]]] = None,
    campaigns: Optional[List[Dict[str, Any]]] = None,
    workflow_summary: Optional[Dict[str, Any]] = None,
    investigation_profile: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build compact readiness gate profiles for supported scopes.

    Supported scopes: device, case, cluster, campaign, evidence_pack, queue_item.
    """
    rows = list(queue_items or [])
    packs = list(evidence_packs or [])
    health = queue_health_snapshot if isinstance(queue_health_snapshot, dict) else {}
    out_rows = list(outcomes or [])
    alert_rows = list(alerts or [])
    events = list(timeline_events or [])
    campaign_rows = list(campaigns or [])
    wf = workflow_summary if isinstance(workflow_summary, dict) else {}
    inv = investigation_profile if isinstance(investigation_profile, dict) else {}

    stamp = str(generated_at or _now())

    stale_ids = {str(x.get("item_id", "")).strip() for x in (health.get("stale_items", []) or []) if str(x.get("item_id", "")).strip()}
    queue_pressure = str(health.get("queue_pressure", "low")).strip().lower()

    alerts_by_scope: Dict[str, int] = {}
    for row in alert_rows:
        key = _norm(row.get("device_address") or row.get("address") or row.get("scope_id"))
        if not key:
            continue
        alerts_by_scope[key] = alerts_by_scope.get(key, 0) + 1

    outcomes_by_scope: Dict[str, List[Dict[str, Any]]] = {}
    for row in out_rows:
        key = _norm(row.get("scope_id"))
        if not key:
            continue
        outcomes_by_scope.setdefault(key, []).append(row)

    pack_keys = {
        _norm(p.get("scope_id") or p.get("pack_id"))
        for p in packs
        if _norm(p.get("scope_id") or p.get("pack_id"))
    }

    campaign_by_id = {
        str(c.get("campaign_id", "")).strip(): c
        for c in campaign_rows
        if str(c.get("campaign_id", "")).strip()
    }

    workflow_addr_status: Dict[str, str] = {}
    for group in ("needs_action", "investigating", "resolved", "open"):
        for row in (wf.get(group, []) or []):
            addr = _norm(row.get("address") or row.get("scope_id"))
            if not addr:
                continue
            workflow_addr_status[addr] = str(row.get("status", group))

    timeline_score = min(len(events), 8)
    inv_triage = _safe_int((inv.get("triage", {}) or {}).get("triage_score"), 0)

    profiles: List[Dict[str, Any]] = []
    for item in rows:
        scope_type = str(item.get("scope_type", "device")).strip().lower()
        scope_id = str(item.get("scope_id", "-")).strip()
        scope_key = _norm(scope_id)
        queue_state = str(item.get("queue_state", "new")).strip().lower()

        missing: List[str] = []
        strengths: List[str] = []

        has_evidence = scope_key in pack_keys
        if has_evidence:
            strengths.append("evidence_pack_available")
        else:
            missing.append("evidence_pack")

        scope_outcomes = outcomes_by_scope.get(scope_key, [])
        outcome_labels = [str(r.get("outcome_label", "")).strip().lower() for r in scope_outcomes]
        if scope_outcomes:
            strengths.append("outcome_history")
        else:
            missing.append("outcome_validation")

        alert_count = _safe_int(alerts_by_scope.get(scope_key), 0)
        if alert_count > 0:
            missing.append(f"active_alerts={alert_count}")
        else:
            strengths.append("no_active_alerts")

        if queue_state in {"ready", "in_review", "resolved", "archived"}:
            strengths.append(f"queue_state={queue_state}")
        else:
            missing.append(f"queue_state={queue_state}")

        if str(item.get("item_id", "")).strip() in stale_ids:
            missing.append("stale_queue_item")
        else:
            strengths.append("queue_freshness_ok")

        if queue_pressure in {"high", "critical"}:
            missing.append(f"queue_pressure={queue_pressure}")
        else:
            strengths.append(f"queue_pressure={queue_pressure or 'low'}")

        case_status = workflow_addr_status.get(scope_key, "")
        if scope_type in {"device", "case"} and case_status:
            if case_status in {"investigating", "review", "new"}:
                missing.append(f"case_status={case_status}")
            else:
                strengths.append(f"case_status={case_status}")

        if scope_type == "campaign" and scope_id in campaign_by_id:
            c_row = campaign_by_id.get(scope_id, {})
            c_status = str(c_row.get("status", "")).lower()
            if c_status in {"stable", "cooling_down", "closed"}:
                strengths.append(f"campaign_status={c_status}")
            else:
                missing.append(f"campaign_status={c_status or 'new'}")

        if inv_triage > 0 and scope_type in {"device", "case"}:
            if inv_triage >= 55:
                missing.append(f"triage_score={inv_triage}")
            else:
                strengths.append(f"triage_score={inv_triage}")

        score = 100
        score -= min(len(missing) * 10, 60)
        score += min(len(strengths) * 3, 15)
        score += min(timeline_score, 8)
        score = max(5, min(score, 98))

        readiness_state = _state_from_score(score, has_evidence, queue_state, outcome_labels)

        profiles.append(
            {
                "review_id": f"review-{scope_type}-{_slug(scope_id)}-{_slug(stamp)}",
                "scope_type": scope_type,
                "scope_id": scope_id,
                "readiness_state": readiness_state,
                "readiness_score": score,
                "missing_elements": missing[:8],
                "strengths": strengths[:8],
                "review_notes": (
                    f"state={readiness_state} | queue={queue_state} | evidence={'yes' if has_evidence else 'no'} "
                    f"| outcomes={len(scope_outcomes)} | alerts={alert_count}"
                ),
                "recommended_disposition": _recommended_disposition(readiness_state),
                "created_at": stamp,
            }
        )

    # Queue-item specific readiness from queue health stale context.
    for row in (health.get("stale_items", []) or [])[:8]:
        item_id = str(row.get("item_id", "")).strip()
        if not item_id:
            continue
        missing = ["stale_queue_item", "fresh_evidence_update"]
        strengths = [f"age_minutes={_safe_int(row.get('age_minutes'), 0)}"]
        score = max(10, 45 - min(_safe_int(row.get("age_minutes"), 0) // 30, 25))
        state = "needs_more_data"

        profiles.append(
            {
                "review_id": f"review-queue_item-{_slug(item_id)}-{_slug(stamp)}",
                "scope_type": "queue_item",
                "scope_id": item_id,
                "readiness_state": state,
                "readiness_score": score,
                "missing_elements": missing,
                "strengths": strengths,
                "review_notes": f"queue item stale and requires refresh before review | score={score}",
                "recommended_disposition": _recommended_disposition(state),
                "created_at": stamp,
            }
        )

    profiles.sort(
        key=lambda r: (
            _safe_int(r.get("readiness_score"), 0),
            str(r.get("readiness_state", "")),
        ),
        reverse=True,
    )

    return profiles[:48]


def summarize_review_readiness(profiles: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Build compact dashboard sections for review readiness gate panel."""
    rows = list(profiles or [])

    readiness = rows[:16]

    ready_for_review = [
        r for r in rows
        if str(r.get("readiness_state", "")).lower() == "ready_for_review"
    ][:10]

    needs_more_evidence = [
        r for r in rows
        if str(r.get("readiness_state", "")).lower() in {"not_ready", "needs_more_data"}
    ][:10]

    ready_for_handoff = [
        r for r in rows
        if str(r.get("readiness_state", "")).lower() == "ready_for_handoff"
    ][:10]

    ready_for_archive = [
        r for r in rows
        if str(r.get("readiness_state", "")).lower() == "ready_for_archive"
    ][:10]

    return {
        "review_readiness": readiness,
        "ready_for_review": ready_for_review,
        "needs_more_evidence": needs_more_evidence,
        "ready_for_handoff": ready_for_handoff,
        "ready_for_archive": ready_for_archive,
    }
