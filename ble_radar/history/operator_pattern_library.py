"""Lightweight operator pattern library / recurring case memory system."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


_SUPPORTED_TYPES = {"device", "case", "cluster", "campaign", "evidence_pack", "queue_item"}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _slug(value: Any) -> str:
    return (
        str(value or "unknown")
        .replace(":", "")
        .replace("/", "-")
        .replace(" ", "_")
        .lower()
    )


def _scope_type(row: Dict[str, Any]) -> str:
    t = _norm(row.get("scope_type") or row.get("pattern_type") or row.get("type") or "device")
    if t not in _SUPPORTED_TYPES:
        return "device"
    return t


def _scope_id(row: Dict[str, Any]) -> str:
    return str(row.get("scope_id") or row.get("item_id") or row.get("campaign_id") or row.get("pack_id") or "-")


def _confidence_from_score(score: int) -> str:
    if score >= 78:
        return "high"
    if score >= 55:
        return "medium"
    return "low"


def _risk_profile(
    *,
    severity_score: int,
    alerts_count: int,
    weak_hits: int,
    queue_state: str,
) -> str:
    if severity_score >= 80 or alerts_count >= 2 or queue_state in {"blocked", "waiting"}:
        return "high"
    if severity_score >= 50 or weak_hits > 0:
        return "medium"
    return "low"


def _pitfalls_for_type(pattern_type: str, weak_hits: int, queue_state: str, readiness_state: str) -> List[str]:
    pitfalls: List[str] = []
    if weak_hits > 0:
        pitfalls.append("repeated weak recommendations")
    if queue_state in {"blocked", "waiting"}:
        pitfalls.append("queue friction may delay closure")
    if readiness_state in {"needs_more_data", "not_ready"}:
        pitfalls.append("readiness gate missing evidence")

    if pattern_type == "campaign":
        pitfalls.append("campaign scope can hide mixed-risk devices")
    elif pattern_type == "cluster":
        pitfalls.append("cluster correlation may include noisy neighbors")
    elif pattern_type == "evidence_pack":
        pitfalls.append("evidence packs can become stale without refresh")

    return pitfalls[:4] or ["no major pitfalls observed"]


def build_operator_pattern_records(
    *,
    outcomes: Optional[List[Dict[str, Any]]] = None,
    recommendation_profiles: Optional[List[Dict[str, Any]]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
    campaigns: Optional[List[Dict[str, Any]]] = None,
    clusters: Optional[List[Dict[str, Any]]] = None,
    queue_items: Optional[List[Dict[str, Any]]] = None,
    readiness_profiles: Optional[List[Dict[str, Any]]] = None,
    session_journal: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build compact reusable operator patterns from existing project signals."""
    out_rows = list(outcomes or [])
    rec_rows = list(recommendation_profiles or [])
    alert_rows = list(alerts or [])
    campaign_rows = list(campaigns or [])
    cluster_rows = list(clusters or [])
    queue_rows = list(queue_items or [])
    ready_rows = list(readiness_profiles or [])
    journal = session_journal if isinstance(session_journal, dict) else {}

    stamp = str(generated_at or _now())

    alerts_by_scope: Dict[str, int] = {}
    for row in alert_rows:
        key = _norm(row.get("scope_id") or row.get("device_address") or row.get("address"))
        if not key:
            continue
        alerts_by_scope[key] = alerts_by_scope.get(key, 0) + 1

    queue_by_scope: Dict[str, Dict[str, Any]] = {}
    for row in queue_rows:
        key = _norm(_scope_id(row))
        if not key:
            continue
        queue_by_scope.setdefault(key, row)

    readiness_by_scope: Dict[str, Dict[str, Any]] = {}
    for row in ready_rows:
        key = _norm(row.get("scope_id"))
        if not key:
            continue
        readiness_by_scope.setdefault(key, row)

    recommendations_by_scope: Dict[str, List[Dict[str, Any]]] = {}
    for row in rec_rows:
        key = _norm(row.get("scope_id"))
        if not key:
            continue
        recommendations_by_scope.setdefault(key, []).append(row)

    campaign_ids = {_norm(c.get("campaign_id")) for c in campaign_rows if _norm(c.get("campaign_id"))}

    cluster_ids = {
        _norm(c.get("cluster_id") or c.get("scope_id") or c.get("id"))
        for c in cluster_rows
        if _norm(c.get("cluster_id") or c.get("scope_id") or c.get("id"))
    }

    patterns: List[Dict[str, Any]] = []
    seen_keys = set()

    # Primary pattern candidates come from outcomes to preserve actionable history.
    for row in out_rows:
        pattern_type = _scope_type(row)
        scope_id = _scope_id(row)
        scope_key = _norm(scope_id)
        if not scope_key:
            continue

        key = (pattern_type, scope_key)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        queue_row = queue_by_scope.get(scope_key, {})
        ready_row = readiness_by_scope.get(scope_key, {})
        rec_for_scope = recommendations_by_scope.get(scope_key, [])

        queue_state = _norm(queue_row.get("queue_state") or "new")
        readiness_state = _norm(ready_row.get("readiness_state") or "not_ready")
        weak_hits = len([r for r in rec_for_scope if _norm(r.get("confidence_level")) in {"low", "uncertain"}])

        severity_score = _safe_int(row.get("effectiveness"), 0)
        if _norm(row.get("outcome_label")) in {"reopened", "escalated"}:
            severity_score += 35
        alerts_count = _safe_int(alerts_by_scope.get(scope_key), 0)

        match_signals = [
            f"outcome:{_norm(row.get('outcome_label') or 'unknown')}",
            f"queue:{queue_state}",
            f"readiness:{readiness_state}",
            f"alerts:{alerts_count}",
        ]
        if rec_for_scope:
            match_signals.append(f"recommendations:{len(rec_for_scope)}")
        if _norm(scope_id) in campaign_ids:
            match_signals.append("campaign_linked")
        if _norm(scope_id) in cluster_ids:
            match_signals.append("cluster_linked")

        playbooks = []
        for rec in rec_for_scope[:4]:
            pb = str(rec.get("source_playbook") or rec.get("playbook_id") or "").strip()
            if pb and pb not in playbooks:
                playbooks.append(pb)

        if not playbooks:
            fallback = str(row.get("source_playbook") or row.get("source_action") or "baseline_followup").strip()
            playbooks.append(fallback or "baseline_followup")

        confidence_seed = 50
        confidence_seed += min(len(rec_for_scope) * 6, 20)
        confidence_seed += min(_safe_int(row.get("effectiveness"), 0) // 6, 15)
        if alerts_count > 0:
            confidence_seed += 5
        if readiness_state in {"ready_for_handoff", "ready_for_archive"}:
            confidence_seed += 8
        if weak_hits > 0:
            confidence_seed -= min(weak_hits * 10, 30)
        confidence_seed = max(15, min(confidence_seed, 95))

        patterns.append(
            {
                "pattern_id": f"pattern-{pattern_type}-{_slug(scope_id)}",
                "pattern_type": pattern_type,
                "title": f"Recurring {pattern_type} pattern ({scope_id})",
                "match_signals": match_signals[:8],
                "risk_profile": _risk_profile(
                    severity_score=severity_score,
                    alerts_count=alerts_count,
                    weak_hits=weak_hits,
                    queue_state=queue_state,
                ),
                "common_outcomes": [str(row.get("outcome_label") or "unknown")],
                "recommended_playbooks": playbooks[:4],
                "known_pitfalls": _pitfalls_for_type(pattern_type, weak_hits, queue_state, readiness_state),
                "confidence_level": _confidence_from_score(confidence_seed),
                "last_seen": str(row.get("created_at") or stamp),
            }
        )

    # Add minimal pattern memory for queue items with friction not captured by outcomes.
    for row in queue_rows:
        scope_id = str(row.get("item_id") or _scope_id(row)).strip()
        scope_key = _norm(scope_id)
        if not scope_key:
            continue
        key = ("queue_item", scope_key)
        if key in seen_keys:
            continue

        state = _norm(row.get("queue_state"))
        if state not in {"blocked", "waiting", "in_review"}:
            continue

        seen_keys.add(key)
        blockers = [str(x) for x in (row.get("blocking_factors") or []) if str(x).strip()]

        patterns.append(
            {
                "pattern_id": f"pattern-queue_item-{_slug(scope_id)}",
                "pattern_type": "queue_item",
                "title": f"Recurring queue friction ({scope_id})",
                "match_signals": [
                    f"queue:{state}",
                    f"blockers:{len(blockers)}",
                    f"journal_items_touched:{_safe_int(journal.get('items_touched'), 0)}",
                ],
                "risk_profile": "high" if state in {"blocked", "waiting"} else "medium",
                "common_outcomes": ["followup_required"],
                "recommended_playbooks": ["queue_unblock_routine"],
                "known_pitfalls": ["queue items can silently age without ownership"],
                "confidence_level": "medium",
                "last_seen": str(row.get("updated_at") or stamp),
            }
        )

    # Ensure coverage memory for campaign/cluster/evidence scopes when signals exist.
    for campaign in campaign_rows[:10]:
        cid = str(campaign.get("campaign_id") or "").strip()
        if not cid:
            continue
        key = ("campaign", _norm(cid))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        c_status = _norm(campaign.get("status") or "new")
        patterns.append(
            {
                "pattern_id": f"pattern-campaign-{_slug(cid)}",
                "pattern_type": "campaign",
                "title": f"Recurring campaign lifecycle ({cid})",
                "match_signals": [f"campaign:{c_status}", f"journal_campaigns:{_safe_int(journal.get('campaigns_updated'), 0)}"],
                "risk_profile": "high" if c_status in {"expanding", "new"} else "medium",
                "common_outcomes": ["campaign_monitoring"],
                "recommended_playbooks": ["campaign_stabilization"],
                "known_pitfalls": ["campaign state can drift without regular review"],
                "confidence_level": "medium",
                "last_seen": stamp,
            }
        )

    for cluster in cluster_rows[:10]:
        cl_id = str(cluster.get("cluster_id") or cluster.get("scope_id") or cluster.get("id") or "").strip()
        if not cl_id:
            continue
        key = ("cluster", _norm(cl_id))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        patterns.append(
            {
                "pattern_id": f"pattern-cluster-{_slug(cl_id)}",
                "pattern_type": "cluster",
                "title": f"Recurring cluster correlation ({cl_id})",
                "match_signals": ["cluster_correlation", f"journal_alerts:{_safe_int(journal.get('alerts_reviewed'), 0)}"],
                "risk_profile": "medium",
                "common_outcomes": ["cluster_review"],
                "recommended_playbooks": ["cluster_correlation_followup"],
                "known_pitfalls": ["cluster correlation may over-group transient devices"],
                "confidence_level": "medium",
                "last_seen": stamp,
            }
        )

    patterns.sort(
        key=lambda r: (
            {"high": 3, "medium": 2, "low": 1}.get(_norm(r.get("risk_profile")), 0),
            {"high": 3, "medium": 2, "low": 1}.get(_norm(r.get("confidence_level")), 0),
            str(r.get("last_seen", "")),
        ),
        reverse=True,
    )

    return patterns[:60]


def match_scopes_to_patterns(
    current_scopes: Optional[List[Dict[str, Any]]],
    patterns: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Lightweight matching of current scopes to known patterns."""
    scope_rows = list(current_scopes or [])
    pattern_rows = list(patterns or [])

    indexed: Dict[str, List[Dict[str, Any]]] = {}
    for p in pattern_rows:
        t = _norm(p.get("pattern_type"))
        if not t:
            continue
        indexed.setdefault(t, []).append(p)

    matches: List[Dict[str, Any]] = []

    for scope in scope_rows:
        scope_type = _scope_type(scope)
        scope_id = _scope_id(scope)
        scope_key = _norm(scope_id)
        if not scope_key:
            continue

        for pattern in indexed.get(scope_type, []):
            pid = _norm(pattern.get("pattern_id"))
            signals = [str(x) for x in (pattern.get("match_signals") or [])]

            score = 0.0
            if scope_key and scope_key in pid:
                score += 0.65

            scope_state = _norm(scope.get("queue_state") or scope.get("readiness_state") or scope.get("status"))
            if scope_state and any(scope_state in _norm(sig) for sig in signals):
                score += 0.25

            if _norm(pattern.get("confidence_level")) == "high":
                score += 0.1
            elif _norm(pattern.get("confidence_level")) == "medium":
                score += 0.05

            if score < 0.5:
                continue

            matches.append(
                {
                    "scope_type": scope_type,
                    "scope_id": scope_id,
                    "pattern_id": str(pattern.get("pattern_id", "-")),
                    "pattern_title": str(pattern.get("title", "-")),
                    "match_score": round(score, 2),
                    "confidence_level": str(pattern.get("confidence_level", "low")),
                    "risk_profile": str(pattern.get("risk_profile", "low")),
                    "recommended_playbooks": list(pattern.get("recommended_playbooks", []) or [])[:3],
                }
            )

    matches.sort(
        key=lambda r: (
            _safe_float(r.get("match_score"), 0.0),
            {"high": 3, "medium": 2, "low": 1}.get(_norm(r.get("confidence_level")), 0),
        ),
        reverse=True,
    )
    return matches[:30]


def summarize_operator_pattern_library(
    patterns: Optional[List[Dict[str, Any]]] = None,
    *,
    matches: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Prepare compact dashboard sections for pattern library panel."""
    rows = list(patterns or [])
    found_matches = list(matches or [])

    known_patterns = rows[:12]

    recurring_case_types: List[Dict[str, Any]] = []
    for p in rows:
        p_type = str(p.get("pattern_type", "device"))
        recurring_case_types.append(
            {
                "pattern_type": p_type,
                "title": str(p.get("title", "-")),
                "risk_profile": str(p.get("risk_profile", "low")),
                "confidence_level": str(p.get("confidence_level", "low")),
            }
        )

    likely_matches = found_matches[:10]

    pattern_based_guidance: List[str] = []
    for m in likely_matches[:6]:
        playbooks = m.get("recommended_playbooks", []) or []
        playbook_hint = playbooks[0] if playbooks else "manual_review"
        pattern_based_guidance.append(
            f"{m.get('scope_type', 'scope')}:{m.get('scope_id', '-')} -> {m.get('pattern_id', '-')} | use {playbook_hint}"
        )

    if not pattern_based_guidance and known_patterns:
        for p in known_patterns[:4]:
            playbooks = p.get("recommended_playbooks", []) or []
            playbook_hint = playbooks[0] if playbooks else "manual_review"
            pattern_based_guidance.append(f"{p.get('pattern_id', '-')} | prefer {playbook_hint}")

    return {
        "known_patterns": known_patterns,
        "recurring_case_types": recurring_case_types[:10],
        "likely_matches": likely_matches,
        "pattern_based_guidance": pattern_based_guidance[:10],
    }
