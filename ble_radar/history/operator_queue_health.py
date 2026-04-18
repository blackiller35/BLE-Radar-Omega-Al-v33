"""Lightweight operator queue health / aging / bottleneck system."""
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


def _parse_dt(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d_%H-%M-%S",
        "%Y-%m-%d_%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    )
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _age_minutes(item: Dict[str, Any], now_dt: datetime) -> int:
    updated = _parse_dt(item.get("updated_at"))
    created = _parse_dt(item.get("created_at"))
    base = updated or created
    if not base:
        return 0
    delta = now_dt - base
    mins = int(delta.total_seconds() // 60)
    return max(mins, 0)


def _bucket(age_min: int) -> str:
    if age_min < 30:
        return "fresh"
    if age_min < 120:
        return "warm"
    if age_min < 480:
        return "aging"
    return "stale"


def _pressure_level(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def build_queue_health_snapshot(
    queue_items: Optional[List[Dict[str, Any]]] = None,
    *,
    workflow_summary: Optional[Dict[str, Any]] = None,
    pending_confirmations: Optional[List[Dict[str, Any]]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
    campaigns: Optional[List[Dict[str, Any]]] = None,
    evidence_packs: Optional[List[Dict[str, Any]]] = None,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build compact queue health snapshot from operator queue + related signals."""
    rows = list(queue_items or [])
    now_str = str(generated_at or _now())
    now_dt = _parse_dt(now_str) or datetime.now()

    total = len(rows)
    ready_count = 0
    blocked_count = 0
    in_review_count = 0

    aging_buckets = {
        "fresh": 0,
        "warm": 0,
        "aging": 0,
        "stale": 0,
    }

    stale_items: List[Dict[str, Any]] = []

    for item in rows:
        state = str(item.get("queue_state", "")).strip().lower()
        if state == "ready":
            ready_count += 1
        if state in {"blocked", "waiting"}:
            blocked_count += 1
        if state == "in_review":
            in_review_count += 1

        age_min = _age_minutes(item, now_dt)
        b = _bucket(age_min)
        aging_buckets[b] = aging_buckets.get(b, 0) + 1

        if b == "stale" or (state in {"blocked", "waiting"} and age_min >= 120):
            stale_items.append(
                {
                    "item_id": str(item.get("item_id", "?")),
                    "scope_type": str(item.get("scope_type", "-")),
                    "scope_id": str(item.get("scope_id", "-")),
                    "queue_state": state,
                    "age_minutes": age_min,
                }
            )

    stale_items.sort(key=lambda x: _safe_int(x.get("age_minutes"), 0), reverse=True)

    pending_count = len(list(pending_confirmations or []))
    critical_alerts = sum(1 for a in (alerts or []) if str(a.get("severity", "")).lower() == "critical")
    expanding_campaigns = sum(1 for c in (campaigns or []) if str(c.get("status", "")).lower() == "expanding")
    high_risk_packs = sum(1 for p in (evidence_packs or []) if str(p.get("risk_level", "")).lower() in {"critical", "high"})

    bottleneck_reasons: List[str] = []
    if blocked_count > 0:
        bottleneck_reasons.append(f"blocked_or_waiting_items={blocked_count}")
    if pending_count > 0:
        bottleneck_reasons.append(f"pending_confirmations={pending_count}")
    if aging_buckets.get("stale", 0) > 0:
        bottleneck_reasons.append(f"stale_items={aging_buckets['stale']}")
    if critical_alerts > 0:
        bottleneck_reasons.append(f"critical_alerts={critical_alerts}")
    if expanding_campaigns > 0:
        bottleneck_reasons.append(f"expanding_campaigns={expanding_campaigns}")

    wf = workflow_summary if isinstance(workflow_summary, dict) else {}
    wf_needs_action = len(wf.get("needs_action", []) or [])
    if wf_needs_action > 0:
        bottleneck_reasons.append(f"workflow_needs_action={wf_needs_action}")

    pressure_score = (
        min(total * 4, 24)
        + min(ready_count * 2, 20)
        + min(blocked_count * 8, 28)
        + min(aging_buckets.get("stale", 0) * 6, 24)
        + min(pending_count * 4, 20)
        + min(critical_alerts * 5, 20)
        + min(expanding_campaigns * 4, 16)
        + min(high_risk_packs * 2, 16)
    )
    queue_pressure = _pressure_level(pressure_score)

    if queue_pressure == "critical":
        followup = "Immediate queue triage: clear blocked items and resolve pending confirmations"
    elif queue_pressure == "high":
        followup = "Prioritize ready and stale items; run focused review for bottlenecks"
    elif queue_pressure == "medium":
        followup = "Maintain queue flow and monitor aging items"
    else:
        followup = "Queue health is stable; continue routine operator cadence"

    stamp_token = now_str.replace(" ", "_").replace(":", "").replace("-", "")

    return {
        "snapshot_id": f"qhealth-{stamp_token}",
        "generated_at": now_str,
        "total_items": total,
        "ready_count": ready_count,
        "blocked_count": blocked_count,
        "in_review_count": in_review_count,
        "aging_buckets": aging_buckets,
        "stale_items": stale_items[:10],
        "bottleneck_reasons": bottleneck_reasons[:8],
        "queue_pressure": queue_pressure,
        "recommended_followup": followup,
    }


def summarize_queue_health(
    snapshot: Optional[Dict[str, Any]] = None,
    queue_items: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build compact dashboard groups for queue health panel."""
    snap = dict(snapshot or {})
    rows = list(queue_items or [])

    blocked_items = [
        r for r in rows
        if str(r.get("queue_state", "")).lower() in {"blocked", "waiting"}
    ][:10]

    stale_map = {str(x.get("item_id", "")): x for x in snap.get("stale_items", [])}
    stale_rows = []
    for row in rows:
        iid = str(row.get("item_id", ""))
        if iid in stale_map:
            merged = dict(row)
            merged["age_minutes"] = _safe_int(stale_map[iid].get("age_minutes"), 0)
            stale_rows.append(merged)
    stale_rows.sort(key=lambda x: _safe_int(x.get("age_minutes"), 0), reverse=True)

    aging = []
    for key in ("fresh", "warm", "aging", "stale"):
        aging.append({"bucket": key, "count": _safe_int((snap.get("aging_buckets", {}) or {}).get(key, 0), 0)})

    return {
        "queue_health": snap,
        "aging_overview": aging,
        "blocked_items": blocked_items,
        "stale_items": stale_rows[:10],
        "operator_pressure": {
            "queue_pressure": str(snap.get("queue_pressure", "low")),
            "recommended_followup": str(snap.get("recommended_followup", "")),
            "bottleneck_reasons": list(snap.get("bottleneck_reasons", []) or [])[:8],
        },
    }
