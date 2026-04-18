"""Lightweight campaign tracking / cluster lifecycle system.

Builds persistent campaign records from correlation clusters and links current
clusters to previous campaigns when continuity is strong enough.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from ble_radar.config import HISTORY_DIR
from ble_radar.state import load_json, save_json

CAMPAIGN_LOG_FILE = HISTORY_DIR / "operator_campaigns.json"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_address(value: Any) -> str:
    return str(value or "").strip().upper()


def _risk_rank(risk_level: str) -> int:
    return {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }.get(str(risk_level or "low").strip().lower(), 1)


def _signal_key(signal: str) -> str:
    s = str(signal or "").strip().lower()
    if "movement" in s:
        return "movement"
    if "triage" in s:
        return "triage"
    if "timeline" in s:
        return "timeline"
    if "alert" in s:
        return "alert"
    if "playbook" in s:
        return "playbook"
    if "workflow" in s or "case" in s:
        return "workflow"
    if "investigation" in s:
        return "investigation"
    return s


def _signal_keys(signals: List[Any]) -> Set[str]:
    out: Set[str] = set()
    for row in signals or []:
        key = _signal_key(str(row))
        if key:
            out.add(key)
    return out


def load_campaign_records() -> List[Dict[str, Any]]:
    """Load campaign records from local persistent store."""
    rows = load_json(CAMPAIGN_LOG_FILE, [])
    return rows if isinstance(rows, list) else []


def save_campaign_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Save campaign records to local persistent store."""
    save_json(CAMPAIGN_LOG_FILE, records)
    return records


def _continuity_score(current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:
    curr_members = {_normalize_address(a) for a in current.get("member_addresses", []) if _normalize_address(a)}
    prev_members = {_normalize_address(a) for a in previous.get("member_addresses", []) if _normalize_address(a)}

    inter = curr_members.intersection(prev_members)
    min_base = max(1, min(len(curr_members), len(prev_members)))
    overlap = len(inter) / float(min_base)

    curr_risk = _risk_rank(str(current.get("risk_level", "low")))
    prev_risk = _risk_rank(str(previous.get("risk_level", "low")))
    risk_proximity = 1.0 - (abs(curr_risk - prev_risk) / 3.0)

    curr_signals = _signal_keys(current.get("top_signals", []))
    prev_signals = _signal_keys(previous.get("top_signals", []))

    timeline_sim = 1.0 if "timeline" in curr_signals and "timeline" in prev_signals else 0.0
    alert_sim = 1.0 if "alert" in curr_signals and "alert" in prev_signals else 0.0
    playbook_sim = 1.0 if "playbook" in curr_signals and "playbook" in prev_signals else 0.0
    movement_sim = 1.0 if "movement" in curr_signals and "movement" in prev_signals else 0.0

    score = (
        (0.55 * overlap)
        + (0.20 * risk_proximity)
        + (0.10 * timeline_sim)
        + (0.08 * alert_sim)
        + (0.04 * playbook_sim)
        + (0.03 * movement_sim)
    )

    return {
        "score": score,
        "overlap": overlap,
        "risk_proximity": risk_proximity,
        "timeline_similarity": timeline_sim,
        "alert_similarity": alert_sim,
        "playbook_similarity": playbook_sim,
        "movement_overlap": movement_sim,
    }


def _campaign_status(prev: Optional[Dict[str, Any]], current: Dict[str, Any], overlap: float) -> str:
    if not prev:
        return "new"

    prev_count = _safe_int(prev.get("member_count", 0), 0)
    curr_count = _safe_int(current.get("member_count", 0), 0)

    if curr_count > prev_count:
        return "expanding"
    if curr_count < prev_count:
        return "cooling_down"

    prev_risk = _risk_rank(str(prev.get("risk_level", "low")))
    curr_risk = _risk_rank(str(current.get("risk_level", "low")))

    if overlap >= 0.8 and prev_risk == curr_risk:
        return "stable"
    return "recurring"


def _activity_trend(status: str, prev: Optional[Dict[str, Any]], curr: Dict[str, Any]) -> str:
    if status == "new":
        return "up"
    if status == "expanding":
        return "up"
    if status == "cooling_down":
        return "down"
    if status == "closed":
        return "down"

    if prev:
        prev_risk = _risk_rank(str(prev.get("risk_level", "low")))
        curr_risk = _risk_rank(str(curr.get("risk_level", "low")))
        if curr_risk > prev_risk:
            return "up"
        if curr_risk < prev_risk:
            return "down"
    return "flat"


def _new_campaign_id(cluster: Dict[str, Any], stamp: str) -> str:
    members = [
        _normalize_address(a)
        for a in cluster.get("member_addresses", [])
        if _normalize_address(a)
    ]
    anchor = (members[0] if members else "unknown").replace(":", "").lower()
    token = stamp.replace(" ", "_").replace(":", "").replace("-", "")
    return f"campaign-{anchor}-{token}"


def build_campaign_lifecycle(
    clusters: Optional[List[Dict[str, Any]]] = None,
    *,
    previous_campaigns: Optional[List[Dict[str, Any]]] = None,
    stamp: Optional[str] = None,
    persist: bool = False,
) -> List[Dict[str, Any]]:
    """Build campaign lifecycle records from current clusters + previous campaigns."""
    current_clusters = list(clusters or [])
    old_rows = list(previous_campaigns or load_campaign_records())
    now_stamp = str(stamp or _now())

    active_old = [r for r in old_rows if str(r.get("status", "")).strip().lower() != "closed"]
    used_old_ids: Set[str] = set()
    campaign_rows: List[Dict[str, Any]] = []

    for cluster in current_clusters:
        best_prev = None
        best_metric = None

        for prev in active_old:
            prev_id = str(prev.get("campaign_id", "")).strip()
            if not prev_id or prev_id in used_old_ids:
                continue

            metric = _continuity_score(cluster, prev)
            if metric["score"] < 0.55 or metric["overlap"] < 0.4:
                continue
            if best_metric is None or metric["score"] > best_metric["score"]:
                best_prev = prev
                best_metric = metric

        if best_prev:
            used_old_ids.add(str(best_prev.get("campaign_id")))

        status = _campaign_status(best_prev, cluster, (best_metric or {}).get("overlap", 0.0))

        row = {
            "campaign_id": str(best_prev.get("campaign_id")) if best_prev else _new_campaign_id(cluster, now_stamp),
            "member_addresses": list(cluster.get("member_addresses", [])),
            "member_count": _safe_int(cluster.get("member_count", 0), 0),
            "status": status,
            "first_seen": str(best_prev.get("first_seen", now_stamp)) if best_prev else now_stamp,
            "last_seen": now_stamp,
            "activity_trend": _activity_trend(status, best_prev, cluster),
            "risk_level": str(cluster.get("risk_level", "low")),
            "reason_summary": str(cluster.get("reason_summary", "shared cluster continuity")),
            "recommended_followup": str(cluster.get("recommended_followup", "Review campaign continuity")),
            "top_signals": list(cluster.get("top_signals", [])),
        }
        campaign_rows.append(row)

    # Close previous campaigns not seen in the current run.
    for prev in active_old:
        prev_id = str(prev.get("campaign_id", "")).strip()
        if not prev_id or prev_id in used_old_ids:
            continue

        closed_row = dict(prev)
        closed_row["status"] = "closed"
        closed_row["last_seen"] = now_stamp
        closed_row["activity_trend"] = "down"
        campaign_rows.append(closed_row)

    # Keep history compact but useful.
    campaign_rows.sort(
        key=lambda r: (
            str(r.get("last_seen", "")),
            _risk_rank(str(r.get("risk_level", "low"))),
            _safe_int(r.get("member_count", 0), 0),
        ),
        reverse=True,
    )
    out = campaign_rows[:120]

    if persist:
        try:
            save_campaign_records(out)
        except Exception:
            pass

    return out


def summarize_campaigns(campaigns: Optional[List[Dict[str, Any]]] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Build compact dashboard groups for campaign lifecycle panel."""
    rows = list(campaigns or [])
    active = [r for r in rows if str(r.get("status", "")).lower() != "closed"]

    recurring = [
        r for r in active
        if str(r.get("status", "")).lower() in {"recurring", "stable", "cooling_down"}
    ][:8]

    expanding = [
        r for r in active
        if str(r.get("status", "")).lower() == "expanding"
    ][:8]

    needs_review = [
        r for r in active
        if str(r.get("risk_level", "")).lower() in {"critical", "high"}
        or str(r.get("status", "")).lower() in {"new", "expanding"}
    ][:8]

    return {
        "active_campaigns": active[:8],
        "recurring_clusters": recurring,
        "expanding_groups": expanding,
        "needs_campaign_review": needs_review,
    }
