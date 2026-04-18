"""Lightweight recommendation tuning / operator confidence system."""
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


def _confidence_level(score: int, success: int, failures: int, usage: int) -> str:
    if usage == 0:
        return "uncertain"
    if usage < 2 and failures > 0:
        return "uncertain"
    if score >= 78 and success >= max(2, failures + 1):
        return "high"
    if score >= 55 and success >= failures:
        return "medium"
    if score < 40 or failures > success:
        return "low"
    return "uncertain"


def _usage_notes(
    *,
    confidence: str,
    reopened_count: int,
    alert_count: int,
    pending_count: int,
    queue_pressure: str,
    campaign_signals: int,
) -> str:
    notes = []
    if confidence == "high":
        notes.append("Stable recommendation performance")
    elif confidence == "medium":
        notes.append("Useful recommendation with moderate variance")
    elif confidence == "low":
        notes.append("Low confidence recommendation")
    else:
        notes.append("Insufficient signal confidence")

    if reopened_count > 0:
        notes.append(f"reopened={reopened_count}")
    if pending_count > 0:
        notes.append(f"pending_confirmations={pending_count}")
    if alert_count > 0:
        notes.append(f"alerts_in_scope={alert_count}")
    if campaign_signals > 0:
        notes.append(f"campaign_signals={campaign_signals}")
    if str(queue_pressure or "low").lower() in {"high", "critical"}:
        notes.append(f"queue_pressure={queue_pressure}")

    return " | ".join(notes)


def _rank_adjustment(confidence: str, effectiveness_score: int, reopened_count: int, failure_count: int) -> int:
    if confidence == "high" and reopened_count == 0 and failure_count == 0:
        return 2
    if confidence == "medium" and effectiveness_score >= 60:
        return 1
    if confidence == "low":
        return -2
    if reopened_count > 0 or failure_count > 0:
        return -1
    return 0


def build_recommendation_tuning_profiles(
    outcomes: Optional[List[Dict[str, Any]]] = None,
    *,
    playbook_recommendations: Optional[List[Dict[str, Any]]] = None,
    rule_results: Optional[List[Dict[str, Any]]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
    queue_items: Optional[List[Dict[str, Any]]] = None,
    campaigns: Optional[List[Dict[str, Any]]] = None,
    evidence_packs: Optional[List[Dict[str, Any]]] = None,
    generated_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build compact confidence/tuning profiles for playbook recommendations."""
    outcome_rows = list(outcomes or [])
    playbook_rows = list(playbook_recommendations or [])
    rule_rows = list(rule_results or [])
    alert_rows = list(alerts or [])
    queue_rows = list(queue_items or [])
    campaign_rows = list(campaigns or [])
    pack_rows = list(evidence_packs or [])

    stamp = str(generated_at or _now())

    # Index context by scope id/address.
    queue_scope_index = {
        str(q.get("scope_id", "")).strip(): q
        for q in queue_rows
        if str(q.get("scope_id", "")).strip()
    }
    queue_addr_index = {
        _norm(q.get("scope_id")): q
        for q in queue_rows
        if _norm(q.get("scope_id"))
    }

    alerts_by_scope: Dict[str, int] = {}
    for row in alert_rows:
        key = _norm(row.get("device_address") or row.get("address") or row.get("scope_id"))
        if not key:
            continue
        alerts_by_scope[key] = alerts_by_scope.get(key, 0) + 1

    pending_by_scope: Dict[str, int] = {}
    for row in rule_rows:
        if not bool(row.get("requires_confirmation")):
            continue
        key = _norm(row.get("address") or row.get("scope_id"))
        if not key:
            continue
        pending_by_scope[key] = pending_by_scope.get(key, 0) + 1

    campaign_by_id = {
        str(c.get("campaign_id", "")).strip(): c
        for c in campaign_rows
        if str(c.get("campaign_id", "")).strip()
    }
    pack_by_id = {
        str(p.get("pack_id", "")).strip(): p
        for p in pack_rows
        if str(p.get("pack_id", "")).strip()
    }

    # Aggregate outcomes by playbook id.
    agg: Dict[str, Dict[str, Any]] = {}
    for row in outcome_rows:
        pb = str(row.get("source_playbook", "")).strip()
        if not pb:
            continue

        scope_type = str(row.get("scope_type", "device")).strip().lower() or "device"
        scope_id = str(row.get("scope_id", "-")).strip()
        eff = _safe_int(row.get("effectiveness"), 0)
        reopened = bool(row.get("reopened"))
        label = str(row.get("outcome_label", "")).strip().lower()

        bucket = agg.setdefault(
            pb,
            {
                "source_playbook": pb,
                "scope_type": scope_type,
                "success_count": 0,
                "failure_count": 0,
                "reopened_count": 0,
                "effectiveness_total": 0,
                "usage_count": 0,
                "sample_scope_id": scope_id,
            },
        )

        bucket["usage_count"] += 1
        bucket["effectiveness_total"] += eff
        bucket["sample_scope_id"] = bucket.get("sample_scope_id") or scope_id
        if reopened:
            bucket["reopened_count"] += 1

        if label in {"resolved_cleanly", "stabilized", "false_positive"} and eff >= 60 and not reopened:
            bucket["success_count"] += 1
        else:
            bucket["failure_count"] += 1

    # Ensure currently suggested playbooks appear even without outcomes yet.
    for pb_row in playbook_rows:
        pb = str(pb_row.get("playbook_id", "")).strip()
        if not pb:
            continue
        if pb not in agg:
            agg[pb] = {
                "source_playbook": pb,
                "scope_type": "device",
                "success_count": 0,
                "failure_count": 0,
                "reopened_count": 0,
                "effectiveness_total": 0,
                "usage_count": 0,
                "sample_scope_id": str(pb_row.get("address", "-")).strip(),
            }

    profiles: List[Dict[str, Any]] = []
    for pb, a in agg.items():
        usage = _safe_int(a.get("usage_count"), 0)
        success = _safe_int(a.get("success_count"), 0)
        failures = _safe_int(a.get("failure_count"), 0)
        reopened = _safe_int(a.get("reopened_count"), 0)

        base_eff = int((_safe_int(a.get("effectiveness_total"), 0) / usage)) if usage > 0 else 45

        scope_type = str(a.get("scope_type", "device"))
        scope_id = str(a.get("sample_scope_id", "-")).strip()
        scope_key = _norm(scope_id)

        queue_ctx = queue_scope_index.get(scope_id) or queue_addr_index.get(scope_key) or {}
        queue_state = str(queue_ctx.get("queue_state", "new")).strip().lower()
        queue_pressure_penalty = 8 if queue_state in {"blocked", "waiting"} else 0

        pending_count = _safe_int(pending_by_scope.get(scope_key), 0)
        pending_penalty = min(pending_count * 6, 18)

        alert_count = _safe_int(alerts_by_scope.get(scope_key), 0)
        alert_penalty = min(alert_count * 3, 15)

        campaign_signals = 0
        if scope_type == "campaign" and scope_id in campaign_by_id:
            c = campaign_by_id.get(scope_id, {})
            if str(c.get("status", "")).lower() in {"new", "expanding"}:
                campaign_signals += 1
            if str(c.get("risk_level", "")).lower() in {"high", "critical"}:
                campaign_signals += 1
        if scope_type == "evidence_pack" and scope_id in pack_by_id:
            p = pack_by_id.get(scope_id, {})
            if str(p.get("risk_level", "")).lower() in {"high", "critical"}:
                campaign_signals += 1

        signal_penalty = min(campaign_signals * 4, 12)

        effectiveness_score = max(
            5,
            min(
                100,
                base_eff
                - (reopened * 7)
                - queue_pressure_penalty
                - pending_penalty
                - alert_penalty
                - signal_penalty,
            ),
        )

        confidence = _confidence_level(effectiveness_score, success, failures, usage)

        usage_notes = _usage_notes(
            confidence=confidence,
            reopened_count=reopened,
            alert_count=alert_count,
            pending_count=pending_count,
            queue_pressure=queue_state,
            campaign_signals=campaign_signals,
        )

        profiles.append(
            {
                "recommendation_id": f"rectune-{_slug(pb)}-{_slug(scope_id or 'global')}",
                "source_playbook": pb,
                "scope_type": scope_type,
                "success_count": success,
                "failure_count": failures,
                "reopened_count": reopened,
                "confidence_level": confidence,
                "effectiveness_score": effectiveness_score,
                "usage_notes": usage_notes,
                "recommended_rank_adjustment": _rank_adjustment(confidence, effectiveness_score, reopened, failures),
                "created_at": stamp,
            }
        )

    profiles.sort(
        key=lambda r: (
            _safe_int(r.get("effectiveness_score"), 0),
            _safe_int(r.get("success_count"), 0) - _safe_int(r.get("failure_count"), 0),
        ),
        reverse=True,
    )

    return profiles[:32]


def summarize_recommendation_tuning_profiles(profiles: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Build compact dashboard sections for recommendation confidence tuning."""
    rows = list(profiles or [])

    confidence_rows = rows[:12]

    most_effective = [
        r for r in rows
        if str(r.get("confidence_level", "")).lower() in {"high", "medium"}
        and _safe_int(r.get("effectiveness_score"), 0) >= 60
    ][:8]

    weak = [
        r for r in rows
        if str(r.get("confidence_level", "")).lower() in {"low", "uncertain"}
        or _safe_int(r.get("recommended_rank_adjustment"), 0) < 0
        or _safe_int(r.get("effectiveness_score"), 0) < 50
    ][:10]

    manual_review = [
        r for r in rows
        if _safe_int(r.get("reopened_count"), 0) > 0
        or _safe_int(r.get("failure_count"), 0) > _safe_int(r.get("success_count"), 0)
        or str(r.get("confidence_level", "")).lower() == "uncertain"
    ][:10]

    return {
        "recommendation_confidence": confidence_rows,
        "most_effective_playbooks": most_effective,
        "weak_recommendations": weak,
        "needs_manual_review": manual_review,
    }
