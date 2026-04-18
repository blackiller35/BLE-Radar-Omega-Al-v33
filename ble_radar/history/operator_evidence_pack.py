"""Lightweight evidence pack / consolidated operator dossier system.

Builds compact evidence packs for device, case, cluster, and campaign scopes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ble_radar.config import HISTORY_DIR
from ble_radar.state import load_json, save_json

EVIDENCE_PACK_LOG_FILE = HISTORY_DIR / "operator_evidence_packs.json"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _norm_address(value: Any) -> str:
    return str(value or "").strip().upper()


def _risk_rank(value: Any) -> int:
    return {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }.get(str(value or "low").strip().lower(), 1)


def _risk_label(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _build_pack_id(scope_type: str, scope_id: str, generated_at: str) -> str:
    token = generated_at.replace(" ", "_").replace(":", "").replace("-", "")
    sid = str(scope_id or "unknown").replace(":", "").replace("/", "-").lower()
    return f"pack-{scope_type}-{sid}-{token}"


def load_evidence_packs(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load persisted evidence packs."""
    rows = load_json(EVIDENCE_PACK_LOG_FILE, [])
    packs = rows if isinstance(rows, list) else []
    if isinstance(limit, int) and limit >= 0:
        packs = packs[-limit:]
    return packs


def save_evidence_packs(packs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Persist evidence packs."""
    save_json(EVIDENCE_PACK_LOG_FILE, packs)
    return packs


def _pick_artifacts(
    artifact_index: Optional[Dict[str, Any]],
    *,
    include_incident: bool = False,
) -> List[str]:
    idx = artifact_index or {}
    out = []

    manifest_latest = (idx.get("scan_manifests") or {}).get("latest")
    diff_latest = (idx.get("session_diff_reports") or {}).get("latest")
    export_latest = (idx.get("export_contexts") or {}).get("latest")
    incident_latest = (idx.get("incident_packs") or {}).get("latest")

    if manifest_latest:
        out.append(str(manifest_latest))
    if diff_latest:
        out.append(str(diff_latest))
    if export_latest:
        out.append(str(export_latest))
    if include_incident and incident_latest:
        out.append(str(incident_latest))

    return out[:5]


def _timeline_snippets(events: Optional[List[Dict[str, Any]]], limit: int = 4) -> List[str]:
    rows = []
    for e in events or []:
        src = str(e.get("source", "?")).strip()
        summary = str(e.get("summary", "-")).strip()
        if summary:
            rows.append(f"{src}: {summary}")
    return rows[:limit]


def _alerts_summary(alerts: Optional[List[Dict[str, Any]]], addresses: Optional[List[str]] = None) -> str:
    rows = list(alerts or [])
    if addresses:
        addr_set = {_norm_address(a) for a in addresses if _norm_address(a)}
        rows = [
            a for a in rows
            if _norm_address(a.get("device_address") or a.get("address")) in addr_set
        ]

    if not rows:
        return "No active alerts in scope"

    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for r in rows:
        sev = str(r.get("severity", "low")).strip().lower()
        if sev not in sev_counts:
            sev = "low"
        sev_counts[sev] += 1

    return (
        f"critical={sev_counts['critical']} | high={sev_counts['high']} | "
        f"medium={sev_counts['medium']} | low={sev_counts['low']}"
    )


def _base_pack(
    *,
    scope_type: str,
    scope_id: str,
    generated_at: Optional[str],
    summary: str,
    key_findings: List[str],
    risk_level: str,
    timeline_highlights: List[str],
    alerts_summary: str,
    recommended_followup: str,
    included_artifacts: List[str],
) -> Dict[str, Any]:
    ts = str(generated_at or _now())
    return {
        "pack_id": _build_pack_id(scope_type, scope_id, ts),
        "scope_type": scope_type,
        "scope_id": scope_id,
        "generated_at": ts,
        "summary": summary,
        "key_findings": key_findings[:8],
        "risk_level": risk_level,
        "timeline_highlights": timeline_highlights[:6],
        "alerts_summary": alerts_summary,
        "recommended_followup": recommended_followup,
        "included_artifacts": included_artifacts[:6],
    }


def build_device_evidence_pack(
    scope_id: str,
    *,
    investigation_profile: Optional[Dict[str, Any]] = None,
    case_record: Optional[Dict[str, Any]] = None,
    timeline_events: Optional[List[Dict[str, Any]]] = None,
    playbook_recommendation: Optional[Dict[str, Any]] = None,
    rule_summary: Optional[Dict[str, Any]] = None,
    briefing: Optional[Dict[str, Any]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
    artifact_index: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    addr = _norm_address(scope_id)
    triage = (investigation_profile or {}).get("triage", {})
    triage_score = _safe_int(triage.get("triage_score", 0), 0)
    triage_bucket = str(triage.get("triage_bucket", "normal"))
    case_status = str((case_record or {}).get("status", (investigation_profile or {}).get("case", {}).get("status", "none")))

    playbook_id = str((playbook_recommendation or {}).get("playbook_id", "none"))
    auto_count = len((rule_summary or {}).get("auto_applied", [])) if isinstance(rule_summary, dict) else 0
    pending_count = len((rule_summary or {}).get("pending_confirmations", [])) if isinstance(rule_summary, dict) else 0

    findings = [
        f"Triage {triage_bucket}:{triage_score}",
        f"Case status={case_status}",
        f"Playbook={playbook_id}",
        f"Auto-actions={auto_count}",
        f"Pending confirmations={pending_count}",
    ]
    if briefing:
        findings.append(f"Briefing priorities={len(briefing.get('top_priorities', []))}")

    risk_score = triage_score + (_risk_rank(triage_bucket) * 8) + (pending_count * 5)
    risk_level = _risk_label(risk_score)

    return _base_pack(
        scope_type="device",
        scope_id=addr,
        generated_at=generated_at,
        summary=f"Device dossier for {addr}",
        key_findings=findings,
        risk_level=risk_level,
        timeline_highlights=_timeline_snippets(timeline_events),
        alerts_summary=_alerts_summary(alerts, [addr]),
        recommended_followup=str((playbook_recommendation or {}).get("recommended_action", "Review device evidence and update case notes")),
        included_artifacts=_pick_artifacts(artifact_index),
    )


def build_case_evidence_pack(
    scope_id: str,
    *,
    case_record: Optional[Dict[str, Any]] = None,
    workflow_summary: Optional[Dict[str, Any]] = None,
    investigation_profile: Optional[Dict[str, Any]] = None,
    timeline_events: Optional[List[Dict[str, Any]]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
    artifact_index: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    status = str((case_record or {}).get("status", "none"))
    triage = (investigation_profile or {}).get("triage", {})
    triage_score = _safe_int(triage.get("triage_score", 0), 0)
    needs_action = len((workflow_summary or {}).get("needs_action", [])) if isinstance(workflow_summary, dict) else 0

    risk_score = triage_score + (8 if status in {"investigating", "review"} else 0) + min(needs_action, 5)

    findings = [
        f"Case status={status}",
        f"Workflow needs_action={needs_action}",
        f"Triage score={triage_score}",
    ]

    return _base_pack(
        scope_type="case",
        scope_id=str(scope_id),
        generated_at=generated_at,
        summary=f"Case dossier for {scope_id}",
        key_findings=findings,
        risk_level=_risk_label(risk_score),
        timeline_highlights=_timeline_snippets(timeline_events),
        alerts_summary=_alerts_summary(alerts),
        recommended_followup="Review case workflow transitions and confirm next operator action",
        included_artifacts=_pick_artifacts(artifact_index, include_incident=True),
    )


def build_cluster_evidence_pack(
    scope_id: str,
    *,
    cluster_record: Optional[Dict[str, Any]] = None,
    timeline_by_address: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    playbook_recommendations: Optional[List[Dict[str, Any]]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
    campaign_rows: Optional[List[Dict[str, Any]]] = None,
    artifact_index: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    cluster = cluster_record or {}
    members = [
        _norm_address(a)
        for a in cluster.get("member_addresses", [])
        if _norm_address(a)
    ]
    top_signals = [str(s) for s in cluster.get("top_signals", [])]

    timeline_hl = []
    for addr in members[:3]:
        timeline_hl.extend(_timeline_snippets((timeline_by_address or {}).get(addr, []), limit=2))

    playbook_ids = {
        str(r.get("playbook_id", "")).strip()
        for r in (playbook_recommendations or [])
        if _norm_address(r.get("address")) in set(members)
    }
    playbook_ids.discard("")

    related_campaigns = [
        c for c in (campaign_rows or [])
        if set(_norm_address(a) for a in c.get("member_addresses", [])).intersection(set(members))
    ]

    findings = [
        f"Members={len(members)}",
        f"Top signals={', '.join(top_signals[:3]) or 'none'}",
        f"Playbooks in scope={len(playbook_ids)}",
        f"Linked campaigns={len(related_campaigns)}",
    ]

    risk_rank = max(_risk_rank(cluster.get("risk_level", "low")), 1)
    risk_score = (risk_rank * 20) + min(len(members) * 4, 20) + min(len(top_signals) * 3, 12)

    return _base_pack(
        scope_type="cluster",
        scope_id=str(scope_id),
        generated_at=generated_at,
        summary=f"Cluster dossier for {scope_id}",
        key_findings=findings,
        risk_level=_risk_label(risk_score),
        timeline_highlights=timeline_hl,
        alerts_summary=_alerts_summary(alerts, members),
        recommended_followup=str(cluster.get("recommended_followup", "Validate cluster coordination hypothesis")),
        included_artifacts=_pick_artifacts(artifact_index, include_incident=True),
    )


def build_campaign_evidence_pack(
    scope_id: str,
    *,
    campaign_record: Optional[Dict[str, Any]] = None,
    clusters: Optional[List[Dict[str, Any]]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
    briefing: Optional[Dict[str, Any]] = None,
    artifact_index: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    campaign = campaign_record or {}
    members = [
        _norm_address(a)
        for a in campaign.get("member_addresses", [])
        if _norm_address(a)
    ]
    status = str(campaign.get("status", "new"))
    trend = str(campaign.get("activity_trend", "flat"))

    linked_clusters = [
        c for c in (clusters or [])
        if set(_norm_address(a) for a in c.get("member_addresses", [])).intersection(set(members))
    ]

    findings = [
        f"Campaign status={status}",
        f"Activity trend={trend}",
        f"Members={len(members)}",
        f"Linked clusters={len(linked_clusters)}",
    ]
    if briefing:
        findings.append(f"Briefing suggested steps={len(briefing.get('suggested_next_steps', []))}")

    risk_score = (_risk_rank(campaign.get("risk_level", "low")) * 20) + (8 if status in {"new", "expanding"} else 0)

    return _base_pack(
        scope_type="campaign",
        scope_id=str(scope_id),
        generated_at=generated_at,
        summary=f"Campaign dossier for {scope_id}",
        key_findings=findings,
        risk_level=_risk_label(risk_score),
        timeline_highlights=[],
        alerts_summary=_alerts_summary(alerts, members),
        recommended_followup=str(campaign.get("recommended_followup", "Review campaign lifecycle and escalation readiness")),
        included_artifacts=_pick_artifacts(artifact_index, include_incident=True),
    )


def build_evidence_packs(
    *,
    focus_address: Optional[str] = None,
    watch_cases: Optional[Dict[str, Dict[str, Any]]] = None,
    investigation_profile: Optional[Dict[str, Any]] = None,
    workflow_summary: Optional[Dict[str, Any]] = None,
    timeline_events: Optional[List[Dict[str, Any]]] = None,
    playbook_recommendations: Optional[List[Dict[str, Any]]] = None,
    rule_summary: Optional[Dict[str, Any]] = None,
    briefing: Optional[Dict[str, Any]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
    clusters: Optional[List[Dict[str, Any]]] = None,
    campaigns: Optional[List[Dict[str, Any]]] = None,
    artifact_index: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
    persist: bool = False,
) -> List[Dict[str, Any]]:
    """Build compact evidence packs for device/case/cluster/campaign scopes."""
    ts = str(generated_at or _now())
    packs: List[Dict[str, Any]] = []

    if focus_address:
        addr = _norm_address(focus_address)
        case_record = (watch_cases or {}).get(addr, {})
        playbook_rec = next(
            (r for r in (playbook_recommendations or []) if _norm_address(r.get("address")) == addr),
            None,
        )

        packs.append(
            build_device_evidence_pack(
                addr,
                investigation_profile=investigation_profile,
                case_record=case_record,
                timeline_events=timeline_events,
                playbook_recommendation=playbook_rec,
                rule_summary=rule_summary,
                briefing=briefing,
                alerts=alerts,
                artifact_index=artifact_index,
                generated_at=ts,
            )
        )

        packs.append(
            build_case_evidence_pack(
                addr,
                case_record=case_record,
                workflow_summary=workflow_summary,
                investigation_profile=investigation_profile,
                timeline_events=timeline_events,
                alerts=alerts,
                artifact_index=artifact_index,
                generated_at=ts,
            )
        )

    if clusters:
        cluster = clusters[0]
        packs.append(
            build_cluster_evidence_pack(
                str(cluster.get("cluster_id", "cluster-unknown")),
                cluster_record=cluster,
                timeline_by_address={_norm_address(focus_address): timeline_events or []} if focus_address else {},
                playbook_recommendations=playbook_recommendations,
                alerts=alerts,
                campaign_rows=campaigns,
                artifact_index=artifact_index,
                generated_at=ts,
            )
        )

    if campaigns:
        campaign = campaigns[0]
        packs.append(
            build_campaign_evidence_pack(
                str(campaign.get("campaign_id", "campaign-unknown")),
                campaign_record=campaign,
                clusters=clusters,
                alerts=alerts,
                briefing=briefing,
                artifact_index=artifact_index,
                generated_at=ts,
            )
        )

    if persist and packs:
        try:
            prior = load_evidence_packs()
            merged = (prior + packs)[-160:]
            save_evidence_packs(merged)
        except Exception:
            pass

    return packs


def summarize_evidence_packs(
    packs: Optional[List[Dict[str, Any]]] = None,
    persisted_packs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Build compact dashboard groups for operator dossier panel."""
    current = list(packs or [])
    history = list(persisted_packs or [])

    recent = (history + current)[-8:]

    ready_for_review = [
        p for p in current
        if str(p.get("risk_level", "")).lower() in {"critical", "high"}
        or str(p.get("scope_type", "")).lower() in {"cluster", "campaign"}
    ][:8]

    campaign_summary = [
        p for p in recent
        if str(p.get("scope_type", "")).lower() == "campaign"
    ][:8]

    return {
        "recent_evidence_packs": recent,
        "ready_for_review_dossiers": ready_for_review,
        "campaign_evidence_summary": campaign_summary,
    }
