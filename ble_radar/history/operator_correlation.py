"""Lightweight correlation cluster / campaign view system.

Builds compact operator-oriented correlation clusters from existing project
signals without heavy dependencies.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set


def _normalize_address(value: Any) -> str:
    return str(value or "").strip().upper()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _addr_set(rows: Optional[List[Dict[str, Any]]]) -> Set[str]:
    out: Set[str] = set()
    for row in rows or []:
        addr = _normalize_address(row.get("address"))
        if addr:
            out.add(addr)
    return out


def _triage_rank(bucket: str) -> int:
    b = str(bucket or "normal").strip().lower()
    return {
        "critical": 4,
        "review": 3,
        "watch": 2,
        "normal": 1,
    }.get(b, 1)


def _risk_label(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _signal_title(signal: str) -> str:
    labels = {
        "movement_overlap": "session movement overlap",
        "movement_score_trend": "movement score trend overlap",
        "triage_bucket_proximity": "triage bucket proximity",
        "triage_score_proximity": "triage score proximity",
        "investigation_context_link": "investigation workspace context link",
        "case_workflow_similarity": "case/workflow similarity",
        "timeline_proximity": "operator timeline proximity",
        "playbook_similarity": "playbook similarity",
        "alert_similarity": "operator alert similarity",
    }
    return labels.get(signal, signal)


def _build_contexts(
    addresses: List[str],
    *,
    movement: Optional[Dict[str, Any]] = None,
    triage_results: Optional[List[Dict[str, Any]]] = None,
    investigation_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
    watch_cases: Optional[Dict[str, Dict[str, Any]]] = None,
    workflow_summary: Optional[Dict[str, Any]] = None,
    timeline_by_address: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    playbook_recommendations: Optional[List[Dict[str, Any]]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    triage_by_addr = {
        _normalize_address(row.get("address")): row
        for row in (triage_results or [])
        if _normalize_address(row.get("address"))
    }

    inv_by_addr = {
        _normalize_address(addr): profile
        for addr, profile in (investigation_profiles or {}).items()
        if _normalize_address(addr)
    }

    playbook_by_addr = {
        _normalize_address(row.get("address")): row
        for row in (playbook_recommendations or [])
        if _normalize_address(row.get("address"))
    }

    alerts_by_addr: Dict[str, List[Dict[str, Any]]] = {}
    for row in (alerts or []):
        addr = _normalize_address(row.get("device_address") or row.get("address"))
        if not addr:
            continue
        alerts_by_addr.setdefault(addr, []).append(row)

    movement_new = _addr_set((movement or {}).get("new", []))
    movement_rec = _addr_set((movement or {}).get("recurring", []))
    movement_dis = _addr_set((movement or {}).get("disappeared", []))

    movement_delta_sign: Dict[str, int] = {}
    for row in (movement or {}).get("score_changes", []) or []:
        addr = _normalize_address(row.get("address"))
        if not addr:
            continue
        delta = _safe_int(row.get("delta"), 0)
        movement_delta_sign[addr] = 1 if delta > 0 else (-1 if delta < 0 else 0)

    wf_sets = {
        "open": _addr_set((workflow_summary or {}).get("open", [])),
        "investigating": _addr_set((workflow_summary or {}).get("investigating", [])),
        "needs_action": _addr_set((workflow_summary or {}).get("needs_action", [])),
        "resolved": _addr_set((workflow_summary or {}).get("resolved", [])),
    }

    contexts: Dict[str, Dict[str, Any]] = {}
    for addr in addresses:
        triage = triage_by_addr.get(addr, {})
        inv = inv_by_addr.get(addr, {})
        case_record = (watch_cases or {}).get(addr, {})
        case_status = str(case_record.get("status", "")).strip().lower()
        if not case_status:
            case_status = str((inv or {}).get("case", {}).get("status", "")).strip().lower()

        triage_score = _safe_int(triage.get("triage_score", (inv or {}).get("triage", {}).get("triage_score", 0)), 0)
        triage_bucket = str(triage.get("triage_bucket", (inv or {}).get("triage", {}).get("triage_bucket", "normal"))).strip().lower()

        movement_status = "unknown"
        if addr in movement_new:
            movement_status = "new"
        elif addr in movement_rec:
            movement_status = "recurring"
        elif addr in movement_dis:
            movement_status = "disappeared"

        workflow_tags: Set[str] = set()
        for tag, rows in wf_sets.items():
            if addr in rows:
                workflow_tags.add(tag)

        events = (timeline_by_address or {}).get(addr, []) or []
        timeline_actions = {
            str(e.get("action", "")).strip().lower()
            for e in events
            if str(e.get("action", "")).strip()
        }

        playbook = playbook_by_addr.get(addr, {})
        playbook_id = str(playbook.get("playbook_id", "")).strip().lower()
        playbook_priority = str(playbook.get("priority", "")).strip().lower()

        alert_rows = alerts_by_addr.get(addr, [])
        alert_severities = {
            str(a.get("severity", "")).strip().lower()
            for a in alert_rows
            if str(a.get("severity", "")).strip()
        }

        contexts[addr] = {
            "address": addr,
            "triage_score": triage_score,
            "triage_bucket": triage_bucket,
            "movement_status": movement_status,
            "movement_delta_sign": movement_delta_sign.get(addr, 0),
            "case_status": case_status,
            "workflow_tags": workflow_tags,
            "timeline_actions": timeline_actions,
            "playbook_id": playbook_id,
            "playbook_priority": playbook_priority,
            "alert_severities": alert_severities,
            "is_investigation_focus": bool(inv),
        }

    return contexts


def _pair_signals(a: Dict[str, Any], b: Dict[str, Any]) -> List[str]:
    signals: List[str] = []

    if a["movement_status"] != "unknown" and a["movement_status"] == b["movement_status"]:
        signals.append("movement_overlap")

    if a["movement_delta_sign"] != 0 and a["movement_delta_sign"] == b["movement_delta_sign"]:
        signals.append("movement_score_trend")

    if a["triage_bucket"] == b["triage_bucket"]:
        signals.append("triage_bucket_proximity")

    if abs(_safe_int(a["triage_score"]) - _safe_int(b["triage_score"])) <= 10:
        signals.append("triage_score_proximity")

    if a["is_investigation_focus"] or b["is_investigation_focus"]:
        if a["triage_bucket"] == b["triage_bucket"] or (
            a["case_status"] and a["case_status"] == b["case_status"]
        ):
            signals.append("investigation_context_link")

    workflow_overlap = set(a["workflow_tags"]).intersection(set(b["workflow_tags"]))
    if workflow_overlap or (a["case_status"] and a["case_status"] == b["case_status"]):
        signals.append("case_workflow_similarity")

    if set(a["timeline_actions"]).intersection(set(b["timeline_actions"])):
        signals.append("timeline_proximity")

    if a["playbook_id"] and a["playbook_id"] == b["playbook_id"]:
        signals.append("playbook_similarity")
    elif a["playbook_priority"] and a["playbook_priority"] == b["playbook_priority"]:
        signals.append("playbook_similarity")

    if set(a["alert_severities"]).intersection(set(b["alert_severities"])):
        signals.append("alert_similarity")

    return signals


def _component_graph(edges: Dict[str, Set[str]], addresses: List[str]) -> List[List[str]]:
    seen: Set[str] = set()
    components: List[List[str]] = []

    for addr in addresses:
        if addr in seen:
            continue
        stack = [addr]
        comp: List[str] = []
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            comp.append(node)
            for nxt in edges.get(node, set()):
                if nxt not in seen:
                    stack.append(nxt)
        if len(comp) > 1:
            components.append(sorted(comp))

    return components


def build_correlation_clusters(
    devices: Optional[List[Dict[str, Any]]] = None,
    *,
    movement: Optional[Dict[str, Any]] = None,
    triage_results: Optional[List[Dict[str, Any]]] = None,
    investigation_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
    watch_cases: Optional[Dict[str, Dict[str, Any]]] = None,
    workflow_summary: Optional[Dict[str, Any]] = None,
    timeline_by_address: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    playbook_recommendations: Optional[List[Dict[str, Any]]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Build compact correlation clusters from existing operator signals."""
    candidate_addresses: List[str] = []

    for row in (triage_results or [])[:8]:
        addr = _normalize_address(row.get("address"))
        if addr and addr not in candidate_addresses:
            candidate_addresses.append(addr)

    for row in (devices or [])[:12]:
        addr = _normalize_address(row.get("address"))
        if addr and addr not in candidate_addresses:
            candidate_addresses.append(addr)

    if len(candidate_addresses) < 2:
        return []

    ctx = _build_contexts(
        candidate_addresses,
        movement=movement,
        triage_results=triage_results,
        investigation_profiles=investigation_profiles,
        watch_cases=watch_cases,
        workflow_summary=workflow_summary,
        timeline_by_address=timeline_by_address,
        playbook_recommendations=playbook_recommendations,
        alerts=alerts,
    )

    edges: Dict[str, Set[str]] = {a: set() for a in candidate_addresses}
    pair_signal_map: Dict[tuple[str, str], List[str]] = {}

    for i, a in enumerate(candidate_addresses):
        for b in candidate_addresses[i + 1:]:
            signals = _pair_signals(ctx[a], ctx[b])
            if len(signals) >= 2:
                edges[a].add(b)
                edges[b].add(a)
                pair_signal_map[(a, b)] = signals

    components = _component_graph(edges, candidate_addresses)
    clusters: List[Dict[str, Any]] = []

    for members in components:
        signal_counts: Dict[str, int] = {}
        max_triage = 0
        max_bucket_rank = 1
        sev_hits: Set[str] = set()

        for i, a in enumerate(members):
            c = ctx[a]
            max_triage = max(max_triage, _safe_int(c["triage_score"], 0))
            max_bucket_rank = max(max_bucket_rank, _triage_rank(c["triage_bucket"]))
            sev_hits.update(c.get("alert_severities", set()))

            for b in members[i + 1:]:
                key = (a, b) if (a, b) in pair_signal_map else (b, a)
                for s in pair_signal_map.get(key, []):
                    signal_counts[s] = signal_counts.get(s, 0) + 1

        top_signal_keys = [
            s for s, _ in sorted(
                signal_counts.items(),
                key=lambda x: (-x[1], x[0]),
            )[:4]
        ]
        top_signals = [_signal_title(s) for s in top_signal_keys]

        risk_score = max_triage + (max_bucket_rank * 8) + (len(members) * 4)
        if "critical" in sev_hits:
            risk_score += 12
        elif "high" in sev_hits:
            risk_score += 8

        risk_level = _risk_label(risk_score)

        reason_summary = " | ".join(top_signals) if top_signals else "shared operator signals"

        if risk_level == "critical":
            followup = "Immediate cluster review and coordinated incident escalation"
        elif risk_level == "high":
            followup = "Review as possible coordinated campaign and validate links"
        elif risk_level == "medium":
            followup = "Confirm shared signals and keep under active monitoring"
        else:
            followup = "Keep this cluster in watch mode and enrich context"

        cluster_id = f"cluster-{members[0].replace(':', '').lower()}-{len(members)}"

        clusters.append(
            {
                "cluster_id": cluster_id,
                "member_addresses": members,
                "member_count": len(members),
                "reason_summary": reason_summary,
                "risk_level": risk_level,
                "top_signals": top_signals,
                "recommended_followup": followup,
            }
        )

    clusters.sort(
        key=lambda c: (
            {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(str(c.get("risk_level", "low")).lower(), 1),
            _safe_int(c.get("member_count", 0), 0),
        ),
        reverse=True,
    )

    return clusters


def summarize_clusters(clusters: Optional[List[Dict[str, Any]]] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Build compact dashboard groups for cluster/campaign panel."""
    rows = list(clusters or [])
    top = rows[:5]

    coordinated = [
        r for r in rows
        if _safe_int(r.get("member_count", 0), 0) >= 3
        or str(r.get("risk_level", "")).lower() in {"critical", "high"}
    ][:5]

    needs_review = [
        r for r in rows
        if str(r.get("risk_level", "")).lower() in {"critical", "high"}
        or "case/workflow similarity" in [str(x).lower() for x in r.get("top_signals", [])]
    ][:5]

    return {
        "top_correlation_clusters": top,
        "possible_coordinated_devices": coordinated,
        "needs_cluster_review": needs_review,
    }
