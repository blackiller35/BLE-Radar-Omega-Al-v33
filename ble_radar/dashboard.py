import json
from ble_radar.alert_history import get_recent_alerts
from ble_radar.bluehood_layer import enrich_devices_for_session
from datetime import datetime
from html import escape

from ble_radar.device_contract import explain_device, normalize_device
from ble_radar.intel import get_tracker_candidates, get_vendor_summary
from ble_radar.intel.omega_intel_map import build_omega_intel_maps
from ble_radar.investigation import list_cases
from ble_radar.session_diff import latest_session_diff
from ble_radar.session_catalog import build_session_catalog, latest_session_overview
from ble_radar.artifact_index import build_artifact_index
from ble_radar.history.device_registry import load_registry
from ble_radar.history.device_scoring import compute_device_score
from ble_radar.history.cases import load_cases as load_watch_cases
from ble_radar.history.case_workflow import case_workflow_summary, next_action
from ble_radar.history.investigation_workspace import build_investigation_profile
from ble_radar.history.operator_alerting import (
    build_operator_alerts,
    load_alert_log,
    summarize_alerts,
)
from ble_radar.history.operator_briefing import build_operator_briefing
from ble_radar.history.operator_campaign_tracking import (
    build_campaign_lifecycle,
    load_campaign_records,
    summarize_campaigns,
)
from ble_radar.history.operator_closure_package import (
    build_operator_closure_packages,
    summarize_operator_closure_packages,
)
from ble_radar.history.operator_post_closure_monitoring_policy import (
    build_operator_post_closure_monitoring_policies,
    summarize_operator_post_closure_monitoring_policies,
)
from ble_radar.history.operator_reopen_policy import (
    build_operator_reopen_records,
    summarize_operator_reopen_records,
)
from ble_radar.history.operator_lifecycle_lineage import (
    build_operator_lifecycle_lineage_records,
    summarize_operator_lifecycle_lineage,
)
from ble_radar.history.operator_resolution_quality import (
    build_operator_resolution_quality_records,
    summarize_operator_resolution_quality,
)
from ble_radar.history.operator_improvement_plan import (
    build_operator_improvement_plan_records,
    summarize_operator_improvement_plans,
)
from ble_radar.history.operator_outcome_learning import (
    build_operator_outcome_learning_records,
    summarize_operator_outcome_learning,
)
from ble_radar.history.operator_correlation import (
    build_correlation_clusters,
    summarize_clusters,
)
from ble_radar.history.operator_evidence_pack import (
    build_evidence_packs,
    load_evidence_packs,
    summarize_evidence_packs,
)
from ble_radar.history.operator_escalation_feedback import (
    build_operator_escalation_feedback_records,
    summarize_operator_escalation_feedback,
)
from ble_radar.history.operator_escalation_package import (
    build_operator_escalation_packages,
    summarize_operator_escalation_packages,
)
from ble_radar.history.operator_outcomes import (
    build_operator_outcomes,
    summarize_operator_outcomes,
)
from ble_radar.history.operator_pattern_library import (
    build_operator_pattern_records,
    match_scopes_to_patterns,
    summarize_operator_pattern_library,
)
from ble_radar.history.operator_playbook import recommend_operator_playbook
from ble_radar.history.operator_queue import (
    build_operator_queue,
    summarize_operator_queue,
)
from ble_radar.history.operator_queue_health import (
    build_queue_health_snapshot,
    summarize_queue_health,
)
from ble_radar.history.operator_session_journal import (
    build_operator_session_journal,
    summarize_operator_session_journal,
)
from ble_radar.history.recommendation_tuning import (
    build_recommendation_tuning_profiles,
    summarize_recommendation_tuning_profiles,
)
from ble_radar.history.review_readiness import (
    build_review_readiness_profiles,
    summarize_review_readiness,
)
from ble_radar.history.operator_rule_engine import (
    evaluate_operator_rules,
    load_automation_events,
    summarize_rule_results,
)
from ble_radar.history.operator_timeline import (
    build_operator_timeline,
    recent_timeline_events,
)
from ble_radar.history.triage import triage_device_list
from ble_radar.eventlog import read_events
from ble_radar.session.session_movement import build_session_movement
from ble_radar.security import build_security_context
from ble_radar.state import load_last_scan, load_scan_history
from pathlib import Path
from ble_radar.intel.risk_tags import build_risk_tags, risk_level_from_tags
from ble_radar.intel.ble_fingerprint import classify_ble_device


def load_pcap_intel() -> list[dict]:
    path = Path("reports/pcap_intel_summary.json")
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload.get("devices", [])
    except Exception:
        return []




def omega_intel_map_to_core_row(ctx: dict) -> dict:
    """Adapt OMEGA Intel Map output to OMEGA Core dashboard row."""
    risk_level = str(ctx.get("risk", {}).get("level", "low")).lower()

    confidence_by_level = {
        "high": 0.92,
        "medium": 0.68,
        "low": 0.35,
    }

    return {
        "name": ctx.get("identity", {}).get("name", "Unknown"),
        "address": ctx.get("identity", {}).get("address", ""),
        "threat_level": risk_level,
        "confidence": confidence_by_level.get(risk_level, 0.35),
        "has_live_alert": risk_level == "high",
    }



def render_omega_core_panel(rows: list[dict]) -> str:
    """Render a safe OMEGA CORE panel without touching dashboard flow."""
    if not rows:
        return '<div class="muted">No OMEGA CORE data.</div>'

    cards = []
    for row in rows[:10]:
        level = escape(str(row.get("threat_level", "low")).lower())
        name = escape(str(row.get("name", "Unknown")))
        address = escape(str(row.get("address", "")))
        confidence = round(float(row.get("confidence", 0)) * 100, 2)
        live = "YES" if row.get("has_live_alert") else "NO"

        cards.append(f"""
        <div class="card omega-core-card level-{level}">
            <strong>{name}</strong><br>
            <code>{address}</code><br>
            <small>
            Level: {level.upper()} |
            Confidence: {confidence}% |
            Live: {live}
            </small>
        </div>
        """)

    return "\n".join(cards)



def render_ble_intel_panel(devices: list[dict]) -> str:
    if not devices:
        return '<div class="omega-empty">No BLE intel data.</div>'

    rows = []

    for device in devices[:10]:
        fingerprint = classify_ble_device(device)
        device["omega_category"] = fingerprint["category"]
        device["omega_tags"] = fingerprint["tags"]
        device["omega_confidence"] = fingerprint["confidence"]
        device["omega_summary"] = fingerprint["summary"]

        address = escape(str(device.get("address", "?"))).upper()
        hits = int(device.get("hits", 0) or 0)

        tags = build_risk_tags(device)
        level = risk_level_from_tags(tags)

        tags_html = (
            " ".join(
                f'<span class="omega-tag omega-tag-{level}">{escape(tag)}</span>'
                for tag in tags
            )
            or '<span class="muted">No tags</span>'
        )

        omega_tags_html = " ".join(
            f'<span class="omega-tag omega-tag-{level}">{escape(tag)}</span>'
            for tag in device.get("omega_tags", [])
        ) or '<span class="muted">No OMEGA tags</span>'

        rows.append(f"""
        <article class="omega-event level-{level}">
            <strong>{address}</strong><br>
            Hits: {hits}<br>
            <div class="risk-tags">{tags_html}</div>
            <div class="omega-summary">
                <strong>OMEGA:</strong> {escape(str(device.get("omega_category", "unknown_ble")))}
                | confidence={escape(str(device.get("omega_confidence", 0)))}%
            </div>
            <div class="risk-tags">{omega_tags_html}</div>
            <div class="muted">{escape(str(device.get("omega_summary", "")))}</div>
        </article>
        """)


    return "\n".join(rows)


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _delta_label(current: int, previous) -> str:
    if previous is None:
        return "n/a"
    diff = current - _safe_int(previous, 0)
    if diff > 0:
        return f"+{diff}"
    return str(diff)


def _parse_scan_stamp(value: str):
    if not value:
        return None
    for fmt in ("%Y-%m-%d_%H-%M-%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(value), fmt)
        except Exception:
            continue
    return None


def _device_behavior_flags(
    device: dict,
    registry_row: dict | None = None,
    observations: list[dict] | None = None,
) -> dict:
    """Return deterministic behavior flags based on local registry/history signals."""
    row = registry_row if isinstance(registry_row, dict) else {}
    obs = [o for o in (observations or []) if isinstance(o, dict)]

    seen_count = _safe_int(row.get("seen_count", 0), 0)
    recurring = seen_count >= 8
    seen_frequently = len(obs) >= 4

    names = [
        str(o.get("name", "")).strip() for o in obs if str(o.get("name", "")).strip()
    ]
    current_name = str(device.get("name", "")).strip()
    if current_name:
        names.append(current_name)
    unique_names = {name for name in names if name and name.lower() != "inconnu"}
    name_changed = len(unique_names) >= 2

    rssis = []
    for o in obs:
        value = o.get("rssi")
        if isinstance(value, (int, float)):
            rssis.append(int(value))
    current_rssi = device.get("rssi")
    if isinstance(current_rssi, (int, float)):
        rssis.append(int(current_rssi))
    unstable_signal = len(rssis) >= 3 and (max(rssis) - min(rssis)) >= 18

    positions = sorted(
        {
            _safe_int(o.get("scan_pos"), -1)
            for o in obs
            if _safe_int(o.get("scan_pos"), -1) >= 0
        }
    )
    recently_reappeared = len(positions) >= 2 and (positions[-1] - positions[-2]) >= 3

    return {
        "recurring": recurring,
        "seen_frequently": seen_frequently,
        "name_changed": name_changed,
        "unstable_signal": unstable_signal,
        "recently_reappeared": recently_reappeared,
    }


def build_compact_device_behavior_summary(
    device: dict,
    registry_row: dict | None = None,
    observations: list[dict] | None = None,
) -> str:
    """Build a compact deterministic behavior summary from local signals only."""
    flags = _device_behavior_flags(
        device, registry_row=registry_row, observations=observations
    )
    summaries = []

    if flags["recurring"]:
        summaries.append("Likely recurring device")

    if flags["seen_frequently"]:
        summaries.append("Seen frequently in recent scans")

    if flags["name_changed"]:
        summaries.append("Name changed recently")

    if flags["unstable_signal"]:
        summaries.append("Signal pattern unstable")

    if flags["recently_reappeared"]:
        summaries.append("Recently reappeared after absence")

    if not summaries:
        return ""
    return " | ".join(summaries[:3])


def compute_device_interest_score(
    device: dict,
    registry_row: dict | None = None,
    observations: list[dict] | None = None,
) -> dict:
    """Compute deterministic local risk/interest score from behavior + anomaly flags."""
    flags = _device_behavior_flags(
        device, registry_row=registry_row, observations=observations
    )
    base_score = 0
    if flags["recurring"]:
        base_score += 2
    if flags["name_changed"]:
        base_score += 2
    if flags["unstable_signal"]:
        base_score += 1
    if flags["recently_reappeared"]:
        base_score += 1

    anomaly_flags = detect_device_anomaly_flags(
        device,
        registry_row=registry_row,
        observations=observations,
    )
    anomaly_boost_map = {
        "NEW_DEVICE": 1,
        "NAME_CHANGE_SPIKE": 2,
        "REAPPEAR_ALERT": 2,
        "STABILITY_BREAK": 3,
    }
    anomaly_boost = sum(anomaly_boost_map.get(flag, 0) for flag in anomaly_flags)
    score = base_score + anomaly_boost

    if score <= 1:
        label = "normal"
    elif score <= 3:
        label = "interesting"
    else:
        label = "suspicious"

    return {
        "score": score,
        "label": label,
        "base_score": base_score,
        "anomaly_boost": anomaly_boost,
        "anomaly_flags": anomaly_flags,
    }


def detect_device_anomaly_flags(
    device: dict,
    registry_row: dict | None = None,
    observations: list[dict] | None = None,
) -> list[str]:
    """Return compact deterministic anomaly flags from local signals only."""
    row = registry_row if isinstance(registry_row, dict) else {}
    obs = [o for o in (observations or []) if isinstance(o, dict)]
    behavior = _device_behavior_flags(device, registry_row=row, observations=obs)

    seen_count = _safe_int(row.get("seen_count", 0), 0)
    first_seen = str(row.get("first_seen", "")).strip()
    last_seen = str(row.get("last_seen", "")).strip()

    flags = []

    # New profile: first observations only, no established recurrence yet.
    if seen_count <= 1 and len(obs) <= 1:
        flags.append("NEW_DEVICE")
    elif seen_count <= 2 and first_seen and last_seen and first_seen == last_seen:
        flags.append("NEW_DEVICE")

    # Stability break: unstable RSSI on an otherwise recurrent/frequent device.
    if behavior["unstable_signal"] and (
        behavior["recurring"] or behavior["seen_frequently"]
    ):
        flags.append("STABILITY_BREAK")

    names = [
        str(o.get("name", "")).strip() for o in obs if str(o.get("name", "")).strip()
    ]
    current_name = str(device.get("name", "")).strip()
    if current_name:
        names.append(current_name)
    normalized_names = [n for n in names if n and n.lower() != "inconnu"]
    unique_name_count = len(set(normalized_names))
    if behavior["name_changed"] and (unique_name_count >= 3 or len(obs) >= 3):
        flags.append("NAME_CHANGE_SPIKE")

    if behavior["recently_reappeared"]:
        flags.append("REAPPEAR_ALERT")

    return flags


def detect_device_live_alerts(
    device: dict,
    registry_row: dict | None = None,
    observations: list[dict] | None = None,
) -> list[str]:
    """Return compact deterministic live alerts from local anomaly/risk signals."""
    row = registry_row if isinstance(registry_row, dict) else {}
    obs = [o for o in (observations or []) if isinstance(o, dict)]

    current_flags = detect_device_anomaly_flags(
        device,
        registry_row=row,
        observations=obs,
    )
    score_info = compute_device_interest_score(
        device,
        registry_row=row,
        observations=obs,
    )

    previous_flags = []
    if obs:
        last = obs[-1]
        previous_device = dict(device)
        if last.get("name"):
            previous_device["name"] = last.get("name")
        if isinstance(last.get("rssi"), (int, float)):
            previous_device["rssi"] = last.get("rssi")
        previous_flags = detect_device_anomaly_flags(
            previous_device,
            registry_row=row,
            observations=obs[:-1],
        )

    newly_present = [flag for flag in current_flags if flag not in previous_flags]
    alerts = []

    if "NEW_DEVICE" in newly_present or (
        "NEW_DEVICE" in current_flags and len(obs) <= 1
    ):
        alerts.append("New device anomaly detected")

    if "STABILITY_BREAK" in newly_present or (
        "STABILITY_BREAK" in current_flags and len(obs) >= 3
    ):
        alerts.append("Device stability break detected")

    if "REAPPEAR_ALERT" in newly_present or "REAPPEAR_ALERT" in current_flags:
        alerts.append("Recently reappeared device flagged")

    if _safe_int(score_info.get("anomaly_boost", 0), 0) >= 3:
        alerts.append("Risk spike detected")

    if not alerts:
        return []
    return alerts[:3]


def build_compact_device_profile(
    device: dict,
    registry_row: dict | None = None,
    observations: list[dict] | None = None,
) -> dict:
    """Build a compact deterministic device profile from local history and analysis."""
    row = registry_row if isinstance(registry_row, dict) else {}
    obs = [o for o in (observations or []) if isinstance(o, dict)]
    behavior = _device_behavior_flags(device, registry_row=row, observations=obs)
    score_info = compute_device_interest_score(
        device,
        registry_row=row,
        observations=obs,
    )
    anomaly_flags = detect_device_anomaly_flags(
        device,
        registry_row=row,
        observations=obs,
    )

    total_sightings = _safe_int(row.get("seen_count", 0), 0)
    if total_sightings <= 0:
        total_sightings = len(obs)

    anomaly_count = len(anomaly_flags)
    last_risk = str(score_info.get("label", "normal"))

    if total_sightings >= 8 and anomaly_count == 0 and not behavior["unstable_signal"]:
        trust_level = "high"
    elif (
        total_sightings >= 3
        and anomaly_count <= 1
        and _safe_int(score_info.get("anomaly_boost", 0), 0) <= 1
    ):
        trust_level = "medium"
    else:
        trust_level = "low"

    return {
        "total_sightings": total_sightings,
        "anomaly_count": anomaly_count,
        "last_risk": last_risk,
        "trust_level": trust_level,
    }


def build_tracking_exposure_summary(
    device: dict,
    registry_row: dict | None = None,
    observations: list[dict] | None = None,
) -> dict:
    behavior = _device_behavior_flags(
        device,
        registry_row=registry_row,
        observations=observations,
    )
    interest = compute_device_interest_score(
        device,
        registry_row=registry_row,
        observations=observations,
    )
    anomalies = detect_device_anomaly_flags(
        device,
        registry_row=registry_row,
        observations=observations,
    )

    privacy_score = 0

    if behavior.get("recurring"):
        privacy_score += 2
    if behavior.get("seen_frequently"):
        privacy_score += 1
    if behavior.get("name_changed"):
        privacy_score += 2
    if behavior.get("unstable_signal"):
        privacy_score += 1
    if behavior.get("recently_reappeared"):
        privacy_score += 2

    if "REAPPEAR_ALERT" in anomalies:
        privacy_score += 1
    if "NAME_CHANGE_SPIKE" in anomalies:
        privacy_score += 1

    if privacy_score <= 1:
        level = "low"
    elif privacy_score <= 3:
        level = "medium"
    else:
        level = "high"

    tracking_exposure = "unlikely"
    if privacy_score >= 5:
        tracking_exposure = "probable"
    elif privacy_score >= 3:
        tracking_exposure = "possible"

    reasons = []
    if behavior.get("recurring"):
        reasons.append("recurring presence")
    if behavior.get("name_changed"):
        reasons.append("name churn")
    if behavior.get("unstable_signal"):
        reasons.append("unstable signal pattern")
    if behavior.get("recently_reappeared"):
        reasons.append("reappeared after absence")

    return {
        "privacy_score": privacy_score,
        "privacy_level": level,
        "tracking_exposure": tracking_exposure,
        "reasons": reasons[:4],
        "interest_label": interest.get("label", "normal"),
    }


_BUCKET_STYLE = {
    "critical": "color:var(--pink);font-weight:700",
    "review": "color:var(--red)",
    "watch": "color:var(--yellow)",
    "normal": "color:var(--green)",
}


def render_triage_panel(triage_results: list) -> str:
    """Render a compact HTML priority list from ``triage_device_list()`` output."""
    if not triage_results:
        return '<ul><li class="muted">Aucun appareil à trier.</li></ul>'

    top = triage_results[:15]
    items = []
    for r in top:
        bucket = r.get("triage_bucket", "normal")
        style = _BUCKET_STYLE.get(bucket, "")
        items.append(
            f'<li style="{style}">'
            f"[{escape(bucket.upper())}] "
            f"<code>{escape(str(r.get('address', '?')))}</code> "
            f"| {escape(str(r.get('name', 'Inconnu')))} "
            f"| score={escape(str(r.get('triage_score', 0)))} "
            f"| {escape(str(r.get('short_reason', '-')))}"
            f"</li>"
        )
    overflow = len(triage_results) - 15
    suffix = f'<li class="muted">… {overflow} de plus</li>' if overflow > 0 else ""
    return f"<ul>{''.join(items)}{suffix}</ul>"


def render_investigation_profile_panel(profile: dict | None) -> str:
    """Render a compact workspace view for one focused device address."""
    if not profile:
        return (
            '<ul><li class="muted">Aucun profil d\'investigation disponible.</li></ul>'
        )

    identity = profile.get("identity", {})
    registry = profile.get("registry", {})
    triage = profile.get("triage", {})
    case = profile.get("case", {})
    movement = profile.get("movement", {})
    refs = profile.get("incident_refs", {})
    lines = [
        f"<li><strong>Focus</strong>: {escape(str(identity.get('name', 'Inconnu')))} | <code>{escape(str(profile.get('address', '?')))}</code></li>",
        f"<li>Vendor={escape(str(identity.get('vendor', 'Unknown')))} | profile={escape(str(identity.get('profile', '-')))} | alert={escape(str(identity.get('alert_level', '-')))} | watch_hit={escape(str(identity.get('watch_hit', False)))}</li>",
        f"<li>Registry: seen={escape(str(registry.get('seen_count', 0)))} | sessions={escape(str(registry.get('session_count', 0)))} | score={escape(str(registry.get('registry_score', 0)))}</li>",
        f"<li>Triage: bucket={escape(str(triage.get('triage_bucket', '-')))} | score={escape(str(triage.get('triage_score', 0)))} | reason={escape(str(triage.get('short_reason', '-')))}</li>",
        f"<li>Case: status={escape(str(case.get('status', 'none')))} | reason={escape(str(case.get('reason', '-')))} | updated={escape(str(case.get('updated_at', '-')))}</li>",
        f"<li>Movement: status={escape(str(movement.get('status', 'unknown')))}"
        + (
            f" | score_delta={escape(str(movement.get('score_delta')))}"
            if movement.get("score_delta") is not None
            else ""
        )
        + "</li>",
    ]

    device_pack_refs = refs.get("device_packs", [])
    incident_pack_refs = refs.get("incident_packs", [])
    lines.append(
        f"<li>Device pack refs: {escape(', '.join(device_pack_refs) if device_pack_refs else 'none')}</li>"
    )
    lines.append(
        f"<li>Incident pack refs: {escape(', '.join(incident_pack_refs) if incident_pack_refs else 'none')}</li>"
    )
    return f"<ul>{''.join(lines)}</ul>"


def render_tracking_exposure_panel(rows: list[dict]) -> str:
    """Render compact tracking exposure / privacy risk rows."""
    if not rows:
        return '<ul><li class="muted">Aucune donnée privacy/tracking.</li></ul>'

    items = []
    for row in rows[:10]:
        reasons = ", ".join(row.get("reasons", [])) or "no strong signal"
        items.append(
            f"<li>"
            f"<code>{escape(str(row.get('address', '?')))}</code> | "
            f"{escape(str(row.get('name', 'Inconnu')))} | "
            f"privacy=<strong>{escape(str(row.get('privacy_level', 'low')).upper())}</strong> | "
            f"tracking={escape(str(row.get('tracking_exposure', 'unlikely')))} | "
            f"{escape(reasons)}"
            f"</li>"
        )
    return f"<ul>{''.join(items)}</ul>"


def render_case_workflow_panel(summary: dict) -> str:
    """Render a compact HTML panel for the operator case workflow."""
    if not summary or summary.get("total", 0) == 0:
        return '<ul><li class="muted">Aucun cas dans le workflow opérateur.</li></ul>'

    open_cases = summary.get("open", [])
    investigating = summary.get("investigating", [])
    needs_action = summary.get("needs_action", [])
    resolved = summary.get("resolved", [])

    lines = [
        f"<li>Cas ouverts : <strong>{len(open_cases)}</strong> | "
        f"En course d'investigation : <strong>{len(investigating)}</strong> | "
        f"Action requise : <strong>{len(needs_action)}</strong> | "
        f"Résolus récents : <strong>{len(resolved)}</strong></li>",
    ]

    if needs_action:
        rows = "".join(
            f"<li><code>{escape(str(r.get('address', '?')))}</code> "
            f"[<strong>{escape(str(r.get('status', 'new')))}</strong>] "
            f"— {escape(next_action(r))}"
            f"{(' | reason: ' + escape(str(r.get('reason', '')))) if r.get('reason') else ''}</li>"
            for r in needs_action[:5]
        )
        lines.append(f"<li>Action requise (top 5):<ul>{rows}</ul></li>")

    if investigating:
        rows = "".join(
            f"<li><code>{escape(str(r.get('address', '?')))}</code> "
            f"— {escape(next_action(r))}</li>"
            for r in investigating[:5]
        )
        lines.append(f"<li>En investigation (top 5):<ul>{rows}</ul></li>")

    if resolved:
        rows = "".join(
            f"<li><code>{escape(str(r.get('address', '?')))}</code> "
            f"updated={escape(str(r.get('updated_at', '-')))}</li>"
            for r in resolved[:3]
        )
        lines.append(f"<li>Récemment résolus:<ul>{rows}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_timeline_panel(events: list) -> str:
    """Render compact recent operator timeline events."""
    if not events:
        return '<ul><li class="muted">Aucun événement timeline disponible.</li></ul>'

    items = "".join(
        f'<li><span class="muted">{escape(str(e.get("timestamp") or "n/a"))}</span> | '
        f"<strong>{escape(str(e.get('source', '?')))}</strong> | "
        f"{escape(str(e.get('summary', '-')))}</li>"
        for e in events
    )
    return f"<ul>{items}</ul>"


def render_operator_playbook_panel(recommendations: list) -> str:
    """Render compact operator playbook recommendations."""
    if not recommendations:
        return '<ul><li class="muted">Aucune recommendation opérateur disponible.</li></ul>'

    rows = []
    for rec in recommendations:
        steps = rec.get("suggested_steps", [])
        steps_html = ""
        if steps:
            steps_items = "".join(f"<li>{escape(str(s))}</li>" for s in steps[:3])
            steps_html = f"<ul>{steps_items}</ul>"

        rows.append(
            f"<li>"
            f"<strong>[{escape(str(rec.get('priority', 'low')).upper())}]</strong> "
            f"<code>{escape(str(rec.get('address', '?')))}</code> "
            f"| playbook={escape(str(rec.get('playbook_id', '-')))} "
            f"| action={escape(str(rec.get('recommended_action', '-')))} "
            f"| reason={escape(str(rec.get('reason', '-')))}"
            f"{steps_html}"
            f"</li>"
        )

    return f"<ul>{''.join(rows)}</ul>"


def render_operator_rule_engine_panel(summary: dict, recent_log_events: list) -> str:
    """Render compact local rule engine results."""
    auto_rows = summary.get("auto_applied", []) if isinstance(summary, dict) else []
    pending_rows = (
        summary.get("pending_confirmations", []) if isinstance(summary, dict) else []
    )
    recent_rows = summary.get("recent_matched", []) if isinstance(summary, dict) else []

    lines = [
        f"<li>Auto-applied actions: <strong>{len(auto_rows)}</strong> | "
        f"Pending confirmations: <strong>{len(pending_rows)}</strong> | "
        f"Recently matched rules: <strong>{len(recent_rows)}</strong></li>"
    ]

    if auto_rows:
        items = "".join(
            f"<li><code>{escape(str(r.get('address', '?')))}</code> "
            f"| {escape(str(r.get('rule_id', '-')))} "
            f"| {escape(str(r.get('recommended_action', '-')))}</li>"
            for r in auto_rows[:5]
        )
        lines.append(f"<li>Auto-applied (top 5):<ul>{items}</ul></li>")

    if pending_rows:
        items = "".join(
            f"<li><code>{escape(str(r.get('address', '?')))}</code> "
            f"| {escape(str(r.get('rule_id', '-')))} "
            f"| reason={escape(str(r.get('reason', '-')))}</li>"
            for r in pending_rows[:5]
        )
        lines.append(f"<li>Pending confirmations (top 5):<ul>{items}</ul></li>")

    if recent_rows:
        items = "".join(
            f"<li><code>{escape(str(r.get('address', '?')))}</code> "
            f"| {escape(str(r.get('rule_id', '-')))} "
            f"| matched={escape(str(r.get('matched', False)))}"
            f"</li>"
            for r in recent_rows[:5]
        )
        lines.append(f"<li>Recently matched (current eval):<ul>{items}</ul></li>")

    if recent_log_events:
        items = "".join(
            f'<li><span class="muted">{escape(str(e.get("timestamp", "-")))}</span> '
            f"| <code>{escape(str(e.get('address', '?')))}</code> "
            f"| {escape(str(e.get('rule_id', '-')))} "
            f"| auto={escape(str(e.get('auto_applied', False)))}</li>"
            for e in recent_log_events[-5:]
        )
        lines.append(f"<li>Recent local automation log:<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_briefing_panel(briefing: dict) -> str:
    """Render compact operator shift-handoff briefing."""
    if not briefing:
        return '<ul><li class="muted">Aucun briefing opérateur disponible.</li></ul>'

    top_priorities = briefing.get("top_priorities", [])
    recent_auto = briefing.get("recent_auto_actions", [])
    timeline_hl = briefing.get("recent_timeline_highlights", [])
    next_steps = briefing.get("suggested_next_steps", [])

    lines = [
        f"<li>Open cases: <strong>{escape(str(briefing.get('open_cases_count', 0)))}</strong> | "
        f"Investigating: <strong>{escape(str(briefing.get('investigating_count', 0)))}</strong> | "
        f"Pending confirmations: <strong>{escape(str(briefing.get('pending_confirmations_count', 0)))}</strong></li>"
    ]

    if top_priorities:
        items = "".join(
            f"<li><code>{escape(str(p.get('address', '?')))}</code> "
            f"| {escape(str(p.get('name', 'Inconnu')))} "
            f"| {escape(str(p.get('triage_bucket', 'normal')))}:{escape(str(p.get('triage_score', 0)))} "
            f"| {escape(str(p.get('reason', '-')))}</li>"
            for p in top_priorities[:5]
        )
        lines.append(f"<li>Top priorities:<ul>{items}</ul></li>")

    if recent_auto:
        items = "".join(
            f"<li><code>{escape(str(a.get('address', '?')))}</code> "
            f"| {escape(str(a.get('rule_id', '-')))} "
            f"| {escape(str(a.get('recommended_action', '-')))}</li>"
            for a in recent_auto[:3]
        )
        lines.append(f"<li>Recent auto-actions:<ul>{items}</ul></li>")

    if timeline_hl:
        items = "".join(f"<li>{escape(str(x))}</li>" for x in timeline_hl[:3])
        lines.append(f"<li>Recent timeline highlights:<ul>{items}</ul></li>")

    if next_steps:
        items = "".join(f"<li>{escape(str(step))}</li>" for step in next_steps[:5])
        lines.append(f"<li>Suggested next steps:<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_alerting_panel(summary: dict) -> str:
    """Render compact operator alerting and escalation panel."""
    if not summary:
        return '<ul><li class="muted">Aucune alerte opérateur disponible.</li></ul>'

    active = summary.get("active_alerts", [])
    escalations = summary.get("recent_escalations", [])
    immediate = summary.get("needs_immediate_review", [])

    lines = [
        f"<li>Active alerts: <strong>{len(active)}</strong> | "
        f"Recent escalations: <strong>{len(escalations)}</strong> | "
        f"Needs immediate review: <strong>{len(immediate)}</strong></li>"
    ]

    if active:
        items = "".join(
            f'<li><span class="muted">{escape(str(a.get("created_at", "-")))}</span> '
            f"| <strong>{escape(str(a.get('severity', 'low')).upper())}</strong> "
            f"| <code>{escape(str(a.get('device_address', '?')))}</code> "
            f"| {escape(str(a.get('title', '-')))}</li>"
            for a in active[:5]
        )
        lines.append(f"<li>Active alerts (top 5):<ul>{items}</ul></li>")

    if escalations:
        items = "".join(
            f"<li><code>{escape(str(a.get('device_address', '?')))}</code> "
            f"| {escape(str(a.get('alert_id', '-')))} "
            f"| {escape(str(a.get('reason', '-')))}</li>"
            for a in escalations[:5]
        )
        lines.append(f"<li>Recent escalations (top 5):<ul>{items}</ul></li>")

    if immediate:
        items = "".join(
            f"<li><code>{escape(str(a.get('device_address', '?')))}</code> "
            f"| follow-up: {escape(str(a.get('recommended_followup', '-')))}</li>"
            for a in immediate[:5]
        )
        lines.append(f"<li>Needs immediate review (top 5):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_correlation_panel(summary: dict) -> str:
    """Render compact cluster/campaign view for operator correlation."""
    if not summary:
        return (
            '<ul><li class="muted">Aucun cluster de corrélation disponible.</li></ul>'
        )

    top_clusters = summary.get("top_correlation_clusters", [])
    coordinated = summary.get("possible_coordinated_devices", [])
    needs_review = summary.get("needs_cluster_review", [])

    lines = [
        f"<li>Top correlation clusters: <strong>{len(top_clusters)}</strong> | "
        f"Possible coordinated devices: <strong>{len(coordinated)}</strong> | "
        f"Needs cluster review: <strong>{len(needs_review)}</strong></li>"
    ]

    if top_clusters:
        items = "".join(
            f"<li><code>{escape(str(c.get('cluster_id', '?')))}</code> "
            f"| risk=<strong>{escape(str(c.get('risk_level', 'low')).upper())}</strong> "
            f"| members={escape(str(c.get('member_count', 0)))} "
            f"| {escape(str(c.get('reason_summary', '-')))}</li>"
            for c in top_clusters[:5]
        )
        lines.append(f"<li>Top clusters (top 5):<ul>{items}</ul></li>")

    if coordinated:
        items = "".join(
            f"<li><code>{escape(', '.join(c.get('member_addresses', [])[:4]))}</code>"
            f" | signals={escape(', '.join([str(s) for s in c.get('top_signals', [])[:3]]) or '-')}</li>"
            for c in coordinated[:5]
        )
        lines.append(f"<li>Possible coordinated devices (top 5):<ul>{items}</ul></li>")

    if needs_review:
        items = "".join(
            f"<li><code>{escape(str(c.get('cluster_id', '?')))}</code> "
            f"| follow-up: {escape(str(c.get('recommended_followup', '-')))}</li>"
            for c in needs_review[:5]
        )
        lines.append(f"<li>Needs cluster review (top 5):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_campaign_panel(summary: dict) -> str:
    """Render compact campaign lifecycle view from tracked clusters."""
    if not summary:
        return '<ul><li class="muted">Aucune campagne suivie disponible.</li></ul>'

    active = summary.get("active_campaigns", [])
    recurring = summary.get("recurring_clusters", [])
    expanding = summary.get("expanding_groups", [])
    needs_review = summary.get("needs_campaign_review", [])

    lines = [
        f"<li>Active campaigns: <strong>{len(active)}</strong> | "
        f"Recurring clusters: <strong>{len(recurring)}</strong> | "
        f"Expanding groups: <strong>{len(expanding)}</strong> | "
        f"Needs campaign review: <strong>{len(needs_review)}</strong></li>"
    ]

    if active:
        items = "".join(
            f"<li><code>{escape(str(c.get('campaign_id', '?')))}</code> "
            f"| status=<strong>{escape(str(c.get('status', 'new')).upper())}</strong> "
            f"| risk={escape(str(c.get('risk_level', 'low')).upper())} "
            f"| members={escape(str(c.get('member_count', 0)))} "
            f"| trend={escape(str(c.get('activity_trend', '-')))}</li>"
            for c in active[:5]
        )
        lines.append(f"<li>Active campaigns (top 5):<ul>{items}</ul></li>")

    if recurring:
        items = "".join(
            f"<li><code>{escape(str(c.get('campaign_id', '?')))}</code> "
            f"| last_seen={escape(str(c.get('last_seen', '-')))} "
            f"| reason={escape(str(c.get('reason_summary', '-')))}</li>"
            for c in recurring[:5]
        )
        lines.append(f"<li>Recurring clusters (top 5):<ul>{items}</ul></li>")

    if expanding:
        items = "".join(
            f"<li><code>{escape(str(c.get('campaign_id', '?')))}</code> "
            f"| follow-up: {escape(str(c.get('recommended_followup', '-')))}</li>"
            for c in expanding[:5]
        )
        lines.append(f"<li>Expanding groups (top 5):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_evidence_panel(summary: dict) -> str:
    """Render compact evidence pack / consolidated dossier panel."""
    if not summary:
        return '<ul><li class="muted">Aucun evidence pack disponible.</li></ul>'

    recent = summary.get("recent_evidence_packs", [])
    review = summary.get("ready_for_review_dossiers", [])
    campaign = summary.get("campaign_evidence_summary", [])

    lines = [
        f"<li>Recent evidence packs: <strong>{len(recent)}</strong> | "
        f"Ready for review dossiers: <strong>{len(review)}</strong> | "
        f"Campaign evidence summary: <strong>{len(campaign)}</strong></li>"
    ]

    if recent:
        items = "".join(
            f"<li><code>{escape(str(p.get('pack_id', '?')))}</code> "
            f"| scope={escape(str(p.get('scope_type', '-')))}:{escape(str(p.get('scope_id', '-')))} "
            f"| risk={escape(str(p.get('risk_level', 'low')).upper())}</li>"
            for p in recent[-5:]
        )
        lines.append(f"<li>Recent evidence packs (top 5):<ul>{items}</ul></li>")

    if review:
        items = "".join(
            f"<li><code>{escape(str(p.get('scope_type', '-')))}:{escape(str(p.get('scope_id', '-')))}</code> "
            f"| findings={escape(str(len(p.get('key_findings', []))))} "
            f"| follow-up: {escape(str(p.get('recommended_followup', '-')))}</li>"
            for p in review[:5]
        )
        lines.append(f"<li>Ready for review dossiers (top 5):<ul>{items}</ul></li>")

    if campaign:
        items = "".join(
            f"<li><code>{escape(str(p.get('scope_id', '-')))}</code> "
            f"| alerts={escape(str(p.get('alerts_summary', '-')))} "
            f"| summary={escape(str(p.get('summary', '-')))}</li>"
            for p in campaign[:5]
        )
        lines.append(f"<li>Campaign evidence summary (top 5):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_queue_panel(summary: dict) -> str:
    """Render compact operator queue / case board panel."""
    if not summary:
        return '<ul><li class="muted">Aucune file opérateur disponible.</li></ul>'

    queue = summary.get("operator_queue", [])
    needs_review = summary.get("needs_review", [])
    blocked = summary.get("blocked_items", [])
    ready_now = summary.get("ready_now", [])
    resolved = summary.get("recently_resolved", [])

    lines = [
        f"<li>Operator queue: <strong>{len(queue)}</strong> | "
        f"Needs review: <strong>{len(needs_review)}</strong> | "
        f"Blocked items: <strong>{len(blocked)}</strong> | "
        f"Ready now: <strong>{len(ready_now)}</strong> | "
        f"Recently resolved: <strong>{len(resolved)}</strong></li>"
    ]

    if queue:
        items = "".join(
            f"<li><code>{escape(str(i.get('item_id', '?')))}</code> "
            f"| {escape(str(i.get('scope_type', '-')))}:{escape(str(i.get('scope_id', '-')))} "
            f"| state=<strong>{escape(str(i.get('queue_state', 'new')).upper())}</strong> "
            f"| priority={escape(str(i.get('priority', 'low')).upper())}</li>"
            for i in queue[:6]
        )
        lines.append(f"<li>Operator queue (top 6):<ul>{items}</ul></li>")

    if ready_now:
        items = "".join(
            f"<li><code>{escape(str(i.get('item_id', '?')))}</code> "
            f"| action: {escape(str(i.get('recommended_action', '-')))}</li>"
            for i in ready_now[:5]
        )
        lines.append(f"<li>Ready now (top 5):<ul>{items}</ul></li>")

    if blocked:
        items = "".join(
            f"<li><code>{escape(str(i.get('item_id', '?')))}</code> "
            f"| blockers: {escape(', '.join([str(b) for b in i.get('blocking_factors', [])]) or '-')}</li>"
            for i in blocked[:5]
        )
        lines.append(f"<li>Blocked items (top 5):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_queue_health_panel(summary: dict) -> str:
    """Render compact queue health / aging / bottleneck panel."""
    if not summary:
        return '<ul><li class="muted">Aucun snapshot queue health disponible.</li></ul>'

    health = summary.get("queue_health", {})
    aging = summary.get("aging_overview", [])
    blocked = summary.get("blocked_items", [])
    stale = summary.get("stale_items", [])
    pressure = summary.get("operator_pressure", {})

    lines = [
        f"<li>Queue health: total=<strong>{escape(str(health.get('total_items', 0)))}</strong> "
        f"| ready={escape(str(health.get('ready_count', 0)))} "
        f"| blocked={escape(str(health.get('blocked_count', 0)))} "
        f"| in_review={escape(str(health.get('in_review_count', 0)))} "
        f"| pressure=<strong>{escape(str(health.get('queue_pressure', 'low')).upper())}</strong></li>"
    ]

    if aging:
        items = "".join(
            f"<li>{escape(str(a.get('bucket', '-')))}: <strong>{escape(str(a.get('count', 0)))}</strong></li>"
            for a in aging
        )
        lines.append(f"<li>Aging overview:<ul>{items}</ul></li>")

    if blocked:
        items = "".join(
            f"<li><code>{escape(str(i.get('item_id', '?')))}</code> "
            f"| state={escape(str(i.get('queue_state', '-')))} "
            f"| blockers={escape(', '.join([str(b) for b in i.get('blocking_factors', [])]) or '-')}</li>"
            for i in blocked[:5]
        )
        lines.append(f"<li>Blocked items (top 5):<ul>{items}</ul></li>")

    if stale:
        items = "".join(
            f"<li><code>{escape(str(i.get('item_id', '?')))}</code> "
            f"| age_min={escape(str(i.get('age_minutes', 0)))} "
            f"| state={escape(str(i.get('queue_state', '-')))}</li>"
            for i in stale[:5]
        )
        lines.append(f"<li>Stale items (top 5):<ul>{items}</ul></li>")

    if pressure:
        reasons = pressure.get("bottleneck_reasons", [])
        reasons_html = ""
        if reasons:
            reasons_html = (
                "<ul>"
                + "".join(f"<li>{escape(str(r))}</li>" for r in reasons[:5])
                + "</ul>"
            )
        lines.append(
            f"<li>Operator pressure: <strong>{escape(str(pressure.get('queue_pressure', 'low')).upper())}</strong> "
            f"| follow-up: {escape(str(pressure.get('recommended_followup', '-')))}{reasons_html}</li>"
        )

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_outcomes_panel(summary: dict) -> str:
    """Render compact operator outcomes / feedback loop panel."""
    if not summary:
        return '<ul><li class="muted">Aucun outcome opérateur disponible.</li></ul>'

    outcomes = summary.get("operator_outcomes", [])
    effective = summary.get("most_effective_actions", [])
    reopened = summary.get("reopened_items", [])
    weak = summary.get("weak_recommendations", [])

    lines = [
        f"<li>Operator outcomes: <strong>{escape(str(len(outcomes)))}</strong> "
        f"| reopened: <strong>{escape(str(len(reopened)))}</strong> "
        f"| weak recommendations: <strong>{escape(str(len(weak)))}</strong></li>"
    ]

    if outcomes:
        items = "".join(
            f"<li><code>{escape(str(r.get('outcome_id', '?')))}</code> "
            f"| {escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| label=<strong>{escape(str(r.get('outcome_label', '-')))}</strong> "
            f"| eff={escape(str(r.get('effectiveness', 0)))} "
            f"| action={escape(str(r.get('source_action', '-')))}</li>"
            for r in outcomes[:6]
        )
        lines.append(f"<li>Operator outcomes (top 6):<ul>{items}</ul></li>")

    if effective:
        items = "".join(
            f"<li>{escape(str(r.get('source_action', '-')))} "
            f"| avg_eff=<strong>{escape(str(r.get('avg_effectiveness', 0)))}</strong> "
            f"| count={escape(str(r.get('count', 0)))}</li>"
            for r in effective[:5]
        )
    else:
        items = '<li class="muted">No effective action ranking yet.</li>'
    lines.append(f"<li>Most effective actions:<ul>{items}</ul></li>")

    if reopened:
        items = "".join(
            f"<li><code>{escape(str(r.get('scope_id', '-')))}</code> "
            f"| {escape(str(r.get('scope_type', '-')))} "
            f"| {escape(str(r.get('outcome_label', '-')))} "
            f"| from {escape(str(r.get('queue_state_before', '-')))} to {escape(str(r.get('queue_state_after', '-')))}</li>"
            for r in reopened[:5]
        )
    else:
        items = '<li class="muted">No reopened items.</li>'
    lines.append(f"<li>Reopened items (top 5):<ul>{items}</ul></li>")

    if weak:
        items = "".join(
            f"<li><code>{escape(str(r.get('scope_id', '-')))}</code> "
            f"| label={escape(str(r.get('outcome_label', '-')))} "
            f"| eff={escape(str(r.get('effectiveness', 0)))} "
            f"| playbook={escape(str(r.get('source_playbook', '-')) or '-')}</li>"
            for r in weak[:5]
        )
    else:
        items = '<li class="muted">No weak recommendations flagged.</li>'
    lines.append(f"<li>Weak recommendations (top 5):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_recommendation_tuning_panel(summary: dict) -> str:
    """Render compact recommendation tuning / operator confidence panel."""
    if not summary:
        return '<ul><li class="muted">Aucun profil de confidence disponible.</li></ul>'

    confidence = summary.get("recommendation_confidence", [])
    effective = summary.get("most_effective_playbooks", [])
    weak = summary.get("weak_recommendations", [])
    manual = summary.get("needs_manual_review", [])

    lines = [
        f"<li>Recommendation confidence: <strong>{escape(str(len(confidence)))}</strong> "
        f"| weak recommendations: <strong>{escape(str(len(weak)))}</strong> "
        f"| manual review: <strong>{escape(str(len(manual)))}</strong></li>"
    ]

    if confidence:
        items = "".join(
            f"<li><code>{escape(str(r.get('recommendation_id', '?')))}</code> "
            f"| playbook={escape(str(r.get('source_playbook', '-')))} "
            f"| scope={escape(str(r.get('scope_type', '-')))} "
            f"| confidence=<strong>{escape(str(r.get('confidence_level', 'uncertain')).upper())}</strong> "
            f"| eff={escape(str(r.get('effectiveness_score', 0)))} "
            f"| rank_adj={escape(str(r.get('recommended_rank_adjustment', 0)))}</li>"
            for r in confidence[:6]
        )
        lines.append(f"<li>Recommendation confidence (top 6):<ul>{items}</ul></li>")

    if effective:
        items = "".join(
            f"<li>{escape(str(r.get('source_playbook', '-')))} "
            f"| confidence={escape(str(r.get('confidence_level', 'uncertain')))} "
            f"| eff=<strong>{escape(str(r.get('effectiveness_score', 0)))}</strong> "
            f"| success={escape(str(r.get('success_count', 0)))}</li>"
            for r in effective[:5]
        )
    else:
        items = '<li class="muted">No effective playbooks ranked yet.</li>'
    lines.append(f"<li>Most effective playbooks:<ul>{items}</ul></li>")

    if weak:
        items = "".join(
            f"<li>{escape(str(r.get('source_playbook', '-')))} "
            f"| confidence={escape(str(r.get('confidence_level', 'uncertain')))} "
            f"| failures={escape(str(r.get('failure_count', 0)))} "
            f"| reopened={escape(str(r.get('reopened_count', 0)))}</li>"
            for r in weak[:5]
        )
    else:
        items = '<li class="muted">No weak recommendations flagged.</li>'
    lines.append(f"<li>Weak recommendations (top 5):<ul>{items}</ul></li>")

    if manual:
        items = "".join(
            f"<li>{escape(str(r.get('source_playbook', '-')))} "
            f"| confidence={escape(str(r.get('confidence_level', 'uncertain')))} "
            f"| notes={escape(str(r.get('usage_notes', '-')))}</li>"
            for r in manual[:5]
        )
    else:
        items = '<li class="muted">No manual review signals.</li>'
    lines.append(f"<li>Needs manual review (top 5):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_review_readiness_panel(summary: dict) -> str:
    """Render compact review readiness / readiness gate panel."""
    if not summary:
        return '<ul><li class="muted">Aucun profil de review readiness disponible.</li></ul>'

    readiness = summary.get("review_readiness", [])
    ready_review = summary.get("ready_for_review", [])
    needs_evidence = summary.get("needs_more_evidence", [])
    ready_handoff = summary.get("ready_for_handoff", [])
    ready_archive = summary.get("ready_for_archive", [])

    lines = [
        f"<li>Review readiness: <strong>{escape(str(len(readiness)))}</strong> "
        f"| ready_for_review: <strong>{escape(str(len(ready_review)))}</strong> "
        f"| needs_more_evidence: <strong>{escape(str(len(needs_evidence)))}</strong> "
        f"| handoff: <strong>{escape(str(len(ready_handoff)))}</strong> "
        f"| archive: <strong>{escape(str(len(ready_archive)))}</strong></li>"
    ]

    if readiness:
        items = "".join(
            f"<li><code>{escape(str(r.get('review_id', '?')))}</code> "
            f"| {escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| state=<strong>{escape(str(r.get('readiness_state', 'not_ready')).upper())}</strong> "
            f"| score={escape(str(r.get('readiness_score', 0)))} "
            f"| disposition={escape(str(r.get('recommended_disposition', '-')))}</li>"
            for r in readiness[:6]
        )
        lines.append(f"<li>Review readiness (top 6):<ul>{items}</ul></li>")

    if ready_review:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| score={escape(str(r.get('readiness_score', 0)))} "
            f"| notes={escape(str(r.get('review_notes', '-')))}</li>"
            for r in ready_review[:5]
        )
    else:
        items = '<li class="muted">No scopes ready for review yet.</li>'
    lines.append(f"<li>Ready for review (top 5):<ul>{items}</ul></li>")

    if needs_evidence:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| missing={escape(', '.join([str(x) for x in r.get('missing_elements', [])]) or '-')}</li>"
            for r in needs_evidence[:5]
        )
    else:
        items = '<li class="muted">No additional evidence needed.</li>'
    lines.append(f"<li>Needs more evidence (top 5):<ul>{items}</ul></li>")

    if ready_handoff:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| strengths={escape(', '.join([str(x) for x in r.get('strengths', [])]) or '-')}</li>"
            for r in ready_handoff[:5]
        )
    else:
        items = '<li class="muted">No scopes ready for handoff.</li>'
    lines.append(f"<li>Ready for handoff (top 5):<ul>{items}</ul></li>")

    if ready_archive:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| disposition={escape(str(r.get('recommended_disposition', '-')))} "
            f"| score={escape(str(r.get('readiness_score', 0)))}</li>"
            for r in ready_archive[:5]
        )
    else:
        items = '<li class="muted">No scopes ready for archive.</li>'
    lines.append(f"<li>Ready for archive (top 5):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_session_journal_panel(summary: dict) -> str:
    """Render compact operator session journal / shift continuity panel."""
    if not summary:
        return '<ul><li class="muted">Aucun journal de session opérateur disponible.</li></ul>'

    journal = summary.get("current_session_journal", {})
    activity = summary.get("shift_activity", {})
    carry_over = summary.get("carry_over_items", [])
    priorities = summary.get("next_shift_priorities", [])
    handoffs = summary.get("recent_handoffs", [])

    lines = [
        f"<li>Current session journal: <code>{escape(str(journal.get('session_id', '-')))}</code> "
        f"| started={escape(str(journal.get('started_at', '-')))} "
        f"| ended={escape(str(journal.get('ended_at', '-')))}</li>"
    ]

    lines.append(
        f"<li>Shift activity: items_touched=<strong>{escape(str(activity.get('items_touched', 0)))}</strong> "
        f"| campaigns_updated={escape(str(activity.get('campaigns_updated', 0)))} "
        f"| alerts_reviewed={escape(str(activity.get('alerts_reviewed', 0)))} "
        f"| outcomes_recorded={escape(str(activity.get('outcomes_recorded', 0)))} "
        f"| readiness_changes={escape(str(activity.get('readiness_changes', 0)))}"
        f"</li>"
    )

    if carry_over:
        items = "".join(
            f"<li><code>{escape(str(r.get('item_id', '?')))}</code> "
            f"| {escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| state={escape(str(r.get('queue_state', '-')))}</li>"
            for r in carry_over[:6]
        )
    else:
        items = '<li class="muted">No carry-over items.</li>'
    lines.append(f"<li>Carry over items (top 6):<ul>{items}</ul></li>")

    if priorities:
        items = "".join(f"<li>{escape(str(x))}</li>" for x in priorities[:6])
    else:
        items = '<li class="muted">No next-shift priorities.</li>'
    lines.append(f"<li>Next shift priorities:<ul>{items}</ul></li>")

    if handoffs:
        items = "".join(
            f"<li>{escape(str(h.get('scope_type', '-')))}:{escape(str(h.get('scope_id', '-')))} "
            f"| reason={escape(str(h.get('reason', '-')))}</li>"
            for h in handoffs[:6]
        )
    else:
        items = '<li class="muted">No recent handoffs.</li>'
    lines.append(f"<li>Recent handoffs (top 6):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_pattern_library_panel(summary: dict) -> str:
    """Render compact operator pattern library / recurring case memory panel."""
    if not summary:
        return (
            '<ul><li class="muted">Aucune librairie de patterns disponible.</li></ul>'
        )

    known = summary.get("known_patterns", [])
    recurring = summary.get("recurring_case_types", [])
    matches = summary.get("likely_matches", [])
    guidance = summary.get("pattern_based_guidance", [])

    lines = [
        f"<li>Known patterns: <strong>{escape(str(len(known)))}</strong> | "
        f"Recurring case types: <strong>{escape(str(len(recurring)))}</strong> | "
        f"Likely matches: <strong>{escape(str(len(matches)))}</strong></li>"
    ]

    if known:
        items = "".join(
            f"<li><code>{escape(str(p.get('pattern_id', '?')))}</code> "
            f"| type={escape(str(p.get('pattern_type', '-')))} "
            f"| risk={escape(str(p.get('risk_profile', '-')))} "
            f"| confidence={escape(str(p.get('confidence_level', '-')))} "
            f"| title={escape(str(p.get('title', '-')))}</li>"
            for p in known[:6]
        )
    else:
        items = '<li class="muted">No known patterns yet.</li>'
    lines.append(f"<li>Known patterns (top 6):<ul>{items}</ul></li>")

    if recurring:
        items = "".join(
            f"<li>{escape(str(r.get('pattern_type', '-')))} "
            f"| {escape(str(r.get('title', '-')))} "
            f"| risk={escape(str(r.get('risk_profile', '-')))}</li>"
            for r in recurring[:6]
        )
    else:
        items = '<li class="muted">No recurring case types detected.</li>'
    lines.append(f"<li>Recurring case types (top 6):<ul>{items}</ul></li>")

    if matches:
        items = "".join(
            f"<li>{escape(str(m.get('scope_type', '-')))}:{escape(str(m.get('scope_id', '-')))} "
            f"| pattern=<code>{escape(str(m.get('pattern_id', '-')))}</code> "
            f"| score={escape(str(m.get('match_score', 0.0)))} "
            f"| confidence={escape(str(m.get('confidence_level', '-')))}</li>"
            for m in matches[:6]
        )
    else:
        items = '<li class="muted">No likely matches for current scopes.</li>'
    lines.append(f"<li>Likely matches (top 6):<ul>{items}</ul></li>")

    if guidance:
        items = "".join(f"<li>{escape(str(g))}</li>" for g in guidance[:6])
    else:
        items = '<li class="muted">No pattern-based guidance yet.</li>'
    lines.append(f"<li>Pattern-based guidance:<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_escalation_package_panel(summary: dict) -> str:
    """Render compact escalation package / transmission panel."""
    if not summary:
        return '<ul><li class="muted">Aucun package d\'escalade disponible.</li></ul>'

    packages = summary.get("escalation_packages", [])
    ready = summary.get("ready_to_escalate", [])
    specialist = summary.get("specialist_review_needed", [])
    high_risk = summary.get("high_risk_open_items", [])
    recent = summary.get("recent_escalations", [])

    lines = [
        f"<li>Escalation packages: <strong>{escape(str(len(packages)))}</strong> "
        f"| ready to escalate: <strong>{escape(str(len(ready)))}</strong> "
        f"| specialist review needed: <strong>{escape(str(len(specialist)))}</strong> "
        f"| high-risk open items: <strong>{escape(str(len(high_risk)))}</strong></li>"
    ]

    if packages:
        items = "".join(
            f"<li><code>{escape(str(p.get('escalation_id', '?')))}</code> "
            f"| {escape(str(p.get('scope_type', '-')))}:{escape(str(p.get('scope_id', '-')))} "
            f"| reason=<strong>{escape(str(p.get('escalation_reason', '-')))}</strong> "
            f"| priority={escape(str(p.get('priority', '-')))} "
            f"| owner={escape(str(p.get('recommended_next_owner', '-')))}</li>"
            for p in packages[:6]
        )
    else:
        items = '<li class="muted">No escalation packages.</li>'
    lines.append(f"<li>Escalation packages (top 6):<ul>{items}</ul></li>")

    if specialist:
        items = "".join(
            f"<li>{escape(str(p.get('scope_type', '-')))}:{escape(str(p.get('scope_id', '-')))} "
            f"| owner={escape(str(p.get('recommended_next_owner', '-')))} "
            f"| reason={escape(str(p.get('escalation_reason', '-')))}</li>"
            for p in specialist[:6]
        )
    else:
        items = '<li class="muted">No specialist review needed.</li>'
    lines.append(f"<li>Specialist review needed (top 6):<ul>{items}</ul></li>")

    if high_risk:
        items = "".join(
            f"<li>{escape(str(p.get('scope_type', '-')))}:{escape(str(p.get('scope_id', '-')))} "
            f"| priority={escape(str(p.get('priority', '-')))} "
            f"| open_risks={escape(', '.join([str(x) for x in p.get('open_risks', [])]) or '-')}</li>"
            for p in high_risk[:6]
        )
    else:
        items = '<li class="muted">No high-risk open items.</li>'
    lines.append(f"<li>High-risk open items (top 6):<ul>{items}</ul></li>")

    if recent:
        items = "".join(
            f"<li><code>{escape(str(p.get('escalation_id', '?')))}</code> "
            f"| created={escape(str(p.get('created_at', '-')))} "
            f"| reason={escape(str(p.get('escalation_reason', '-')))}</li>"
            for p in recent[:6]
        )
    else:
        items = '<li class="muted">No recent escalations.</li>'
    lines.append(f"<li>Recent escalations (top 6):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_escalation_feedback_panel(summary: dict) -> str:
    """Render compact escalation feedback / specialist return panel."""
    if not summary:
        return '<ul><li class="muted">Aucun feedback d\'escalade disponible.</li></ul>'

    feedback = summary.get("escalation_feedback", [])
    followup = summary.get("returned_for_followup", [])
    decisions = summary.get("specialist_decisions", [])
    ready_close = summary.get("ready_to_close", [])
    needs_data = summary.get("needs_more_data", [])

    lines = [
        f"<li>Escalation feedback: <strong>{escape(str(len(feedback)))}</strong> "
        f"| returned for follow-up: <strong>{escape(str(len(followup)))}</strong> "
        f"| ready to close: <strong>{escape(str(len(ready_close)))}</strong> "
        f"| needs more data: <strong>{escape(str(len(needs_data)))}</strong></li>"
    ]

    if feedback:
        items = "".join(
            f"<li><code>{escape(str(r.get('feedback_id', '?')))}</code> "
            f"| esc=<code>{escape(str(r.get('escalation_id', '-')))}</code> "
            f"| {escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| result=<strong>{escape(str(r.get('review_result', '-')))}</strong></li>"
            for r in feedback[:6]
        )
    else:
        items = '<li class="muted">No escalation feedback available.</li>'
    lines.append(f"<li>Escalation feedback (top 6):<ul>{items}</ul></li>")

    if decisions:
        items = "".join(
            f"<li>{escape(str(d.get('scope_type', '-')))}:{escape(str(d.get('scope_id', '-')))} "
            f"| result={escape(str(d.get('review_result', '-')))} "
            f"| {escape(str(d.get('decision_summary', '-')))}</li>"
            for d in decisions[:6]
        )
    else:
        items = '<li class="muted">No specialist decisions.</li>'
    lines.append(f"<li>Specialist decisions (top 6):<ul>{items}</ul></li>")

    if followup:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| return_state={escape(str(r.get('return_queue_state', '-')))} "
            f"| followup={escape(', '.join([str(x) for x in r.get('requested_followup', [])]) or '-')}</li>"
            for r in followup[:6]
        )
    else:
        items = '<li class="muted">No returned-for-follow-up entries.</li>'
    lines.append(f"<li>Returned for follow-up (top 6):<ul>{items}</ul></li>")

    if ready_close:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| recommendation={escape(str(r.get('closure_recommendation', '-')))}</li>"
            for r in ready_close[:6]
        )
    else:
        items = '<li class="muted">No items ready to close.</li>'
    lines.append(f"<li>Ready to close (top 6):<ul>{items}</ul></li>")

    if needs_data:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| notes={escape(str(r.get('specialist_notes', '-')))}</li>"
            for r in needs_data[:6]
        )
    else:
        items = '<li class="muted">No items requiring more data.</li>'
    lines.append(f"<li>Needs more data (top 6):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_closure_package_panel(summary: dict) -> str:
    """Render compact operator closure package / final resolution panel."""
    if not summary:
        return '<ul><li class="muted">Aucun package de clôture disponible.</li></ul>'

    packages = summary.get("closure_packages", [])
    recently_closed = summary.get("recently_closed", [])
    closed_after_esc = summary.get("closed_after_escalation", [])
    resolved_fp = summary.get("resolved_vs_false_positive", {})
    followup = summary.get("followup_still_needed", [])

    lines = [
        f"<li>Closure packages: <strong>{escape(str(len(packages)))}</strong> "
        f"| recently closed: <strong>{escape(str(len(recently_closed)))}</strong> "
        f"| closed after escalation: <strong>{escape(str(len(closed_after_esc)))}</strong></li>"
    ]

    if packages:
        items = "".join(
            f"<li><code>{escape(str(r.get('closure_id', '?')))}</code> "
            f"| {escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| disposition=<strong>{escape(str(r.get('final_disposition', '-')))}</strong> "
            f"| risk={escape(str(r.get('final_risk_level', '-')))} "
            f"| followup={escape(str(r.get('followup_mode', '-')))}</li>"
            for r in packages[:6]
        )
    else:
        items = '<li class="muted">No closure packages.</li>'
    lines.append(f"<li>Closure packages (top 6):<ul>{items}</ul></li>")

    if recently_closed:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| closed_at={escape(str(r.get('closed_at', '-')))} "
            f"| archive={escape(str(r.get('archive_recommendation', '-')))}</li>"
            for r in recently_closed[:6]
        )
    else:
        items = '<li class="muted">No recently closed scopes.</li>'
    lines.append(f"<li>Recently closed (top 6):<ul>{items}</ul></li>")

    lines.append(
        f"<li>Resolved vs false positive: "
        f"resolved=<strong>{escape(str(resolved_fp.get('resolved', 0)))}</strong> "
        f"| false_positive=<strong>{escape(str(resolved_fp.get('false_positive', 0)))}</strong></li>"
    )

    if closed_after_esc:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| summary={escape(str(r.get('resolution_summary', '-')))}</li>"
            for r in closed_after_esc[:6]
        )
    else:
        items = '<li class="muted">No closures after escalation.</li>'
    lines.append(f"<li>Closed after escalation (top 6):<ul>{items}</ul></li>")

    if followup:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| followup={escape(str(r.get('followup_mode', '-')))} "
            f"| risk={escape(str(r.get('final_risk_level', '-')))}</li>"
            for r in followup[:6]
        )
    else:
        items = '<li class="muted">No follow-up still needed.</li>'
    lines.append(f"<li>Follow-up still needed (top 6):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_post_closure_monitoring_policy_panel(summary: dict) -> str:
    """Render compact operator post-closure monitoring policy / recurrence watch panel."""
    if not summary:
        return '<ul><li class="muted">Aucune politique de monitoring post-clôture disponible.</li></ul>'

    policies = summary.get("monitoring_policies", [])
    watch_recurrence = summary.get("watch_for_recurrence", [])
    scheduled = summary.get("scheduled_rechecks", [])
    high_attention = summary.get("high_attention", [])
    reopen_triggers = summary.get("recent_reopen_triggers", [])

    lines = [
        f"<li>Monitoring policies: <strong>{escape(str(len(policies)))}</strong> "
        f"| watch_for_recurrence: <strong>{escape(str(len(watch_recurrence)))}</strong> "
        f"| scheduled_rechecks: <strong>{escape(str(len(scheduled)))}</strong></li>"
    ]

    if policies:
        items = "".join(
            f"<li><code>{escape(str(r.get('policy_id', '?')))}</code> "
            f"| {escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| mode=<strong>{escape(str(r.get('monitoring_mode', '-')))}</strong> "
            f"| review_window={escape(str(r.get('review_window', '-')))} "
            f"| priority={escape(str(r.get('priority_after_closure', '-')))}</li>"
            for r in policies[:6]
        )
    else:
        items = '<li class="muted">No monitoring policies.</li>'
    lines.append(f"<li>Post-closure monitoring (top 6):<ul>{items}</ul></li>")

    if watch_recurrence:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| reason={escape(str(r.get('monitoring_reason', '-')[:40]))} "
            f"| watch_signals={escape(str(len(r.get('watch_signals', []))))}</li>"
            for r in watch_recurrence[:6]
        )
    else:
        items = '<li class="muted">No watch_for_recurrence policies.</li>'
    lines.append(f"<li>Watch for recurrence (top 6):<ul>{items}</ul></li>")

    if scheduled:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| window={escape(str(r.get('review_window', '-')))} "
            f"| priority={escape(str(r.get('priority_after_closure', '-')))}</li>"
            for r in scheduled[:6]
        )
    else:
        items = '<li class="muted">No scheduled rechecks.</li>'
    lines.append(f"<li>Scheduled rechecks (top 6):<ul>{items}</ul></li>")

    if high_attention:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| reason={escape(str(r.get('monitoring_reason', '-')[:40]))} "
            f"| triggers={escape(str(len(r.get('reopen_triggers', []))))}</li>"
            for r in high_attention[:6]
        )
    else:
        items = '<li class="muted">No high attention policies.</li>'
    lines.append(f"<li>High attention after closure (top 6):<ul>{items}</ul></li>")

    if reopen_triggers:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| triggers={escape(str('|'.join(r.get('reopen_triggers', [])[:3])))}</li>"
            for r in reopen_triggers[:6]
        )
    else:
        items = '<li class="muted">No recent reopen triggers.</li>'
    lines.append(f"<li>Recent reopen triggers (top 6):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_reopen_policy_panel(summary: dict) -> str:
    """Render compact operator controlled reopen policy panel."""
    if not summary:
        return (
            '<ul><li class="muted">Aucune réouverture contrôlée disponible.</li></ul>'
        )

    records = summary.get("reopen_records", [])
    reopened_cases = summary.get("reopened_cases", [])
    recent_triggers = summary.get("recent_reopen_triggers", [])
    returned_to_queue = summary.get("returned_to_queue", [])
    repeated_reopeners = summary.get("repeated_reopeners", [])
    high_priority = summary.get("high_priority_reopens", [])

    lines = [
        f"<li>Reopen records: <strong>{escape(str(len(records)))}</strong> "
        f"| reopened cases: <strong>{escape(str(len(reopened_cases)))}</strong> "
        f"| returned to queue: <strong>{escape(str(len(returned_to_queue)))}</strong></li>"
    ]

    if records:
        items = "".join(
            f"<li><code>{escape(str(r.get('reopen_id', '?')))}</code> "
            f"| {escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| trigger=<strong>{escape(str(r.get('trigger_type', '-')))}</strong> "
            f"| priority={escape(str(r.get('reopen_priority', '-')))} "
            f"| queue={escape(str(r.get('target_queue_state', '-')))}</li>"
            for r in records[:6]
        )
    else:
        items = '<li class="muted">No reopen records.</li>'
    lines.append(f"<li>Reopen records (top 6):<ul>{items}</ul></li>")

    if reopened_cases:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| reason={escape(str(r.get('reopen_reason', '-')[:64]))}</li>"
            for r in reopened_cases[:6]
        )
    else:
        items = '<li class="muted">No reopened cases.</li>'
    lines.append(f"<li>Reopened cases (top 6):<ul>{items}</ul></li>")

    if recent_triggers:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| {escape(str(r.get('trigger_type', '-')))} "
            f"| {escape(str(r.get('trigger_summary', '-')[:80]))}</li>"
            for r in recent_triggers[:6]
        )
    else:
        items = '<li class="muted">No recent reopen triggers.</li>'
    lines.append(f"<li>Recent reopen triggers (top 6):<ul>{items}</ul></li>")

    if returned_to_queue:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| target={escape(str(r.get('target_queue_state', '-')))}</li>"
            for r in returned_to_queue[:6]
        )
    else:
        items = '<li class="muted">No return-to-queue actions.</li>'
    lines.append(f"<li>Returned to queue (top 6):<ul>{items}</ul></li>")

    if repeated_reopeners:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| reopen_count={escape(str(r.get('reopen_count', 1)))}</li>"
            for r in repeated_reopeners[:6]
        )
    else:
        items = '<li class="muted">No repeated reopeners.</li>'
    lines.append(f"<li>Repeated reopeners (top 6):<ul>{items}</ul></li>")

    if high_priority:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| priority=<strong>{escape(str(r.get('reopen_priority', '-')).upper())}</strong></li>"
            for r in high_priority[:6]
        )
    else:
        items = '<li class="muted">No high priority reopens.</li>'
    lines.append(f"<li>High priority reopens (top 6):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_lifecycle_lineage_panel(summary: dict) -> str:
    """Render compact lifecycle lineage / multi-cycle history panel."""
    if not summary:
        return (
            '<ul><li class="muted">Aucune lignée de cycle de vie disponible.</li></ul>'
        )

    lineage = summary.get("lifecycle_lineage", [])
    repeated = summary.get("repeated_reopeners", [])
    triggers = summary.get("recurring_triggers", [])
    multi_cycle = summary.get("multi_cycle_cases", [])
    stabilized = summary.get("stabilized_after_reopen", [])

    lines = [
        f"<li>Lifecycle lineage: <strong>{escape(str(len(lineage)))}</strong> "
        f"| repeated reopeners: <strong>{escape(str(len(repeated)))}</strong> "
        f"| recurring triggers: <strong>{escape(str(len(triggers)))}</strong> "
        f"| multi-cycle cases: <strong>{escape(str(len(multi_cycle)))}</strong> "
        f"| stabilized after reopen: <strong>{escape(str(len(stabilized)))}</strong></li>"
    ]

    if lineage:
        items = "".join(
            f"<li><code>{escape(str(r.get('lineage_id', '?')))}</code> "
            f"| {escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| cycles=<strong>{escape(str(r.get('cycle_count', 1)))}</strong> "
            f"| opened={escape(str(r.get('opened_count', 0)))} "
            f"| reopened={escape(str(r.get('reopened_count', 0)))} "
            f"| closures={escape(str(r.get('closure_count', 0)))} "
            f"| escalations={escape(str(r.get('escalation_count', 0)))}</li>"
            for r in lineage[:6]
        )
    else:
        items = '<li class="muted">No lifecycle lineage records.</li>'
    lines.append(f"<li>Lifecycle lineage (top 6):<ul>{items}</ul></li>")

    if repeated:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| reopened={escape(str(r.get('reopened_count', 0)))} "
            f"| last_trigger={escape(str(r.get('last_trigger_type', 'none')))}</li>"
            for r in repeated[:6]
        )
    else:
        items = '<li class="muted">No repeated reopeners.</li>'
    lines.append(f"<li>Repeated reopeners (top 6):<ul>{items}</ul></li>")

    if triggers:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| trigger={escape(str(r.get('last_trigger_type', 'none')))} "
            f"| reopened={escape(str(r.get('reopened_count', 0)))}</li>"
            for r in triggers[:6]
        )
    else:
        items = '<li class="muted">No recurring triggers.</li>'
    lines.append(f"<li>Recurring triggers (top 6):<ul>{items}</ul></li>")

    if multi_cycle:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| cycles={escape(str(r.get('cycle_count', 1)))} "
            f"| timeline={escape(str(r.get('timeline_summary', '-')))}</li>"
            for r in multi_cycle[:6]
        )
    else:
        items = '<li class="muted">No multi-cycle cases.</li>'
    lines.append(f"<li>Multi-cycle cases (top 6):<ul>{items}</ul></li>")

    if stabilized:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| state={escape(str(r.get('current_lifecycle_state', '-')))} "
            f"| updated={escape(str(r.get('updated_at', '-')))}</li>"
            for r in stabilized[:6]
        )
    else:
        items = '<li class="muted">No scopes stabilized after reopen.</li>'
    lines.append(f"<li>Stabilized after reopen (top 6):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_resolution_quality_panel(summary: dict) -> str:
    """Render compact resolution quality / stability assessment panel."""
    if not summary:
        return '<ul><li class="muted">Pas d\'évaluation de qualité de résolution disponible.</li></ul>'

    quality_summary = summary.get("resolution_quality", {})
    durable = summary.get("durable_closures", [])
    fragile = summary.get("fragile_closures", [])
    likely_reopen = summary.get("likely_reopeners", [])
    improvements = summary.get("improvement_suggestions", [])

    durable_count = quality_summary.get("durable", 0)
    mostly_stable_count = quality_summary.get("mostly_stable", 0)
    fragile_count = quality_summary.get("fragile", 0)
    likely_reopen_count = quality_summary.get("likely_to_reopen", 0)
    insufficient_count = quality_summary.get("insufficient_resolution", 0)

    lines = [
        f"<li>Resolution quality: "
        f"durable=<strong>{escape(str(durable_count))}</strong> | "
        f"mostly_stable=<strong>{escape(str(mostly_stable_count))}</strong> | "
        f"fragile=<strong>{escape(str(fragile_count))}</strong> | "
        f"likely_reopen=<strong>{escape(str(likely_reopen_count))}</strong> | "
        f"insufficient=<strong>{escape(str(insufficient_count))}</strong></li>"
    ]

    if durable:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| stability=<strong>{escape(str(r.get('stability_score', 0)))}</strong> "
            f"| reopen_risk={escape(str(r.get('reopen_risk', 0)))}</li>"
            for r in durable[:6]
        )
    else:
        items = '<li class="muted">No durable closures.</li>'
    lines.append(f"<li>Durable closures (top 6):<ul>{items}</ul></li>")

    if fragile:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| quality={escape(str(r.get('resolution_quality', '-')))} "
            f"| stability={escape(str(r.get('stability_score', 0)))}</li>"
            for r in fragile[:6]
        )
    else:
        items = '<li class="muted">No fragile closures.</li>'
    lines.append(f"<li>Fragile / at-risk closures (top 6):<ul>{items}</ul></li>")

    if likely_reopen:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| risk={escape(str(r.get('reopen_risk', 0)))} "
            f"| factors={escape(', '.join(r.get('weak_factors', [])[:2]))}</li>"
            for r in likely_reopen[:6]
        )
    else:
        items = '<li class="muted">No high reopen risk items.</li>'
    lines.append(f"<li>Likely reopeners (top 6):<ul>{items}</ul></li>")

    if improvements:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| suggestion={escape(str(r.get('recommendation', '-')))}</li>"
            for r in improvements[:6]
        )
    else:
        items = '<li class="muted">No improvement suggestions.</li>'
    lines.append(f"<li>Improvement suggestions (top 6):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_improvement_plan_panel(summary: dict) -> str:
    """Render compact resolution improvement plan panel."""
    if not summary:
        return '<ul><li class="muted">Pas de plan d\'amélioration disponible.</li></ul>'

    priority_counts = summary.get("priority_counts", {})
    plans = summary.get("improvement_plans", [])
    fragile = summary.get("fragile_closures_needing_action", [])
    gaps = summary.get("top_blocking_gaps", [])
    gains = summary.get("expected_stability_gains", [])
    followups = summary.get("suggested_followup_modes", [])

    critical_count = priority_counts.get("critical", 0)
    high_count = priority_counts.get("high", 0)
    medium_count = priority_counts.get("medium", 0)
    low_count = priority_counts.get("low", 0)

    lines = [
        f"<li>Improvement plans by priority: "
        f"critical=<strong>{escape(str(critical_count))}</strong> | "
        f"high=<strong>{escape(str(high_count))}</strong> | "
        f"medium=<strong>{escape(str(medium_count))}</strong> | "
        f"low=<strong>{escape(str(low_count))}</strong></li>"
    ]

    if plans:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| goal={escape(str(r.get('improvement_goal', '-')))} "
            f"| priority={escape(str(r.get('priority_level', '-')))}</li>"
            for r in plans[:6]
        )
    else:
        items = '<li class="muted">No active improvement plans.</li>'
    lines.append(f"<li>Improvement plans (top 6):<ul>{items}</ul></li>")

    if fragile:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| quality={escape(str(r.get('resolution_quality', '-')))} "
            f"| goal={escape(str(r.get('improvement_goal', '-')))}</li>"
            for r in fragile[:6]
        )
    else:
        items = '<li class="muted">No fragile closures requiring action.</li>'
    lines.append(f"<li>Fragile closures needing action (top 6):<ul>{items}</ul></li>")

    if gaps:
        gap_items = "".join(
            f"<li>{escape(str(gap[0]))} (found in <strong>{escape(str(gap[1]))}</strong> plans)</li>"
            for gap in gaps[:5]
        )
    else:
        gap_items = '<li class="muted">No blocking gaps identified.</li>'
    lines.append(f"<li>Top blocking gaps (top 5):<ul>{gap_items}</ul></li>")

    if gains:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| current={escape(str(r.get('current_stability', 0)))} "
            f"→ projected={escape(str(r.get('projected_stability', 0)))}</li>"
            for r in gains[:6]
        )
    else:
        items = '<li class="muted">No stability gains projected.</li>'
    lines.append(f"<li>Expected stability gains (top 6):<ul>{items}</ul></li>")

    if followups:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| followup={escape(str(r.get('followup_mode', '-')))}</li>"
            for r in followups[:6]
        )
    else:
        items = '<li class="muted">No follow-up modes suggested.</li>'
    lines.append(f"<li>Suggested follow-up modes (top 6):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_operator_outcome_learning_panel(summary: dict) -> str:
    """Render compact operator outcome learning panel."""
    if not summary:
        return '<ul><li class="muted">No outcome learning available.</li></ul>'

    learning = summary.get("outcome_learning", [])
    high_value = summary.get("high_value_action_patterns", [])
    reopen_reduction = summary.get("reopen_reduction_signals", [])
    mixed = summary.get("mixed_result_patterns", [])
    reuse = summary.get("recommended_reuse", [])

    lines = [
        f"<li>Outcome learning records: <strong>{escape(str(len(learning)))}</strong></li>"
    ]

    if high_value:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| pattern={escape(str(r.get('action_pattern', '-')))} "
            f"| confidence={escape(str(r.get('confidence_level', '-')))}</li>"
            for r in high_value[:6]
        )
    else:
        items = '<li class="muted">No high value action patterns.</li>'
    lines.append(f"<li>High value action patterns (top 6):<ul>{items}</ul></li>")

    if reopen_reduction:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| reopen_delta={escape(str(r.get('reopen_delta', 0)))} "
            f"| stability_delta={escape(str(r.get('stability_delta', 0)))}</li>"
            for r in reopen_reduction[:6]
        )
    else:
        items = '<li class="muted">No reopen reduction signals.</li>'
    lines.append(f"<li>Reopen reduction signals (top 6):<ul>{items}</ul></li>")

    if mixed:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| outcome={escape(str(r.get('observed_outcome', '-')))} "
            f"| caution={escape(', '.join(r.get('caution_flags', [])[:2]))}</li>"
            for r in mixed[:6]
        )
    else:
        items = '<li class="muted">No mixed result patterns.</li>'
    lines.append(f"<li>Mixed result patterns (top 6):<ul>{items}</ul></li>")

    if reuse:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| action={escape(str(r.get('action_pattern', '-')))} "
            f"| reuse={escape(str(r.get('recommended_reuse', '-')))}</li>"
            for r in reuse[:6]
        )
    else:
        items = '<li class="muted">No recommended reuse yet.</li>'
    lines.append(f"<li>Recommended reuse (top 6):<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


_LEARNING_SNAPSHOT_PRIORITY_BY_GUIDANCE = {
    "keep": "low",
    "watch": "medium",
    "investigate": "high",
}

_LEARNING_SNAPSHOT_GUIDANCE_PROFILE = {
    "keep": {
        "recommended_action": "continue current reuse pattern",
        "operator_note": "safe to continue under current pattern",
        "review_trigger": "no immediate review needed",
        "confidence_hint": "stable reuse signal",
        "followup_tempo": "routine",
        "attention_band": "low-touch",
        "response_posture": "steady",
        "reuse_gate": "open",
        "approval_mode": "default",
        "intervention_level": "minimal",
        "oversight_level": "light",
        "verification_mode": "spot-check",
        "escalation_path": "none",
        "operator_checkpoint": "optional",
        "trace_mode": "light trace",
        "audit_readiness": "background",
        "review_burden": "low",
        "documentation_mode": "compact",
        "handoff_readiness": "standby",
        "resolution_posture": "stable track",
        "closure_readiness": "eligible",
        "exit_path": "normal close",
        "reopen_risk": "low",
    },
    "watch": {
        "recommended_action": "monitor next sessions before broad reuse",
        "operator_note": "wait for one more stable learning cycle",
        "review_trigger": "recheck after next stable cycle",
        "confidence_hint": "moderate reuse confidence",
        "followup_tempo": "next cycle",
        "attention_band": "monitor",
        "response_posture": "cautious",
        "reuse_gate": "guarded",
        "approval_mode": "confirm",
        "intervention_level": "selective",
        "oversight_level": "active",
        "verification_mode": "confirm",
        "escalation_path": "ready if needed",
        "operator_checkpoint": "advised",
        "trace_mode": "tracked",
        "audit_readiness": "prepared",
        "review_burden": "moderate",
        "documentation_mode": "standard",
        "handoff_readiness": "ready",
        "resolution_posture": "watch and reassess",
        "closure_readiness": "pending check",
        "exit_path": "delay close",
        "reopen_risk": "moderate",
    },
    "investigate": {
        "recommended_action": "review recent mixed patterns before reuse",
        "operator_note": "review recent caution signals first",
        "review_trigger": "review before next reuse",
        "confidence_hint": "low reuse confidence",
        "followup_tempo": "before reuse",
        "attention_band": "hands-on",
        "response_posture": "active review",
        "reuse_gate": "blocked pending review",
        "approval_mode": "hold",
        "intervention_level": "direct",
        "oversight_level": "strict",
        "verification_mode": "full review",
        "escalation_path": "prepare now",
        "operator_checkpoint": "required",
        "trace_mode": "full trace",
        "audit_readiness": "immediate",
        "review_burden": "high",
        "documentation_mode": "expanded",
        "handoff_readiness": "immediate handoff",
        "resolution_posture": "active resolution",
        "closure_readiness": "blocked",
        "exit_path": "keep open",
        "reopen_risk": "high",
    },
}


def render_operator_learning_snapshot_section(summary: dict) -> str:
    """Render compact read-only learning snapshot from existing outcome learning summary."""
    if not summary:
        return '<ul><li class="muted">No learning snapshot available.</li></ul>'

    learning = list(summary.get("outcome_learning", []) or [])
    high_value = list(summary.get("high_value_action_patterns", []) or [])
    reopen_reduction = list(summary.get("reopen_reduction_signals", []) or [])
    mixed = list(summary.get("mixed_result_patterns", []) or [])
    reuse = list(summary.get("recommended_reuse", []) or [])

    if not learning:
        return '<ul><li class="muted">No learning snapshot available.</li></ul>'

    if len(learning) < 2 and not high_value and not reopen_reduction and not mixed:
        return '<ul><li class="muted">Insufficient learning data for operator guidance.</li></ul>'

    latest = learning[0]
    latest_scope = f"{escape(str(latest.get('scope_type', '-')))}:{escape(str(latest.get('scope_id', '-')))}"
    latest_pattern = escape(str(latest.get("action_pattern", "-")))
    latest_conf = escape(str(latest.get("confidence_level", "-")))
    latest_reuse = escape(str(latest.get("recommended_reuse", "-")))

    recent = learning[:6]
    caution_flags = [
        str(flag) for row in recent for flag in list(row.get("caution_flags", []) or [])
    ]

    guidance = "watch"
    guidance_reason = "mixed signals require monitored reuse"
    if (
        latest_conf == "low"
        or "reopen_pressure_increasing" in caution_flags
        or len(mixed) > len(high_value)
    ):
        guidance = "investigate"
        guidance_reason = "fragility/reopen pressure detected in recent learning"
    elif (
        (high_value or reopen_reduction)
        and len(mixed) == 0
        and latest_conf in {"high", "medium"}
    ):
        guidance = "keep"
        guidance_reason = "consistent positive learning signals"

    profile = _LEARNING_SNAPSHOT_GUIDANCE_PROFILE[guidance]
    priority = _LEARNING_SNAPSHOT_PRIORITY_BY_GUIDANCE[guidance]
    recommended_action = profile["recommended_action"]
    operator_note = profile["operator_note"]
    review_trigger = profile["review_trigger"]
    confidence_hint = profile["confidence_hint"]
    followup_tempo = profile["followup_tempo"]
    attention_band = profile["attention_band"]
    response_posture = profile["response_posture"]
    reuse_gate = profile["reuse_gate"]
    approval_mode = profile["approval_mode"]
    intervention_level = profile["intervention_level"]
    oversight_level = profile["oversight_level"]
    verification_mode = profile["verification_mode"]
    escalation_path = profile["escalation_path"]
    operator_checkpoint = profile["operator_checkpoint"]
    trace_mode = profile["trace_mode"]
    audit_readiness = profile["audit_readiness"]
    review_burden = profile["review_burden"]
    documentation_mode = profile["documentation_mode"]
    handoff_readiness = profile["handoff_readiness"]
    resolution_posture = profile["resolution_posture"]
    closure_readiness = profile["closure_readiness"]
    exit_path = profile["exit_path"]
    reopen_risk = profile["reopen_risk"]

    lines = [
        f"<li>Learned patterns: <strong>{escape(str(len(learning)))}</strong> | "
        f"high-value=<strong>{escape(str(len(high_value)))}</strong> | "
        f"reopen-reduction=<strong>{escape(str(len(reopen_reduction)))}</strong> | "
        f"mixed=<strong>{escape(str(len(mixed)))}</strong></li>",
        f"<li>Operator guidance: <strong>{escape(guidance)}</strong> | priority=<strong>{escape(priority)}</strong> | reason={escape(guidance_reason)}</li>",
        f"<li>Recommended action: <strong>{escape(recommended_action)}</strong></li>",
        f"<li>Operator note: <strong>{escape(operator_note)}</strong></li>",
        f"<li>Review trigger: <strong>{escape(review_trigger)}</strong></li>",
        f"<li>Confidence hint: <strong>{escape(confidence_hint)}</strong></li>",
        f"<li>Follow-up tempo: <strong>{escape(followup_tempo)}</strong></li>",
        f"<li>Attention band: <strong>{escape(attention_band)}</strong></li>",
        f"<li>Response posture: <strong>{escape(response_posture)}</strong></li>",
        f"<li>Reuse gate: <strong>{escape(reuse_gate)}</strong></li>",
        f"<li>Approval mode: <strong>{escape(approval_mode)}</strong></li>",
        f"<li>Intervention level: <strong>{escape(intervention_level)}</strong></li>",
        f"<li>Oversight level: <strong>{escape(oversight_level)}</strong></li>",
        f"<li>Verification mode: <strong>{escape(verification_mode)}</strong></li>",
        f"<li>Escalation path: <strong>{escape(escalation_path)}</strong></li>",
        f"<li>Operator checkpoint: <strong>{escape(operator_checkpoint)}</strong></li>",
        f"<li>Trace mode: <strong>{escape(trace_mode)}</strong></li>",
        f"<li>Audit readiness: <strong>{escape(audit_readiness)}</strong></li>",
        f"<li>Review burden: <strong>{escape(review_burden)}</strong></li>",
        f"<li>Documentation mode: <strong>{escape(documentation_mode)}</strong></li>",
        f"<li>Handoff readiness: <strong>{escape(handoff_readiness)}</strong></li>",
        f"<li>Resolution posture: <strong>{escape(resolution_posture)}</strong></li>",
        f"<li>Closure readiness: <strong>{escape(closure_readiness)}</strong></li>",
        f"<li>Exit path: <strong>{escape(exit_path)}</strong></li>",
        f"<li>Reopen risk: <strong>{escape(reopen_risk)}</strong></li>",
        f"<li>Latest pattern: {latest_scope} | pattern={latest_pattern} | "
        f"confidence={latest_conf} | reuse={latest_reuse}</li>",
    ]

    if reuse:
        items = "".join(
            f"<li>{escape(str(r.get('scope_type', '-')))}:{escape(str(r.get('scope_id', '-')))} "
            f"| {escape(str(r.get('action_pattern', '-')))}</li>"
            for r in reuse[:3]
        )
        lines.append(f"<li>Recommended reuse (top 3):<ul>{items}</ul></li>")
    else:
        lines.append('<li class="muted">No recommended reuse candidates yet.</li>')

    return f"<ul>{''.join(lines)}</ul>"


def render_security_status_panel(security_context) -> str:
    """Render compact read-only security context status."""
    if security_context is None:
        return '<ul><li class="muted">Security context unavailable.</li></ul>'

    key_source = str(getattr(security_context, "key_name", None) or "none")
    lines = [
        f"<li>Mode: <strong>{escape(str(getattr(security_context, 'mode', 'unknown')))}</strong></li>",
        f"<li>YubiKey present: <strong>{escape(str(bool(getattr(security_context, 'yubikey_present', False))).lower())}</strong></li>",
        f"<li>Key source: <strong>{escape(key_source)}</strong></li>",
        f"<li>Sensitive features: <strong>{escape(str(bool(getattr(security_context, 'sensitive_enabled', False))).lower())}</strong></li>",
        f"<li>Secrets unlocked: <strong>{escape(str(bool(getattr(security_context, 'secrets_unlocked', False))).lower())}</strong></li>",
    ]

    mode = str(getattr(security_context, "mode", "unknown")).strip().lower()
    session_unlocked = bool(getattr(security_context, "secrets_unlocked", False))
    lines.append(
        f"<li>Operator session: <strong>{'unlocked' if session_unlocked else 'locked'}</strong></li>"
    )

    unlock_disabled = mode != "operator" or session_unlocked
    lock_disabled = mode != "operator" or not session_unlocked

    def _control_button(label: str, runtime_command: str, disabled: bool) -> str:
        base = (
            "padding:4px 8px;border-radius:8px;border:1px solid rgba(255,255,255,.2);"
            "background:rgba(255,255,255,.06);color:var(--text);font-size:12px;"
        )
        disabled_style = "opacity:.55;cursor:not-allowed;" if disabled else ""
        disabled_attr = " disabled" if disabled else ""
        return (
            f'<button type="button" data-runtime-command="{escape(runtime_command)}"'
            f' style="{base}{disabled_style}"{disabled_attr}>{escape(label)}</button>'
        )

    controls = (
        _control_button("Unlock operator session", "session unlock", unlock_disabled)
        + " "
        + _control_button("Lock operator session", "session lock", lock_disabled)
    )
    lines.append(
        f"<li>Session controls ({'unlocked' if session_unlocked else 'locked'}): {controls}</li>"
    )
    lines.append(
        '<li class="muted">Runtime command path: Command center -> session unlock | session lock | session status</li>'
    )

    if mode == "demo":
        lines.append(
            '<li class="muted">YubiKey/operator mode is required before session controls can be used.</li>'
        )

    if mode == "operator" and not session_unlocked:
        lines.append(
            '<li class="muted">Sensitive secrets remain locked until operator session unlock.</li>'
        )
    elif mode == "operator" and session_unlocked:
        lines.append("<li>Elevated sensitive access: <strong>enabled</strong></li>")

    if mode in {"demo", "operator"}:
        action_enabled = mode == "operator" and session_unlocked
        badge_text = (
            "Operator enabled" if action_enabled else "Operator unlock required"
        )
        badge_style = (
            "display:inline-block;padding:1px 6px;border-radius:999px;"
            "font-size:11px;font-weight:600;"
            + (
                "background:rgba(255,123,123,.16);border:1px solid rgba(255,123,123,.35);color:var(--red);"
                if not action_enabled
                else "background:rgba(125,245,163,.16);border:1px solid rgba(125,245,163,.35);color:var(--green);"
            )
        )
        disabled_attr = (
            ' style="opacity:.6;text-decoration:line-through;"'
            if not action_enabled
            else ""
        )
        action_items = [
            "export context",
            "incident pack creation",
            "case writes",
            "registry writes",
        ]
        items = "".join(
            f'<li{disabled_attr}>{escape(action)} <span style="{badge_style}">{escape(badge_text)}</span></li>'
            for action in action_items
        )
        lines.append(f"<li>Operator-only actions:<ul>{items}</ul></li>")

    return f"<ul>{''.join(lines)}</ul>"


def render_security_quick_actions_panel(
    security_context,
    events: list[dict] | None = None,
    active_history_filter: str = "all",
) -> str:
    """Render compact operator-facing security quick actions."""
    if security_context is None:
        return '<ul><li class="muted">Security context unavailable.</li></ul>'

    mode = str(getattr(security_context, "mode", "unknown")).strip().lower()
    session_unlocked = bool(getattr(security_context, "secrets_unlocked", False))

    demo_mode = mode != "operator"
    unlock_disabled = demo_mode or session_unlocked
    lock_disabled = demo_mode or not session_unlocked
    generic_disabled = demo_mode
    active_history_filter = str(active_history_filter or "all").strip().lower()
    if active_history_filter not in {"all", "session", "cleanup", "audit"}:
        active_history_filter = "all"

    def _action_chip(
        label: str,
        runtime_command: str | None = None,
        disabled: bool = False,
        extra_attrs: str = "",
    ) -> str:
        base = (
            "padding:4px 9px;border-radius:999px;border:1px solid rgba(255,255,255,.16);"
            "background:rgba(255,255,255,.05);color:var(--text);font-size:11px;"
            "font-weight:600;letter-spacing:.01em;"
        )
        disabled_style = "opacity:.55;cursor:not-allowed;" if disabled else ""
        disabled_attr = " disabled" if disabled else ""
        cmd_attr = (
            f' data-runtime-command="{escape(runtime_command)}"'
            if runtime_command
            else ""
        )
        return (
            f'<button type="button"{cmd_attr}{disabled_attr} {extra_attrs}'
            f' style="{base}{disabled_style}">{escape(label)}</button>'
        )

    chips = [
        _action_chip(
            "Unlock operator session",
            runtime_command="session unlock",
            disabled=unlock_disabled,
            extra_attrs="data-security-quick-action=\"unlock\" onclick=\"showSecurityActionFeedback('Operator session unlocked', 'unlock')\"",
        ),
        _action_chip(
            "Lock operator session",
            runtime_command="session lock",
            disabled=lock_disabled,
            extra_attrs="data-security-quick-action=\"lock\" onclick=\"showSecurityActionFeedback('Operator session locked', 'lock')\"",
        ),
        _action_chip(
            "Clear expired session",
            runtime_command="session clear-expired",
            disabled=generic_disabled,
            extra_attrs="data-security-quick-action=\"clear-expired\" onclick=\"showSecurityActionFeedback('Expired session cleared', 'clear-expired')\"",
        ),
        _action_chip(
            "Open security audit view",
            disabled=generic_disabled,
            extra_attrs="data-security-quick-action=\"open-audit\" onclick=\"setSecurityAuditViewFilter('all');document.getElementById('security-audit-dedicated-view')?.scrollIntoView({behavior:'smooth', block:'start'});showSecurityActionFeedback('Security audit view opened', 'audit-view-open');\"",
        ),
    ]

    recent_actions = []
    for event in events or []:
        kind = str(event.get("kind", "")).strip().lower()
        message = str(event.get("message", "")).strip()
        message_lower = message.lower()
        ts = str(event.get("ts", "")).strip()
        label = None
        history_filter = None
        if kind == "security.operator_session.unlocked":
            label = "Operator session unlocked"
            history_filter = "session"
        elif kind in {
            "security.operator_session.locked",
            "security.operator_session.auto_locked",
        }:
            label = "Operator session locked"
            history_filter = "session"
        elif "expired session cleared" in message_lower:
            label = "Expired session cleared"
            history_filter = "cleanup"
        elif "security audit view opened" in message_lower:
            label = "Security audit view opened"
            history_filter = "audit"
        if not label:
            continue
        prefix = f'<span class="muted">{escape(ts)} - </span>' if ts else ""
        recent_actions.append(
            f'<li data-security-quick-action-history-row="{history_filter}">{prefix}{escape(label)}</li>'
        )
        if len(recent_actions) >= 5:
            break

    filtered_recent_actions = [
        item
        for item in recent_actions
        if active_history_filter == "all"
        or f'data-security-quick-action-history-row="{active_history_filter}"' in item
    ]
    visible_count = len(filtered_recent_actions[:5])
    noun = "action" if visible_count == 1 else "actions"
    if active_history_filter == "all":
        count_label = f"Showing {visible_count} recent {noun}"
    elif active_history_filter == "session":
        count_label = f"Showing {visible_count} session {noun}"
    elif active_history_filter == "cleanup":
        count_label = f"Showing {visible_count} cleanup {noun}"
    else:
        count_label = f"Showing {visible_count} audit {noun}"

    button_base = (
        "padding:2px 7px;border-radius:999px;border:1px solid rgba(255,255,255,.16);"
        "background:rgba(255,255,255,.05);color:var(--text);font-size:10px;margin-right:4px;"
        "font-weight:600;letter-spacing:.01em;"
    )
    controls = " ".join(
        (
            f'<button type="button" data-security-quick-action-history-filter="{name}" '
            f'data-security-quick-action-history-active="{"true" if name == active_history_filter else "false"}" '
            f'aria-pressed="{"true" if name == active_history_filter else "false"}" '
            f"onclick=\"setSecurityQuickActionHistoryFilter('{name}')\" "
            f'style="{button_base}{"background:rgba(125,245,163,.14);border-color:rgba(125,245,163,.35);box-shadow:inset 0 0 0 1px rgba(125,245,163,.2);" if name == active_history_filter else ""}">{escape(label)}</button>'
        )
        for name, label in (
            ("all", "all"),
            ("session", "session"),
            ("cleanup", "cleanup"),
            ("audit", "audit"),
        )
    )

    history_html = (
        f'<div style="margin-top:4px;">'
        f"Security action history filter: {controls} "
        f'active=<strong data-security-quick-action-history-active-label="{active_history_filter}">{active_history_filter}</strong>'
        f"</div>"
        f'<div class="muted" style="margin-top:3px;">'
        f'<span data-security-quick-action-history-count-label="{active_history_filter}">{escape(count_label)}</span> '
        f'<span class="muted">(max 5)</span> '
        f"<a href=\"#security-audit-dedicated-view\" data-security-quick-action-history-view-all=\"true\" onclick=\"setSecurityAuditViewFilter('{active_history_filter}');document.getElementById('security-audit-dedicated-view')?.scrollIntoView({{behavior:'smooth', block:'start'}});\" style=\"color:var(--blue);text-decoration:none;\">View all security audit events</a>"
        f"</div>"
        f'<ul style="margin-top:4px;">{"".join(filtered_recent_actions[:5])}</ul>'
        f'<div class="muted" data-security-quick-action-history-empty="true" style="display:{"none" if filtered_recent_actions else "block"};">No recent quick actions for this filter.</div>'
        if recent_actions
        else '<div class="muted">No recent quick actions.</div>'
    )

    lines = [
        f"<li>Quick actions state: <strong>{'demo-disabled' if demo_mode else ('operator-unlocked' if session_unlocked else 'operator-locked')}</strong></li>",
        f'<li style="display:flex;flex-wrap:wrap;gap:6px;">{"".join(chips)}</li>',
        '<li><div id="sec-quick-action-feedback" role="status" aria-live="polite" style="display:none;padding:3px 9px;border-radius:6px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.08);color:var(--text);font-size:11px;font-weight:600;"></div></li>',
        f'<li data-security-quick-action-history="true">Recent quick actions:{history_html}</li>',
    ]

    if demo_mode:
        lines.append(
            '<li class="muted">YubiKey/operator mode is required before quick actions can run.</li>'
        )

    return f"<ul>{''.join(lines)}</ul>"


def _security_audit_filter_key(event: dict) -> str:
    kind = str(event.get("kind", "")).strip().lower()
    message = str(event.get("message", "")).strip().lower()
    if kind == "security.operator_session.auto_locked":
        return "timeout"
    if kind == "security.sensitive_action.denied":
        return "denied"
    if kind == "security.sensitive_action.allowed":
        return "allowed"
    if "expired session cleared" in message:
        return "cleanup"
    if "security audit view opened" in message:
        return "audit"
    if kind.startswith("security.operator_session."):
        return "session"
    return "all"


def render_security_audit_events_panel(
    events: list[dict] | None, active_filter: str = "all"
) -> str:
    """Render compact recent security/operator audit events."""
    active_filter = str(active_filter or "all").strip().lower()
    if active_filter not in {"all", "session", "denied", "allowed", "timeout"}:
        active_filter = "all"

    security_events = [
        event
        for event in (events or [])
        if str(event.get("kind", "")).startswith("security.")
    ]
    filtered_events = [
        event
        for event in security_events
        if active_filter == "all" or _security_audit_filter_key(event) == active_filter
    ]

    button_base = (
        "padding:4px 9px;border-radius:999px;border:1px solid rgba(255,255,255,.16);"
        "background:rgba(255,255,255,.05);color:var(--text);font-size:11px;margin-right:4px;"
        "font-weight:600;letter-spacing:.01em;"
    )
    controls = " ".join(
        (
            f'<button type="button" data-security-audit-filter="{name}" '
            f'data-security-audit-active="{"true" if name == active_filter else "false"}" '
            f'aria-pressed="{"true" if name == active_filter else "false"}" '
            f"onclick=\"setSecurityAuditFilter('{name}')\" "
            f'style="{button_base}{"background:rgba(125,245,163,.14);border-color:rgba(125,245,163,.35);box-shadow:inset 0 0 0 1px rgba(125,245,163,.2);" if name == active_filter else ""}">{escape(label)}</button>'
        )
        for name, label in (
            ("all", "all"),
            ("session", "session"),
            ("denied", "denied"),
            ("allowed", "allowed"),
            ("timeout", "timeout"),
        )
    )

    if not filtered_events:
        body = '<ul><li class="muted">No recent security audit events.</li></ul>'
    else:
        items = []
        for event in filtered_events[:8]:
            ts = escape(str(event.get("ts", "-")))
            kind = escape(str(event.get("kind", "unknown")))
            data = event.get("data", {}) if isinstance(event.get("data"), dict) else {}
            detail = data.get("reason") or event.get("message") or "-"
            category = _security_audit_filter_key(event)
            items.append(
                f'<li data-security-audit-filter-row="{escape(category)}"><strong>{kind}</strong> | <span class="muted">{ts}</span> | {escape(str(detail))}</li>'
            )
        body = f"<ul>{''.join(items)}</ul>"

    return (
        f'<div style="margin-bottom:8px;">'
        f'<div class="muted" style="margin-bottom:6px;">Security audit filter: '
        f'<strong data-security-audit-active-label="{escape(active_filter)}">{escape(active_filter)}</strong>'
        f"</div>"
        f'<div style="display:flex;flex-wrap:wrap;gap:4px;align-items:center;">{controls}</div>'
        f"</div>{body}"
    )


def render_security_audit_dedicated_view(
    events: list[dict] | None, stamp: str = "", active_filter: str = "all"
) -> str:
    """Render dedicated security audit view with deeper recent history."""
    active_filter = str(active_filter or "all").strip().lower()
    if active_filter not in {
        "all",
        "session",
        "cleanup",
        "audit",
        "denied",
        "allowed",
        "timeout",
    }:
        active_filter = "all"

    security_events = [
        event
        for event in (events or [])
        if str(event.get("kind", "")).startswith("security.")
    ]
    filtered_events = [
        event
        for event in security_events
        if active_filter == "all" or _security_audit_filter_key(event) == active_filter
    ]

    total_counts = {
        "total": len(security_events),
        "allowed": sum(
            1
            for event in security_events
            if _security_audit_filter_key(event) == "allowed"
        ),
        "denied": sum(
            1
            for event in security_events
            if _security_audit_filter_key(event) == "denied"
        ),
        "timeout": sum(
            1
            for event in security_events
            if _security_audit_filter_key(event) == "timeout"
        ),
    }
    summary_counts = {
        "total": len(filtered_events),
        "allowed": sum(
            1
            for event in filtered_events
            if _security_audit_filter_key(event) == "allowed"
        ),
        "denied": sum(
            1
            for event in filtered_events
            if _security_audit_filter_key(event) == "denied"
        ),
        "timeout": sum(
            1
            for event in filtered_events
            if _security_audit_filter_key(event) == "timeout"
        ),
    }
    summary_html = (
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px;margin-top:10px;margin-bottom:10px;">'
        f'<div data-security-audit-summary-card="total" style="padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.04);">Total shown: <strong>{summary_counts["total"]}</strong></div>'
        f'<div data-security-audit-summary-card="allowed" style="padding:10px 12px;border-radius:12px;border:1px solid rgba(125,245,163,.18);background:rgba(125,245,163,.08);">Allowed: <strong>{summary_counts["allowed"]}</strong></div>'
        f'<div data-security-audit-summary-card="denied" style="padding:10px 12px;border-radius:12px;border:1px solid rgba(255,107,107,.18);background:rgba(255,107,107,.08);">Denied: <strong>{summary_counts["denied"]}</strong></div>'
        f'<div data-security-audit-summary-card="timeout" style="padding:10px 12px;border-radius:12px;border:1px solid rgba(255,196,87,.18);background:rgba(255,196,87,.08);">Timeout: <strong>{summary_counts["timeout"]}</strong></div>'
        "</div>"
    )
    comparison_html = (
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:8px;margin-top:4px;margin-bottom:10px;">'
        f'<div data-security-audit-comparison-card="global-total" style="padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.03);">All security events: <strong>{total_counts["total"]}</strong></div>'
        f'<div data-security-audit-comparison-card="filtered-total" style="padding:10px 12px;border-radius:12px;border:1px solid rgba(91,157,255,.18);background:rgba(91,157,255,.08);">Active filter events: <strong>{summary_counts["total"]}</strong></div>'
        f'<div data-security-audit-comparison-card="allowed-delta" style="padding:10px 12px;border-radius:12px;border:1px solid rgba(125,245,163,.18);background:rgba(125,245,163,.08);">Allowed delta: <strong>{summary_counts["allowed"] - total_counts["allowed"]:+d}</strong></div>'
        f'<div data-security-audit-comparison-card="denied-delta" style="padding:10px 12px;border-radius:12px;border:1px solid rgba(255,107,107,.18);background:rgba(255,107,107,.08);">Denied delta: <strong>{summary_counts["denied"] - total_counts["denied"]:+d}</strong></div>'
        f'<div data-security-audit-comparison-card="timeout-delta" style="padding:10px 12px;border-radius:12px;border:1px solid rgba(255,196,87,.18);background:rgba(255,196,87,.08);">Timeout delta: <strong>{summary_counts["timeout"] - total_counts["timeout"]:+d}</strong></div>'
        "</div>"
    )

    reason_counts = {}
    for event in filtered_events:
        data = event.get("data", {}) if isinstance(event.get("data"), dict) else {}
        reason = (
            str(data.get("reason") or event.get("message") or "unknown").strip()
            or "unknown"
        )
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    top_reasons = sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))[
        :3
    ]
    if top_reasons:
        reason_items = "".join(
            f'<li data-security-audit-reason-item="{escape(reason)}">{escape(reason)} <strong>×{count}</strong></li>'
            for reason, count in top_reasons
        )
        reason_html = (
            '<div data-security-audit-reason-breakdown="true" style="margin-top:6px;margin-bottom:10px;">'
            '<div class="muted" style="margin-bottom:6px;">Top audit reasons</div>'
            f'<ul style="margin:0;padding-left:18px;">{reason_items}</ul>'
            "</div>"
        )
    else:
        reason_html = (
            '<div data-security-audit-reason-breakdown="true" style="margin-top:6px;margin-bottom:10px;">'
            '<div class="muted">No audit reasons available for the active filter.</div>'
            "</div>"
        )

    chip_base = (
        "padding:4px 9px;border-radius:999px;border:1px solid rgba(255,255,255,.16);"
        "background:rgba(255,255,255,.05);color:var(--text);font-size:11px;margin-right:4px;"
        "font-weight:600;letter-spacing:.01em;"
    )
    controls = " ".join(
        (
            f'<button type="button" data-security-audit-view-filter="{name}" '
            f'data-security-audit-view-active="{"true" if name == active_filter else "false"}" '
            f'aria-pressed="{"true" if name == active_filter else "false"}" '
            f"onclick=\"setSecurityAuditViewFilter('{name}')\" "
            f'style="{chip_base}{"background:rgba(125,245,163,.14);border-color:rgba(125,245,163,.35);box-shadow:inset 0 0 0 1px rgba(125,245,163,.2);" if name == active_filter else ""}">{escape(label)}</button>'
        )
        for name, label in (
            ("all", "all"),
            ("session", "session"),
            ("cleanup", "cleanup"),
            ("audit", "audit"),
            ("denied", "denied"),
            ("allowed", "allowed"),
            ("timeout", "timeout"),
        )
    )
    reset_control = (
        f'<button type="button" data-security-audit-view-reset="true" '
        f"onclick=\"setSecurityAuditViewFilter('all')\" "
        f'style="{chip_base}">Reset filter</button>'
    )

    if not filtered_events:
        body = '<ul><li class="muted">No recent security audit events.</li></ul>'
    else:
        items = []
        for event in filtered_events[:40]:
            ts = escape(str(event.get("ts", "-")))
            kind = escape(str(event.get("kind", "unknown")))
            data = event.get("data", {}) if isinstance(event.get("data"), dict) else {}
            detail = data.get("reason") or event.get("message") or "-"
            category = _security_audit_filter_key(event)
            items.append(
                f'<li data-security-audit-view-row="{escape(category)}"><strong>{kind}</strong> | <span class="muted">{ts}</span> | {escape(str(detail))}</li>'
            )
        body = f"<ul>{''.join(items)}</ul>"

    return (
        f'<div style="margin-bottom:8px;">'
        f'<div class="muted" style="margin-bottom:6px;">Security audit view filter: '
        f'<strong data-security-audit-view-active-label="{escape(active_filter)}">{escape(active_filter)}</strong>'
        f"</div>"
        f'<div style="display:flex;flex-wrap:wrap;gap:4px;align-items:center;">{controls} {reset_control}</div>'
        f"""
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;">
          <button
            type="button"
            onclick="copySecurityAuditLink(window.location.href.split('#')[0] + '#security-audit-dedicated-view', 'Security audit view link copied')"
            style="padding:8px 12px;border-radius:10px;border:1px solid rgba(125,245,163,.25);background:rgba(125,245,163,.08);color:var(--fg);font-weight:600;cursor:pointer;"
          >Copy audit view link</button>
          <button
            type="button"
            onclick="copySecurityAuditLink('scan_{stamp}.json', 'Audit JSON link copied')"
            style="padding:8px 12px;border-radius:10px;border:1px solid rgba(91,157,255,.25);background:rgba(91,157,255,.08);color:var(--fg);font-weight:600;cursor:pointer;"
          >Copy JSON link</button>
          <button
            type="button"
            onclick="copySecurityAuditLink('scan_{stamp}.txt', 'Audit TXT link copied')"
            style="padding:8px 12px;border-radius:10px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.05);color:var(--fg);font-weight:600;cursor:pointer;"
          >Copy TXT link</button>
        </div>
        """
        f"{summary_html}"
        f"{comparison_html}"
        f"{reason_html}"
        f'<div class="muted" style="margin-top:8px;">Showing up to 40 recent security audit entries.</div>'
        f"</div>{body}"
    )


def render_watch_cases_panel(watch_cases: dict) -> str:
    """Render a compact HTML fragment for local watch/case entries."""
    if not watch_cases:
        return '<ul><li class="muted">Aucun cas enregistré (history/cases.json vide).</li></ul>'

    rows = sorted(
        watch_cases.values(), key=lambda r: r.get("updated_at", ""), reverse=True
    )[:10]
    items = "".join(
        f"<li><code>{escape(str(r.get('address', '?')))}</code> | "
        f"status=<strong>{escape(str(r.get('status', 'watch')))}</strong> | "
        f"reason={escape(str(r.get('reason', '-')))} | "
        f"updated={escape(str(r.get('updated_at', '-')))}</li>"
        for r in rows
    )
    total = len(watch_cases)
    suffix = f'<li class="muted">… {total - 10} de plus</li>' if total > 10 else ""
    return f"<ul>{items}{suffix}</ul>"


def render_session_movement_panel(movement: dict) -> str:
    """Render an HTML fragment summarising new / disappeared / recurring / score changes."""
    counts = movement.get("counts", {})
    lines = [
        f"<li>Nouveaux appareils : <strong>{counts.get('new', 0)}</strong></li>",
        f"<li>Appareils disparus : <strong>{counts.get('disappeared', 0)}</strong></li>",
        f"<li>Appareils récurrents : <strong>{counts.get('recurring', 0)}</strong></li>",
    ]

    new_devs = movement.get("new", [])[:5]
    if new_devs:
        items = "".join(
            f'<li class="new-device">{escape(str(d.get("name", "Inconnu")))} '
            f"| <code>{escape(str(d.get('address', '?')).upper())}</code></li>"
            for d in new_devs
        )
        lines.append(f"<li>Détail nouveaux (top 5) : <ul>{items}</ul></li>")

    gone_devs = movement.get("disappeared", [])[:5]
    if gone_devs:
        items = "".join(
            f'<li class="muted">{escape(str(d.get("name", "Inconnu")))} '
            f"| <code>{escape(str(d.get('address', '?')).upper())}</code></li>"
            for d in gone_devs
        )
        lines.append(f"<li>Détail disparus (top 5) : <ul>{items}</ul></li>")

    score_changes = movement.get("score_changes", [])[:5]
    if score_changes:
        items = "".join(
            f"<li>{escape(str(sc['name']))} | <code>{escape(sc['address'])}</code> "
            f"| score {sc['prev_score']} → {sc['curr_score']} "
            f"({'<span style="color:var(--green)">+' + str(sc['delta']) + '</span>' if sc['delta'] > 0 else '<span style="color:var(--red)">' + str(sc['delta']) + '</span>'})</li>"
            for sc in score_changes
        )
        lines.append(f"<li>Score changes (top 5) : <ul>{items}</ul></li>")

    if (
        not any([new_devs, gone_devs, score_changes])
        and counts.get("new", 0) == 0
        and counts.get("disappeared", 0) == 0
    ):
        lines.append(
            '<li class="muted">Aucun mouvement détecté vs scan précédent.</li>'
        )

    return f"<ul>{''.join(lines)}</ul>"


def _device_risk_level(score):
    try:
        score = int(score or 0)
    except Exception:
        score = 0

    if score >= 75:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def _device_risk_badge(score):
    level = _device_risk_level(score)

    color_map = {
        "HIGH": "#ff4d4f",
        "MEDIUM": "#faad14",
        "LOW": "#52c41a",
    }

    color = color_map[level]
    return (
        f"<span style='display:inline-block;padding:2px 8px;"
        f"border-radius:999px;font-size:12px;font-weight:700;"
        f"background:{color};color:#111;'>"
        f"{level} · {score}"
        f"</span>"
    )


def device_risk_badge(score: int) -> str:
    try:
        score = int(score or 0)
    except Exception:
        score = 0

    if score >= 75:
        level = "HIGH"
        color = "#ff4d4f"
    elif score >= 50:
        level = "MEDIUM"
        color = "#faad14"
    elif score >= 25:
        level = "LOW"
        color = "#52c41a"
    else:
        level = "SAFE"
        color = "#8c8c8c"

    return (
        f"<span style='display:inline-block;padding:2px 8px;border-radius:999px;"
        f"font-size:12px;font-weight:600;color:white;background:{color};'>"
        f"{level} ({score})"
        f"</span>"
    )


pcap_intel_devices = load_pcap_intel()
pcap_intel_html = render_ble_intel_panel(pcap_intel_devices)


def render_dashboard_html(devices, stamp: str) -> str:

    try:
        bluehood_summary = render_bluehood_summary(devices)
    except Exception:
        bluehood_summary = ""
    try:
        security_context = build_security_context()
    except Exception:
        security_context = None
    try:
        security_audit_events = read_events(25)
    except Exception:
        security_audit_events = []
    devices = [normalize_device(d) for d in devices]
    try:
        registry = load_registry()
    except Exception:
        registry = {}
    try:
        previous_devices = load_last_scan()
    except Exception:
        previous_devices = []
    movement = build_session_movement(devices, previous_devices, registry)
    try:
        watch_cases = load_watch_cases()
    except Exception:
        watch_cases = {}
    # pre-compute per-device registry scores for reuse in triage
    registry_scores = {}
    for d in devices:
        addr = str(d.get("address", "")).strip().upper()
        if addr:
            rec = registry.get(addr, {}) if isinstance(registry, dict) else {}
            registry_scores[addr] = compute_device_score(d, rec)
    triage_results = triage_device_list(
        devices,
        registry=registry,
        watch_cases=watch_cases,
        movement=movement,
        registry_scores=registry_scores,
    )
    focus_address = ""
    if triage_results:
        focus_address = str(triage_results[0].get("address", "")).strip().upper()
    elif devices:
        focus_address = str(devices[0].get("address", "")).strip().upper()

    investigation_profile = None
    if focus_address:
        investigation_profile = build_investigation_profile(
            focus_address,
            devices=devices,
            registry=registry,
            watch_cases=watch_cases,
            movement=movement,
            triage_results=triage_results,
            registry_scores=registry_scores,
        )
    try:
        workflow_summary = case_workflow_summary(watch_cases)
    except Exception:
        workflow_summary = {}
    operator_timeline = {"events": []}
    recent_operator_events = []
    if focus_address:
        try:
            operator_timeline = build_operator_timeline(
                focus_address,
                registry=registry,
                movement=movement,
                triage_results=triage_results,
            )
            recent_operator_events = recent_timeline_events(operator_timeline, limit=8)
        except Exception:
            operator_timeline = {"events": []}
            recent_operator_events = []

    operator_playbook_recommendations = []
    if focus_address:
        triage_row = None
        for row in triage_results:
            if str(row.get("address", "")).strip().upper() == focus_address:
                triage_row = row
                break
        try:
            focus_rec = recommend_operator_playbook(
                focus_address,
                triage_row=triage_row,
                investigation_profile=investigation_profile,
                case_record=watch_cases.get(focus_address, {}),
                timeline_events=operator_timeline.get("events", []),
            )
            operator_playbook_recommendations.append(
                {
                    "address": focus_address,
                    **focus_rec,
                }
            )
        except Exception:
            pass

    for row in triage_results[:5]:
        addr = str(row.get("address", "")).strip().upper()
        if not addr or addr == focus_address:
            continue
        try:
            rec = recommend_operator_playbook(
                addr,
                triage_row=row,
                case_record=watch_cases.get(addr, {}),
            )
            operator_playbook_recommendations.append(
                {
                    "address": addr,
                    **rec,
                }
            )
        except Exception:
            continue

    playbook_by_address = {
        str(r.get("address", "")).strip().upper(): r
        for r in operator_playbook_recommendations
        if isinstance(r, dict)
    }

    operator_rule_results = []

    if focus_address:
        triage_row = next(
            (
                r
                for r in triage_results
                if str(r.get("address", "")).strip().upper() == focus_address
            ),
            None,
        )
        try:
            rows = evaluate_operator_rules(
                focus_address,
                playbook_recommendation=playbook_by_address.get(focus_address),
                case_record=watch_cases.get(focus_address, {}),
                timeline_events=operator_timeline.get("events", []),
                triage_row=triage_row,
                investigation_profile=investigation_profile,
                apply_auto=True,
                persist_log=False,
            )
            operator_rule_results.extend(
                [{"address": focus_address, **r} for r in rows]
            )
        except Exception:
            pass

    for row in triage_results[:5]:
        addr = str(row.get("address", "")).strip().upper()
        if not addr or addr == focus_address:
            continue
        try:
            rows = evaluate_operator_rules(
                addr,
                playbook_recommendation=playbook_by_address.get(addr),
                case_record=watch_cases.get(addr, {}),
                triage_row=row,
                apply_auto=True,
                persist_log=False,
            )
            operator_rule_results.extend([{"address": addr, **r} for r in rows])
        except Exception:
            continue

    operator_rule_summary = summarize_rule_results(operator_rule_results)
    try:
        recent_rule_log_events = load_automation_events(limit=8)
    except Exception:
        recent_rule_log_events = []

    operator_briefing = build_operator_briefing(
        triage_results=triage_results,
        investigation_profile=investigation_profile,
        workflow_summary=workflow_summary,
        timeline_events=recent_operator_events,
        playbook_recommendations=operator_playbook_recommendations,
        rule_summary=operator_rule_summary,
        rule_log_events=recent_rule_log_events,
    )

    pending_by_address = {}
    for row in operator_rule_summary.get("pending_confirmations", []):
        addr = str(row.get("address", "")).strip().upper()
        if not addr:
            continue
        pending_by_address[addr] = pending_by_address.get(addr, 0) + 1

    operator_alerts = []
    alert_addresses = []
    if focus_address:
        alert_addresses.append(focus_address)
    for row in triage_results[:5]:
        addr = str(row.get("address", "")).strip().upper()
        if addr and addr not in alert_addresses:
            alert_addresses.append(addr)

    for addr in alert_addresses:
        triage_row = next(
            (
                r
                for r in triage_results
                if str(r.get("address", "")).strip().upper() == addr
            ),
            None,
        )
        rule_rows = [
            r
            for r in operator_rule_results
            if str(r.get("address", "")).strip().upper() == addr
        ]
        timeline_rows = recent_operator_events if addr == focus_address else []
        inv_profile = investigation_profile if addr == focus_address else None

        try:
            rows = build_operator_alerts(
                addr,
                triage_row=triage_row,
                investigation_profile=inv_profile,
                case_record=watch_cases.get(addr, {}),
                timeline_events=timeline_rows,
                playbook_recommendation=playbook_by_address.get(addr),
                rule_results=rule_rows,
                pending_confirmations_count=pending_by_address.get(addr, 0),
                persist_log=False,
            )
            operator_alerts.extend(rows)
        except Exception:
            continue

    try:
        recent_alert_log_events = load_alert_log(limit=12)
    except Exception:
        recent_alert_log_events = []

    operator_alert_summary = summarize_alerts(
        operator_alerts,
        recent_log_events=recent_alert_log_events,
    )

    correlation_timeline_by_address = {}
    if focus_address and operator_timeline.get("events"):
        correlation_timeline_by_address[focus_address] = operator_timeline.get(
            "events", []
        )

    investigation_profiles = {}
    if focus_address and investigation_profile:
        investigation_profiles[focus_address] = investigation_profile

    correlation_clusters = build_correlation_clusters(
        devices,
        movement=movement,
        triage_results=triage_results,
        investigation_profiles=investigation_profiles,
        watch_cases=watch_cases,
        workflow_summary=workflow_summary,
        timeline_by_address=correlation_timeline_by_address,
        playbook_recommendations=operator_playbook_recommendations,
        alerts=operator_alerts,
    )
    correlation_summary = summarize_clusters(correlation_clusters)

    try:
        previous_campaigns = load_campaign_records()
    except Exception:
        previous_campaigns = []

    campaign_rows = build_campaign_lifecycle(
        correlation_clusters,
        previous_campaigns=previous_campaigns,
        stamp=stamp,
        persist=False,
    )
    campaign_summary = summarize_campaigns(campaign_rows)

    artifact_index = build_artifact_index()

    evidence_packs = build_evidence_packs(
        focus_address=focus_address,
        watch_cases=watch_cases,
        investigation_profile=investigation_profile,
        workflow_summary=workflow_summary,
        timeline_events=recent_operator_events,
        playbook_recommendations=operator_playbook_recommendations,
        rule_summary=operator_rule_summary,
        briefing=operator_briefing,
        alerts=operator_alerts,
        clusters=correlation_clusters,
        campaigns=campaign_rows,
        artifact_index=artifact_index,
        generated_at=stamp,
        persist=False,
    )
    try:
        persisted_evidence_packs = load_evidence_packs(limit=12)
    except Exception:
        persisted_evidence_packs = []
    evidence_summary = summarize_evidence_packs(
        evidence_packs,
        persisted_packs=persisted_evidence_packs,
    )

    operator_queue_items = build_operator_queue(
        triage_results=triage_results,
        workflow_summary=workflow_summary,
        pending_confirmations=operator_rule_summary.get("pending_confirmations", []),
        alerts=operator_alerts,
        briefing=operator_briefing,
        clusters=correlation_clusters,
        campaigns=campaign_rows,
        evidence_packs=evidence_packs,
        watch_cases=watch_cases,
        stamp=stamp,
    )
    operator_queue_summary = summarize_operator_queue(operator_queue_items)

    queue_health_snapshot = build_queue_health_snapshot(
        operator_queue_items,
        workflow_summary=workflow_summary,
        pending_confirmations=operator_rule_summary.get("pending_confirmations", []),
        alerts=operator_alerts,
        campaigns=campaign_rows,
        evidence_packs=evidence_packs,
        generated_at=stamp,
    )
    queue_health_summary = summarize_queue_health(
        queue_health_snapshot,
        operator_queue_items,
    )

    operator_outcomes = build_operator_outcomes(
        operator_queue_items,
        workflow_summary=workflow_summary,
        playbook_recommendations=operator_playbook_recommendations,
        rule_results=operator_rule_results,
        alerts=operator_alerts,
        campaigns=campaign_rows,
        evidence_packs=evidence_packs,
        queue_health_snapshot=queue_health_snapshot,
        generated_at=stamp,
    )
    operator_outcomes_summary = summarize_operator_outcomes(operator_outcomes)

    recommendation_profiles = build_recommendation_tuning_profiles(
        operator_outcomes,
        playbook_recommendations=operator_playbook_recommendations,
        rule_results=operator_rule_results,
        alerts=operator_alerts,
        queue_items=operator_queue_items,
        campaigns=campaign_rows,
        evidence_packs=evidence_packs,
        generated_at=stamp,
    )
    recommendation_tuning_summary = summarize_recommendation_tuning_profiles(
        recommendation_profiles
    )

    review_readiness_profiles = build_review_readiness_profiles(
        operator_queue_items,
        evidence_packs=evidence_packs,
        queue_health_snapshot=queue_health_snapshot,
        outcomes=operator_outcomes,
        alerts=operator_alerts,
        timeline_events=recent_operator_events,
        campaigns=campaign_rows,
        workflow_summary=workflow_summary,
        investigation_profile=investigation_profile,
        generated_at=stamp,
    )
    review_readiness_summary = summarize_review_readiness(review_readiness_profiles)

    operator_session_journal = build_operator_session_journal(
        queue_items=operator_queue_items,
        campaigns=campaign_rows,
        alerts=operator_alerts,
        outcomes=operator_outcomes,
        readiness_profiles=review_readiness_profiles,
        evidence_packs=evidence_packs,
        queue_health_snapshot=queue_health_snapshot,
        generated_at=stamp,
    )
    operator_session_journal_summary = summarize_operator_session_journal(
        operator_session_journal,
        queue_items=operator_queue_items,
        outcomes=operator_outcomes,
        readiness_profiles=review_readiness_profiles,
    )

    operator_patterns = build_operator_pattern_records(
        outcomes=operator_outcomes,
        recommendation_profiles=recommendation_profiles,
        alerts=operator_alerts,
        campaigns=campaign_rows,
        clusters=correlation_clusters,
        queue_items=operator_queue_items,
        readiness_profiles=review_readiness_profiles,
        session_journal=operator_session_journal,
        generated_at=stamp,
    )

    current_pattern_scopes = []
    for row in operator_queue_items:
        current_pattern_scopes.append(
            {
                "scope_type": str(row.get("scope_type", "device")),
                "scope_id": str(row.get("scope_id", "-")),
                "queue_state": str(row.get("queue_state", "new")),
            }
        )
        current_pattern_scopes.append(
            {
                "scope_type": "queue_item",
                "scope_id": str(row.get("item_id", "-")),
                "queue_state": str(row.get("queue_state", "new")),
            }
        )

    for row in campaign_rows:
        current_pattern_scopes.append(
            {
                "scope_type": "campaign",
                "scope_id": str(row.get("campaign_id", "-")),
                "status": str(row.get("status", "new")),
            }
        )

    for row in correlation_clusters:
        current_pattern_scopes.append(
            {
                "scope_type": "cluster",
                "scope_id": str(row.get("cluster_id", row.get("id", "-"))),
                "status": str(row.get("status", "active")),
            }
        )

    for row in evidence_packs:
        current_pattern_scopes.append(
            {
                "scope_type": "evidence_pack",
                "scope_id": str(row.get("pack_id", row.get("scope_id", "-"))),
                "status": str(row.get("pack_state", "ready")),
            }
        )

    for row in review_readiness_profiles[:10]:
        current_pattern_scopes.append(
            {
                "scope_type": str(row.get("scope_type", "device")),
                "scope_id": str(row.get("scope_id", "-")),
                "readiness_state": str(row.get("readiness_state", "not_ready")),
            }
        )

    operator_pattern_matches = match_scopes_to_patterns(
        current_pattern_scopes, operator_patterns
    )
    operator_pattern_summary = summarize_operator_pattern_library(
        operator_patterns,
        matches=operator_pattern_matches,
    )

    current_escalation_scopes = []
    for row in operator_queue_items:
        current_escalation_scopes.append(
            {
                "scope_type": str(row.get("scope_type", "device")),
                "scope_id": str(row.get("scope_id", "-")),
                "queue_state": str(row.get("queue_state", "new")),
            }
        )
        current_escalation_scopes.append(
            {
                "scope_type": "queue_item",
                "scope_id": str(row.get("item_id", "-")),
                "queue_state": str(row.get("queue_state", "new")),
            }
        )

    for row in campaign_rows:
        current_escalation_scopes.append(
            {
                "scope_type": "campaign",
                "scope_id": str(row.get("campaign_id", "-")),
                "status": str(row.get("status", "new")),
            }
        )

    for row in correlation_clusters:
        current_escalation_scopes.append(
            {
                "scope_type": "cluster",
                "scope_id": str(row.get("cluster_id", row.get("id", "-"))),
                "status": str(row.get("status", "active")),
            }
        )

    for row in evidence_packs:
        current_escalation_scopes.append(
            {
                "scope_type": "evidence_pack",
                "scope_id": str(row.get("pack_id", row.get("scope_id", "-"))),
                "status": str(row.get("pack_state", "ready")),
            }
        )

    for row in review_readiness_profiles[:10]:
        current_escalation_scopes.append(
            {
                "scope_type": str(row.get("scope_type", "device")),
                "scope_id": str(row.get("scope_id", "-")),
                "readiness_state": str(row.get("readiness_state", "not_ready")),
            }
        )

    operator_escalation_packages = build_operator_escalation_packages(
        current_escalation_scopes,
        alerts=operator_alerts,
        outcomes=operator_outcomes,
        recommendation_profiles=recommendation_profiles,
        queue_items=operator_queue_items,
        queue_health_snapshot=queue_health_snapshot,
        readiness_profiles=review_readiness_profiles,
        evidence_packs=evidence_packs,
        campaigns=campaign_rows,
        pattern_matches=operator_pattern_matches,
        session_journal=operator_session_journal,
        generated_at=stamp,
    )
    operator_escalation_summary = summarize_operator_escalation_packages(
        operator_escalation_packages
    )

    operator_escalation_feedback = build_operator_escalation_feedback_records(
        operator_escalation_packages,
        readiness_profiles=review_readiness_profiles,
        outcomes=operator_outcomes,
        recommendation_profiles=recommendation_profiles,
        queue_items=operator_queue_items,
        queue_health_snapshot=queue_health_snapshot,
        evidence_packs=evidence_packs,
        session_journal=operator_session_journal,
        pattern_matches=operator_pattern_matches,
        generated_at=stamp,
    )
    operator_escalation_feedback_summary = summarize_operator_escalation_feedback(
        operator_escalation_feedback
    )

    current_closure_scopes = []
    for row in operator_queue_items:
        current_closure_scopes.append(
            {
                "scope_type": str(row.get("scope_type", "device")),
                "scope_id": str(row.get("scope_id", "-")),
                "queue_state": str(row.get("queue_state", "new")),
            }
        )
        current_closure_scopes.append(
            {
                "scope_type": "queue_item",
                "scope_id": str(row.get("item_id", "-")),
                "queue_state": str(row.get("queue_state", "new")),
            }
        )

    for row in campaign_rows:
        current_closure_scopes.append(
            {
                "scope_type": "campaign",
                "scope_id": str(row.get("campaign_id", "-")),
                "status": str(row.get("status", "new")),
            }
        )

    for row in correlation_clusters:
        current_closure_scopes.append(
            {
                "scope_type": "cluster",
                "scope_id": str(row.get("cluster_id", row.get("id", "-"))),
                "status": str(row.get("status", "active")),
            }
        )

    for row in evidence_packs:
        current_closure_scopes.append(
            {
                "scope_type": "evidence_pack",
                "scope_id": str(row.get("pack_id", row.get("scope_id", "-"))),
                "status": str(row.get("pack_state", "ready")),
            }
        )

    for row in review_readiness_profiles[:10]:
        current_closure_scopes.append(
            {
                "scope_type": str(row.get("scope_type", "device")),
                "scope_id": str(row.get("scope_id", "-")),
                "readiness_state": str(row.get("readiness_state", "not_ready")),
            }
        )

    operator_closure_packages = build_operator_closure_packages(
        current_closure_scopes,
        escalation_feedback=operator_escalation_feedback,
        escalation_packages=operator_escalation_packages,
        readiness_profiles=review_readiness_profiles,
        outcomes=operator_outcomes,
        recommendation_profiles=recommendation_profiles,
        queue_items=operator_queue_items,
        queue_health_snapshot=queue_health_snapshot,
        evidence_packs=evidence_packs,
        pattern_matches=operator_pattern_matches,
        session_journal=operator_session_journal,
        generated_at=stamp,
    )
    operator_closure_summary = summarize_operator_closure_packages(
        operator_closure_packages
    )

    current_monitoring_scopes = []
    for row in operator_queue_items:
        current_monitoring_scopes.append(
            {
                "scope_type": str(row.get("scope_type", "device")),
                "scope_id": str(row.get("scope_id", "-")),
                "queue_state": str(row.get("queue_state", "new")),
            }
        )
        current_monitoring_scopes.append(
            {
                "scope_type": "queue_item",
                "scope_id": str(row.get("item_id", "-")),
                "queue_state": str(row.get("queue_state", "new")),
            }
        )

    for row in campaign_rows:
        current_monitoring_scopes.append(
            {
                "scope_type": "campaign",
                "scope_id": str(row.get("campaign_id", "-")),
                "status": str(row.get("status", "new")),
            }
        )

    for row in correlation_clusters:
        current_monitoring_scopes.append(
            {
                "scope_type": "cluster",
                "scope_id": str(row.get("cluster_id", row.get("id", "-"))),
                "status": str(row.get("status", "active")),
            }
        )

    for row in evidence_packs:
        current_monitoring_scopes.append(
            {
                "scope_type": "evidence_pack",
                "scope_id": str(row.get("pack_id", row.get("scope_id", "-"))),
                "status": str(row.get("pack_state", "ready")),
            }
        )

    for row in review_readiness_profiles[:10]:
        current_monitoring_scopes.append(
            {
                "scope_type": str(row.get("scope_type", "device")),
                "scope_id": str(row.get("scope_id", "-")),
                "readiness_state": str(row.get("readiness_state", "not_ready")),
            }
        )

    operator_monitoring_policies = build_operator_post_closure_monitoring_policies(
        current_monitoring_scopes,
        closure_packages=operator_closure_packages,
        escalation_feedback=operator_escalation_feedback,
        outcomes=operator_outcomes,
        recommendation_profiles=recommendation_profiles,
        pattern_matches=operator_pattern_matches,
        campaign_records=campaign_rows,
        queue_health_snapshot=queue_health_snapshot,
        alerts_history=operator_alerts,
        review_readiness=review_readiness_profiles,
        session_journal=operator_session_journal,
        generated_at=stamp,
    )
    operator_monitoring_summary = summarize_operator_post_closure_monitoring_policies(
        operator_monitoring_policies
    )

    operator_reopen_records = build_operator_reopen_records(
        current_monitoring_scopes,
        closure_packages=operator_closure_packages,
        post_closure_monitoring_policies=operator_monitoring_policies,
        escalation_feedback=operator_escalation_feedback,
        outcomes=operator_outcomes,
        pattern_library=operator_patterns,
        queue_health_snapshot=queue_health_snapshot,
        alerts_history=operator_alerts,
        campaign_tracking=campaign_rows,
        evidence_packs=evidence_packs,
        session_journal=operator_session_journal,
        generated_at=stamp,
    )
    operator_reopen_summary = summarize_operator_reopen_records(operator_reopen_records)

    operator_lineage_records = build_operator_lifecycle_lineage_records(
        current_monitoring_scopes,
        outcomes=operator_outcomes,
        closure_packages=operator_closure_packages,
        post_closure_monitoring_policies=operator_monitoring_policies,
        reopen_policy_records=operator_reopen_records,
        escalation_packages=operator_escalation_packages,
        escalation_feedback=operator_escalation_feedback,
        session_journal=operator_session_journal,
        pattern_library=operator_patterns,
        pattern_matches=operator_pattern_matches,
        operator_queue_context=operator_queue_items,
        campaign_tracking=campaign_rows,
        evidence_packs=evidence_packs,
        generated_at=stamp,
    )
    operator_lineage_summary = summarize_operator_lifecycle_lineage(
        operator_lineage_records
    )

    operator_quality_records = build_operator_resolution_quality_records(
        current_monitoring_scopes,
        lineage_records=operator_lineage_records,
        closure_packages=operator_closure_packages,
        reopen_policy_records=operator_reopen_records,
        post_closure_monitoring_policies=operator_monitoring_policies,
        operator_outcomes=operator_outcomes,
        escalation_feedback=operator_escalation_feedback,
        recommendation_tuning=recommendation_profiles,
        pattern_library=operator_patterns,
        pattern_matches=operator_pattern_matches,
        operator_queue_context=operator_queue_items,
        session_journal=operator_session_journal,
        generated_at=stamp,
    )
    operator_quality_summary = summarize_operator_resolution_quality(
        operator_quality_records
    )

    operator_plan_records = build_operator_improvement_plan_records(
        current_monitoring_scopes,
        quality_records=operator_quality_records,
        lineage_records=operator_lineage_records,
        closure_packages=operator_closure_packages,
        reopen_policy_records=operator_reopen_records,
        post_closure_monitoring_policies=operator_monitoring_policies,
        escalation_feedback=operator_escalation_feedback,
        operator_outcomes=operator_outcomes,
        recommendation_tuning=recommendation_profiles,
        pattern_library=operator_patterns,
        session_journal=operator_session_journal,
        generated_at=stamp,
    )
    operator_plan_summary = summarize_operator_improvement_plans(operator_plan_records)
    tracking_exposure_rows = []
    operator_learning_records = build_operator_outcome_learning_records(
        current_monitoring_scopes,
        resolution_quality_records=operator_quality_records,
        improvement_plans=operator_plan_records,
        lifecycle_lineage=operator_lineage_records,
        operator_outcomes=operator_outcomes,
        closure_packages=operator_closure_packages,
        reopen_policy_records=operator_reopen_records,
        post_closure_monitoring_policies=operator_monitoring_policies,
        escalation_feedback=operator_escalation_feedback,
        recommendation_tuning=recommendation_profiles,
        pattern_library=operator_patterns,
        generated_at=stamp,
    )
    operator_learning_summary = summarize_operator_outcome_learning(
        operator_learning_records
    )
    history = load_scan_history()[-8:]
    recent_observations = {}

    for idx, scan in enumerate(history[-12:]):
        for observed in scan.get("devices", []):
            addr = str(observed.get("address", "")).strip().upper()
            if not addr or addr == "-":
                continue
            recent_observations.setdefault(addr, []).append(
                {
                    "scan_pos": idx,
                    "name": observed.get("name", ""),
                    "rssi": observed.get("rssi"),
                    "stamp": scan.get("stamp") or scan.get("timestamp") or "",
                }
            )

    for d in devices:
        addr = str(d.get("address", "")).strip().upper()
        if not addr or addr == "-":
            continue
        summary = build_tracking_exposure_summary(
            d,
            registry_row=registry.get(addr, {}),
            observations=recent_observations.get(addr, []),
        )
        tracking_exposure_rows.append(
            {
                "address": addr,
                "name": d.get("name", "Inconnu"),
                **summary,
            }
        )

    previous = history[-1] if history else None

    critical = [d for d in devices if d.get("alert_level") == "critique"]
    high = [d for d in devices if d.get("alert_level") == "élevé"]
    medium = [d for d in devices if d.get("alert_level") == "moyen"]
    watch_hits = [d for d in devices if d.get("watch_hit")]
    top_hot = sorted(devices, key=lambda d: d.get("final_score", 0), reverse=True)[:10]
    top_trackers = get_tracker_candidates(devices)[:10]
    vendor_counts = get_vendor_summary(devices)[:8]
    cases = list_cases()[:5]
    latest_diff = latest_session_diff()
    recent_sessions = build_session_catalog(limit=5)
    latest_session = latest_session_overview()

    trend_rows = []
    for row in history:
        trend_rows.append(
            f"<tr><td>{escape(str(row.get('stamp', '-')))}</td>"
            f"<td>{_safe_int(row.get('count', 0))}</td>"
            f"<td>{_safe_int(row.get('critical', 0))}</td>"
            f"<td>{_safe_int(row.get('high', 0))}</td>"
            f"<td>{_safe_int(row.get('medium', 0))}</td></tr>"
        )

    normalized_vendor_counts = []
    for item in vendor_counts:
        if isinstance(item, dict):
            name = str(item.get("vendor", "Unknown"))
            count = int(item.get("count", 0) or 0)
        else:
            name = str(item[0])
            count = int(item[1] or 0)
        normalized_vendor_counts.append((name, count))

    vendor_bars = []
    max_vendor = normalized_vendor_counts[0][1] if normalized_vendor_counts else 1

    for name, count in normalized_vendor_counts:
        pct = int((count / max_vendor) * 100) if max_vendor else 0
        vendor_bars.append(
            f"""
            <div class="bar-row">
              <div class="bar-label">{escape(str(name))}</div>
              <div class="bar-wrap"><div class="bar-fill" style="width:{pct}%"></div></div>
              <div class="bar-count">{count}</div>
            </div>
            """
        )

    vendor_options = ['<option value="">Tous</option>']
    for name, _ in normalized_vendor_counts:
        vendor_options.append(
            f'<option value="{escape(str(name))}">{escape(str(name))}</option>'
        )

    hot_list = []
    for d in top_hot:
        hot_list.append(
            f"<li>{escape(str(d.get('name', 'Inconnu')))} "
            f"<span class='muted'>{escape(str(d.get('address', '-')))}</span> "
            f"(score {_safe_int(d.get('final_score', 0))})</li>"
        )

    tracker_list = []
    for d in top_trackers:
        tracker_list.append(
            f"<li>{escape(str(d.get('name', 'Inconnu')))} "
            f"<span class='muted'>{escape(str(d.get('address', '-')))}</span></li>"
        )

    case_list = []
    for case in cases:
        case_list.append(
            f"<li>{escape(str(case.get('title', case.get('address', 'Case'))))} "
            f"<span class='muted'>status={escape(str(case.get('status', '-')))}</span></li>"
        )

    latest_session_lines = [
        f"<li>Stamp: {escape(str(latest_session.get('stamp', 'unknown')))}</li>",
        f"<li>Devices: {escape(str(latest_session.get('device_count', 0)))}</li>",
        f"<li>Critical: {escape(str(latest_session.get('critical', 0)))}</li>",
        f"<li>Watch hits: {escape(str(latest_session.get('watch_hits', 0)))}</li>",
        f"<li>Trackers: {escape(str(latest_session.get('tracker_candidates', 0)))}</li>",
        f"<li>Top vendor: {escape(str(latest_session.get('top_vendor', 'Unknown')))}</li>",
        f"<li>Top device: {escape(str(latest_session.get('top_device_name', 'Inconnu')))} ({escape(str(latest_session.get('top_device_score', 0)))})</li>",
    ]

    recent_session_lines = []
    for row in recent_sessions:
        recent_session_lines.append(
            f"<li>{escape(str(row.get('stamp', 'unknown')))} | "
            f"devices={escape(str(row.get('device_count', 0)))} | "
            f"critical={escape(str(row.get('critical', 0)))} | "
            f"watch_hits={escape(str(row.get('watch_hits', 0)))} | "
            f"trackers={escape(str(row.get('tracker_candidates', 0)))} | "
            f"top_vendor={escape(str(row.get('top_vendor', 'Unknown')))}</li>"
        )

    artifact_lines = [
        f"<li>Scan manifests: {escape(str(artifact_index.get('scan_manifests', {}).get('count', 0)))} | latest={escape(str(artifact_index.get('scan_manifests', {}).get('latest', 'none') or 'none'))}</li>",
        f"<li>Session diff reports: {escape(str(artifact_index.get('session_diff_reports', {}).get('count', 0)))} | latest={escape(str(artifact_index.get('session_diff_reports', {}).get('latest', 'none') or 'none'))}</li>",
        f"<li>Export contexts: {escape(str(artifact_index.get('export_contexts', {}).get('count', 0)))} | latest={escape(str(artifact_index.get('export_contexts', {}).get('latest', 'none') or 'none'))}</li>",
        f"<li>Incident packs: {escape(str(artifact_index.get('incident_packs', {}).get('count', 0)))} | latest={escape(str(artifact_index.get('incident_packs', {}).get('latest', 'none') or 'none'))}</li>",
    ]

    registry_lines = []
    for d in devices[:10]:
        addr = str(d.get("address", "")).upper().strip()
        if not addr or addr == "-":
            continue
        rec = registry.get(addr, {}) if isinstance(registry, dict) else {}
        reg_score = compute_device_score(d, rec)
        registry_lines.append(
            f"<li>{escape(str(d.get('name', 'Inconnu')))} | "
            f"<code>{escape(addr)}</code> | "
            f"first_seen={escape(str(rec.get('first_seen', '-')))} | "
            f"last_seen={escape(str(rec.get('last_seen', '-')))} | "
            f"seen_count={escape(str(rec.get('seen_count', 0)))} | "
            f"session_count={escape(str(rec.get('session_count', 0)))} | "
            f"registry_score={escape(str(reg_score))}</li>"
        )

    if latest_diff.get("has_diff"):
        diff_lines = [
            f"<li>Previous: {escape(str(latest_diff.get('previous_stamp', '-')))}</li>",
            f"<li>Current: {escape(str(latest_diff.get('current_stamp', '-')))}</li>",
            f"<li>Devices delta: {escape(str(latest_diff.get('device_count_delta', 0)))}</li>",
            f"<li>Critical delta: {escape(str(latest_diff.get('critical_delta', 0)))}</li>",
            f"<li>Watch hits delta: {escape(str(latest_diff.get('watch_hits_delta', 0)))}</li>",
            f"<li>Trackers delta: {escape(str(latest_diff.get('tracker_candidates_delta', 0)))}</li>",
            f"<li>Top vendor: {escape(str(latest_diff.get('previous_top_vendor', 'Unknown')))} -> {escape(str(latest_diff.get('current_top_vendor', 'Unknown')))}</li>",
            f"<li>Top device: {escape(str(latest_diff.get('previous_top_device', 'Inconnu')))} -> {escape(str(latest_diff.get('current_top_device', 'Inconnu')))}</li>",
        ]
    else:
        diff_lines = ['<li class="muted">Aucun diff comparable disponible</li>']

    comparison_lines = [
        f"<li>Total: {len(devices)} ({_delta_label(len(devices), previous.get('count') if previous else None)} vs précédent)</li>",
        f"<li>Critiques: {len(critical)} ({_delta_label(len(critical), previous.get('critical') if previous else None)} vs précédent)</li>",
        f"<li>Élevés: {len(high)} ({_delta_label(len(high), previous.get('high') if previous else None)} vs précédent)</li>",
        f"<li>Moyens: {len(medium)} ({_delta_label(len(medium), previous.get('medium') if previous else None)} vs précédent)</li>",
    ]

    incident_lines = [
        f"<li>Critiques visibles: {len(critical)}</li>",
        f"<li>Élevés visibles: {len(high)}</li>",
        f"<li>Watchlist Hits: {len(watch_hits)}</li>",
        f"<li>Trackers probables: {len(top_trackers)}</li>",
    ]

    rows = []
    for d in devices:
        css = "normal"
        if d.get("alert_level") == "critique":
            css = "critical"
        elif d.get("alert_level") == "élevé":
            css = "high"
        elif d.get("alert_level") == "moyen":
            css = "medium"

        flags = d.get("flags", [])
        explanation = explain_device(d)["summary"]
        addr = str(d.get("address", "")).strip().upper()
        registry_row = registry.get(addr, {}) if isinstance(registry, dict) else {}
        behavior_summary = build_compact_device_behavior_summary(
            d,
            registry_row=registry_row,
            observations=recent_observations.get(addr, []),
        )
        device_interest = compute_device_interest_score(
            d,
            registry_row=registry_row,
            observations=recent_observations.get(addr, []),
        )
        interest_score = device_risk_badge(device_interest.get("score", 0))
        anomaly_flags = detect_device_anomaly_flags(
            d,
            registry_row=registry_row,
            observations=recent_observations.get(addr, []),
        )
        live_alerts = detect_device_live_alerts(
            d,
            registry_row=registry_row,
            observations=recent_observations.get(addr, []),
        )
        device_profile = build_compact_device_profile(
            d,
            registry_row=registry_row,
            observations=recent_observations.get(addr, []),
        )
        explanation_block = escape(explanation)
        interest_label = str(device_interest.get("label", "normal"))
        interest_style = {
            "normal": "background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.20);",
            "interesting": "background:rgba(255,209,102,.16);border:1px solid rgba(255,209,102,.38);",
            "suspicious": "background:rgba(255,123,123,.16);border:1px solid rgba(255,123,123,.38);",
        }.get(
            interest_label,
            "background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.20);",
        )
        interest_text = (
            f"interest {escape(str(device_interest.get('score', 0)))} · {escape(interest_label)}"
            + (
                f" (+{escape(str(device_interest.get('anomaly_boost', 0)))} anomaly)"
                if _safe_int(device_interest.get("anomaly_boost", 0), 0) > 0
                else ""
            )
        )
        explanation_block += (
            f'<div class="muted" data-device-interest-badge="true" '
            f'data-device-interest-label="{escape(interest_label)}" '
            f'data-device-interest-score="{escape(str(device_interest.get("score", 0)))}" '
            f'data-device-interest-boost="{escape(str(device_interest.get("anomaly_boost", 0)))}" '
            f'style="margin-top:3px;display:inline-block;padding:1px 7px;border-radius:999px;font-size:10px;font-weight:700;{interest_style}">'
            f"{interest_text}"
            f"</div>"
        )
        if anomaly_flags:
            anomaly_items = " ".join(
                f'<span style="display:inline-block;padding:1px 6px;border-radius:999px;'
                f"border:1px solid rgba(255,123,123,.40);background:rgba(255,123,123,.14);"
                f'font-size:10px;font-weight:700;margin-right:4px;">{escape(flag)}</span>'
                for flag in anomaly_flags
            )
            explanation_block += (
                f'<div class="muted" data-device-anomaly-flags="true" style="margin-top:3px;">'
                f"{anomaly_items}"
                f"</div>"
            )
        if live_alerts:
            alert_text = " | ".join(escape(msg) for msg in live_alerts)
            explanation_block += (
                f'<div class="muted" data-device-live-alerts="true" '
                f'style="margin-top:3px;color:var(--yellow);font-weight:700;">'
                f"{alert_text}"
                f"</div>"
            )
        profile_text = (
            f"profile sightings={escape(str(device_profile.get('total_sightings', 0)))}"
            f" | anomalies={escape(str(device_profile.get('anomaly_count', 0)))}"
            f" | last_risk={escape(str(device_profile.get('last_risk', 'normal')))}"
            f" | trust={escape(str(device_profile.get('trust_level', 'low')))}"
        )
        explanation_block += (
            f'<div class="muted" data-device-profile="true" style="margin-top:3px;">'
            f"{profile_text}"
            f"</div>"
        )
        if behavior_summary:
            explanation_block += (
                f'<div class="muted" data-device-behavior-summary="true">'
                f"{escape(behavior_summary)}"
                f"</div>"
            )
        is_tracker = (
            "true"
            if (
                d.get("possible_suivi")
                or d.get("watch_hit")
                or "tracker" in str(d.get("profile", "")).lower()
            )
            else "false"
        )
        is_watch = "true" if d.get("watch_hit") else "false"

        rows.append(
            f"""
        <tr class="{css}" data-alert="{escape(str(d.get("alert_level", "faible")))}"
            data-vendor="{escape(str(d.get("vendor", "Unknown")))}"
            data-watch="{is_watch}"
            data-tracker="{is_tracker}">
            <td>{escape(str(d.get("name", "Inconnu")))}</td>
            <td>{escape(str(d.get("address", "-")))}</td>
            <td>{escape(str(d.get("vendor", "Unknown")))}</td>
            <td>{escape(str(d.get("profile", "general_ble")))}</td>
            <td>{escape(str(d.get("rssi", "-")))}</td>
            <td>{escape(str(d.get("risk_score", 0)))}</td>
            <td>{escape(str(d.get("follow_score", 0)))}</td>
            <td>{escape(str(d.get("confidence_score", 0)))}</td>
            <td>{escape(str(d.get("final_score", 0)))}</td>
            <td>{escape(str(d.get("alert_level", "faible")))}</td>
            <td>{escape(str(d.get("seen_count", 0)))}</td>
            <td>{escape(",".join(flags) if flags else "-")}</td>
            <td>{explanation_block}</td>
            <td>{escape(str(d.get("reason_short", "normal")))}</td>
        </tr>
        """
        )


    pcap_intel_devices = load_pcap_intel()
    pcap_intel_html = render_ble_intel_panel(pcap_intel_devices)
    omega_core_html = render_omega_core_panel(pcap_intel_devices)
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BLE Radar Omega AI - Dashboard Pro - {escape(stamp)}</title>
<style>
:root {{
  --bg:#08111e; --panel:#111b2c; --border:#2a3b58; --text:#d7e4f4;
  --blue:#70b7ff; --green:#7df5a3; --yellow:#ffd166; --red:#ff7b7b; --pink:#ff4fa3;
}}
body {{ background:var(--bg); color:var(--text); font-family:ui-monospace,Consolas,monospace; margin:0; padding:24px; }}
h1,h2 {{ color:var(--blue); }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin-bottom:18px; }}
.card {{ background:var(--panel); border:1px solid var(--border); border-radius:16px; padding:16px; }}
.big {{ font-size:28px; font-weight:700; margin-top:8px; }}
.grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-bottom:18px; }}
.panel {{ background:var(--panel); border:1px solid var(--border); border-radius:16px; padding:16px; }}
input,button,select {{
  background:#0d1523; color:var(--text); border:1px solid var(--border);
  border-radius:10px; padding:10px 12px; margin-right:8px; margin-bottom:8px;
}}
button {{ cursor:pointer; }}
table {{ width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--border); border-radius:16px; overflow:hidden; }}
th, td {{ padding:10px 12px; border-bottom:1px solid rgba(255,255,255,.08); text-align:left; }}
th {{ color:var(--blue); position:sticky; top:0; background:#0f1a2b; }}
tr.critical {{ background:rgba(255,79,163,.16); }}
tr.high {{ background:rgba(255,123,123,.10); }}
tr.medium {{ background:rgba(255,209,102,.10); }}
tr.normal {{ background:rgba(125,245,163,.06); }}
.table-wrap {{ max-height:65vh; overflow:auto; border-radius:16px; }}
.bar-row {{ display:grid; grid-template-columns:140px 1fr 50px; gap:10px; align-items:center; margin-bottom:8px; }}
.bar-wrap {{ background:#0d1523; border:1px solid var(--border); border-radius:999px; height:14px; overflow:hidden; }}
.bar-fill {{ background:linear-gradient(90deg,var(--blue),var(--green)); height:100%; }}
ul {{ margin:0; padding-left:18px; }}
.muted {{ opacity:.78; }}
.small-table td,.small-table th {{ padding:8px 10px; }}
</style>
</head>
<body>
<section class="omega-section">
    <h2>🧠 OMEGA BLE Intel</h2>
    <div class="omega-grid">
        {pcap_intel_html}
    </div>
</section>

<section class="omega-section">
    <h2>🧠 OMEGA CORE (preview)</h2>
    <div class="omega-grid">
        {omega_core_html}
    </div>
</section>
  <h1>BLE Radar Omega AI - Dashboard Pro</h1>
  <h2>Résumé global</h2>

  <div class="cards">
    <div class="card"><div>Total</div><div class="big">{len(devices)}</div></div>
    <div class="card"><div>Critiques</div><div class="big">{len(critical)}</div></div>
    <div class="card"><div>Élevés</div><div class="big">{len(high)}</div></div>
    <div class="card"><div>Moyens</div><div class="big">{len(medium)}</div></div>
    <div class="card"><div>Watchlist Hits</div><div class="big">{
    len(watch_hits)
}</div></div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>Résumé comparatif</h2>
      <ul>{"".join(comparison_lines)}</ul>
      <div class="muted">Horodatage : {escape(stamp)}</div>
    </div>
    <div class="panel">
      <h2>Incidents visibles</h2>
      <ul>{"".join(incident_lines)}</ul>
      <div class="muted">Vue rapide des signaux prioritaires du scan courant.</div>
    </div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>Cas d'investigation récents</h2>
      <ul>{
    "".join(case_list) if case_list else '<li class="muted">Aucun cas récent</li>'
}</ul>
    </div>
    <div class="panel">
      <h2>Top trackers probables ({len(top_trackers)})</h2>
      <ul>{
    "".join(tracker_list) if tracker_list else '<li class="muted">Aucun</li>'
}</ul>
    </div>
    <div class="panel">
      <h2>Répartition vendors</h2>
      {
    "".join(vendor_bars) if vendor_bars else '<div class="muted">Aucune donnée</div>'
}
    </div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Session diff récent</h2>
    <ul>{"".join(diff_lines)}</ul>
    <div class="muted">Résumé du dernier manifest comparé au précédent.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Artifact index</h2>
    <ul>{"".join(artifact_lines)}</ul>
    <div class="muted">Vue rapide des artefacts locaux générés.</div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>Latest session overview</h2>
      <ul>{"".join(latest_session_lines)}</ul>
    </div>
    <div class="panel">
      <h2>Sessions récentes</h2>
      <ul>{
    "".join(recent_session_lines)
    if recent_session_lines
    else '<li class="muted">Aucune session récente</li>'
}</ul>
    </div>
  </div>

    <div class="panel" style="margin-bottom:18px;">
        <h2>Security status</h2>
        {render_security_status_panel(security_context)}
        <div class="muted">Runtime security context snapshot.</div>
    </div>

    <div class="panel" style="margin-bottom:18px;">
        <h2>Security quick actions</h2>
        {render_security_quick_actions_panel(security_context, security_audit_events)}
        <div class="muted">Operator-facing session and audit shortcuts.</div>
    </div>

    <div class="panel" id="security-audit-panel" style="margin-bottom:18px;">
        <h2>Security audit events</h2>
        {render_security_audit_events_panel(security_audit_events)}
        <div class="muted">Recent operator/security audit activity.</div>
    </div>

    <div class="panel" id="security-audit-dedicated-view" style="margin-bottom:18px;">
        <h2>Security audit view (dedicated)</h2>
        {render_security_audit_dedicated_view(security_audit_events, stamp)}
        <div class="muted">Dedicated operator security audit inspection view.</div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;">
          <a
            href="{escape(f"scan_{stamp}.json")}"
            style="display:inline-flex;align-items:center;justify-content:center;padding:8px 12px;border-radius:10px;border:1px solid rgba(125,245,163,.25);background:rgba(125,245,163,.08);color:var(--fg);text-decoration:none;font-weight:600;"
          >Open audit JSON artifact</a>
          <a
            href="{escape(f"scan_{stamp}.txt")}"
            download
            style="display:inline-flex;align-items:center;justify-content:center;padding:8px 12px;border-radius:10px;border:1px solid rgba(91,157,255,.25);background:rgba(91,157,255,.08);color:var(--fg);text-decoration:none;font-weight:600;"
          >Export audit TXT artifact</a>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;">
          <a
            href="{escape(f"operator_panel_{stamp}.html")}"
            style="display:inline-flex;align-items:center;justify-content:center;padding:8px 12px;border-radius:10px;border:1px solid rgba(125,245,163,.25);background:rgba(125,245,163,.08);color:var(--fg);text-decoration:none;font-weight:600;"
          >Open paired operator panel</a>
          <button
            type="button"
            onclick="setSecurityAuditViewFilter('all')"
            style="padding:8px 12px;border-radius:10px;border:1px solid rgba(91,157,255,.25);background:rgba(91,157,255,.08);color:var(--fg);font-weight:600;cursor:pointer;"
          >Reset audit filter</button>
        </div>
    </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Device registry snapshot</h2>
    <ul>{
    "".join(registry_lines)
    if registry_lines
    else '<li class="muted">Aucune donnée registry disponible</li>'
}</ul>
    <div class="muted">Aperçu local des appareils du scan courant (top 10).</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Session movement summary</h2>
    {render_session_movement_panel(movement)}
    <div class="muted">Comparaison appareil par appareil avec le scan précédent.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Watch / Cases</h2>
    {render_watch_cases_panel(watch_cases)}
    <div class="muted">Appareils sous surveillance locale (history/cases.json).</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Operator Triage Priority</h2>
    {render_triage_panel(triage_results)}
    <div class="muted">Score de triage opérateur par appareil (top 15, signaux combinés).</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Investigation Workspace (Focused Device)</h2>
    {render_investigation_profile_panel(investigation_profile)}
    <div class="muted">Profil compact unifié pour un appareil prioritaire.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Operator Case Workflow</h2>
    {render_case_workflow_panel(workflow_summary)}
    <div class="muted">Suivi des cas opérateur : ouverts, en investigation, action requise, résolus récents.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Operator Timeline (Focused Device)</h2>
    {render_operator_timeline_panel(recent_operator_events)}
    <div class="muted">Événements opérateur récents unifiés (registry, workflow, mouvement, triage, packs).</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Operator Playbook Recommendations</h2>
    {render_operator_playbook_panel(operator_playbook_recommendations)}
    <div class="muted">Recommandations d'action opérateur (focus + top triage).</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Operator Rule Engine (Safe Auto-Actions)</h2>
    {render_operator_rule_engine_panel(operator_rule_summary, recent_rule_log_events)}
    <div class="muted">Actions auto-appliquées, confirmations en attente et règles récemment matchées.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Operator Briefing / Shift Handoff</h2>
    {render_operator_briefing_panel(operator_briefing)}
    <div class="muted">Briefing compact de relève opérateur (priorités, actions et prochaines étapes).</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Operator Alerting & Escalation</h2>
    {render_operator_alerting_panel(operator_alert_summary)}
    <div class="muted">Alertes actives, escalades récentes et éléments en revue immédiate.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Correlation Clusters / Campaign View</h2>
    {render_operator_correlation_panel(correlation_summary)}
    <div class="muted">Clusters corrélés, appareils possiblement coordonnés et revue de cluster.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Campaign Tracking / Cluster Lifecycle</h2>
    {render_operator_campaign_panel(campaign_summary)}
    <div class="muted">Campagnes actives, clusters récurrents, groupes en expansion et revue opérateur.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Evidence Pack / Consolidated Operator Dossier</h2>
    {render_operator_evidence_panel(evidence_summary)}
    <div class="muted">Evidence packs récents, dossiers prêts à revue et synthèse campagne.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Operator Queue / Case Board</h2>
    {render_operator_queue_panel(operator_queue_summary)}
    <div class="muted">File opérateur, revue, blocages, actions prêtes et résolutions récentes.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Operator Queue Health / Aging / Bottlenecks</h2>
    {render_operator_queue_health_panel(queue_health_summary)}
    <div class="muted">Santé de file, vieillissement, blocages, stale items et pression opérateur.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Operator Outcomes / Feedback Loop</h2>
    {render_operator_outcomes_panel(operator_outcomes_summary)}
    <div class="muted">Outcomes opérateur, actions efficaces, réouvertures et recommandations faibles.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Learning snapshot</h2>
    {render_operator_learning_snapshot_section(operator_learning_summary)}
    <div class="muted">Synthèse compacte read-only de l'apprentissage outcome, réutilisation suggérée et niveau de confiance.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Recommendation Tuning / Operator Confidence</h2>
    {render_recommendation_tuning_panel(recommendation_tuning_summary)}
    <div class="muted">Confidence des recommandations, playbooks efficaces, recommandations faibles et revue manuelle.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Review Readiness / Readiness Gate</h2>
    {render_review_readiness_panel(review_readiness_summary)}
    <div class="muted">État de readiness pour review, handoff et archive selon les signaux opérateur.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Operator Session Journal / Shift Continuity</h2>
    {render_operator_session_journal_panel(operator_session_journal_summary)}
    <div class="muted">Journal de session courant, activité de shift, carry-over et priorités de relève.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Operator Pattern Library / Recurring Case Memory</h2>
    {render_operator_pattern_library_panel(operator_pattern_summary)}
    <div class="muted">Patterns connus, types récurrents, matches probables et guidance basée sur mémoire opérateur.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Operator Escalation Packages / Transmission</h2>
    {render_operator_escalation_package_panel(operator_escalation_summary)}
    <div class="muted">Packages d'escalade compacts, prêts à transmission avec signaux, risques et ownership recommandé.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Operator Escalation Feedback / Specialist Return</h2>
    {render_operator_escalation_feedback_panel(operator_escalation_feedback_summary)}
    <div class="muted">Feedback specialist return, décisions de suivi et recommandations de clôture.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Operator Closure Packages / Final Resolution</h2>
    {render_operator_closure_package_panel(operator_closure_summary)}
    <div class="muted">Packages de clôture compacts, résolution finale et recommandations d'archive/follow-up.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Post-Closure Monitoring / Recurrence Watch</h2>
    {render_operator_post_closure_monitoring_policy_panel(operator_monitoring_summary)}
    <div class="muted">Politiques de monitoring post-clôture, observation de récurrence et rouverture potentielle.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Controlled Reopen Policy / Case Reopening</h2>
    {render_operator_reopen_policy_panel(operator_reopen_summary)}
    <div class="muted">Réouvertures compactes, triggers récents, retour en file et suivi des réouvertures répétées.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Lifecycle Lineage / Multi-Cycle History</h2>
    {render_operator_lifecycle_lineage_panel(operator_lineage_summary)}
    <div class="muted">Lignée compacte des cycles opérateur, réouvertures répétées, triggers récurrents et stabilisation.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Resolution Quality / Stability Assessment</h2>
    {render_operator_resolution_quality_panel(operator_quality_summary)}
    <div class="muted">Évaluation compacte de la qualité des résolutions, stabilité, risque de réouverture et suggestions d'amélioration.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Resolution Improvement Plans / Corrective Guidance</h2>
    {render_operator_improvement_plan_panel(operator_plan_summary)}
    <div class="muted">Plans d'amélioration compacts, actions recommandées, lacunes bloquantes et modes de suivi.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Outcome Learning / Historical Effectiveness Feedback</h2>
    {render_operator_outcome_learning_panel(operator_learning_summary)}
    <div class="muted">Apprentissage compact des patterns d'action, efficacité historique, signaux de réduction des réouvertures et recommandations de réutilisation.</div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>Filtres rapides</h2>
      <input id="searchBox" placeholder="Recherche nom / adresse / vendor">
      <select id="vendorSelect">
        {"".join(vendor_options)}
      </select>
      <div>
        <button onclick="setMode('all')">Tout</button>
        <button onclick="setMode('critique')">Critique</button>
        <button onclick="setMode('élevé')">Élevé</button>
        <button onclick="setMode('moyen')">Moyen</button>
        <button onclick="setMode('watch')">Watch hits</button>
        <button onclick="setMode('tracker')">Trackers</button>
      </div>
    </div>
    <div class="panel">
      <h2>Tendance des derniers scans</h2>
      <table class="small-table">
        <thead>
          <tr><th>Scan</th><th>Total</th><th>Critiques</th><th>Élevés</th><th>Moyens</th></tr>
        </thead>
        <tbody>
          {
    "".join(trend_rows)
    if trend_rows
    else '<tr><td colspan="5" class="muted">Aucun historique</td></tr>'
}
        </tbody>
      </table>
    </div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Tableau détaillé des appareils</h2>
    <div class="muted">Vue complète des appareils détectés, scorés et filtrables.</div>
  </div>

  <div class="table-wrap">
    <table id="deviceTable">
      <thead>
        <tr>
          <th>Nom</th>
          <th>Adresse</th>
          <th>Vendor</th>
          <th>Profil</th>
          <th>RSSI</th>
          <th>Risk</th>
          <th>Follow</th>
          <th>Confidence</th>
          <th>Final</th>
          <th>Alerte</th>
          <th>Seen</th>
          <th>Flags</th>
          <th>Explication</th>
          <th>Raison</th>
        </tr>
      </thead>
      <tbody>
        {"".join(rows)}
      </tbody>
    </table>
  </div>

<script>
const searchBox = document.getElementById('searchBox');
const vendorSelect = document.getElementById('vendorSelect');
let activeMode = 'all';

function rowMatchesMode(tr) {{
  if (activeMode === 'all') return true;
  if (activeMode === 'watch') return tr.dataset.watch === 'true';
  if (activeMode === 'tracker') return tr.dataset.tracker === 'true';
  return tr.dataset.alert === activeMode;
}}

function applyFilters() {{
  const q = searchBox.value.toLowerCase();
  const vendor = vendorSelect.value;

  document.querySelectorAll('#deviceTable tbody tr').forEach(tr => {{
    const txt = tr.innerText.toLowerCase();
    const okText = txt.includes(q);
    const okVendor = !vendor || tr.dataset.vendor === vendor;
    const okMode = rowMatchesMode(tr);
    tr.style.display = okText && okVendor && okMode ? '' : 'none';
  }});
}}

function setMode(mode) {{
  activeMode = mode;
  applyFilters();
}}

const SECURITY_AUDIT_FILTER_STORAGE_KEY = 'bleRadarSecurityAuditFilter';

function normalizeSecurityAuditFilter(mode) {{
    return ['all', 'session', 'cleanup', 'audit'].includes(mode) ? mode : 'all';
}}

function loadPersistedSecurityAuditFilter() {{
    try {{
        return normalizeSecurityAuditFilter(
            window.localStorage.getItem(SECURITY_AUDIT_FILTER_STORAGE_KEY) || 'all'
        );
    }} catch (_err) {{
        return 'all';
    }}
}}

function persistSecurityAuditFilter(mode) {{
    const normalized = normalizeSecurityAuditFilter(mode);
    try {{
        window.localStorage.setItem(SECURITY_AUDIT_FILTER_STORAGE_KEY, normalized);
    }} catch (_err) {{
        // Ignore storage errors in local static dashboard mode.
    }}
    return normalized;
}}

function applySecurityAuditFilterButtons(mode) {{
    document.querySelectorAll('[data-security-audit-filter]').forEach(btn => {{
        const active = btn.dataset.securityAuditFilter === mode;
        btn.dataset.securityAuditActive = active ? 'true' : 'false';
        btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        btn.style.background = active ? 'rgba(125,245,163,.14)' : 'rgba(255,255,255,.05)';
        btn.style.borderColor = active ? 'rgba(125,245,163,.35)' : 'rgba(255,255,255,.16)';
        btn.style.boxShadow = active ? 'inset 0 0 0 1px rgba(125,245,163,.2)' : 'none';
    }});

    document.querySelectorAll('[data-security-audit-view-filter]').forEach(btn => {{
        const active = btn.dataset.securityAuditViewFilter === mode;
        btn.dataset.securityAuditViewActive = active ? 'true' : 'false';
        btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        btn.style.background = active ? 'rgba(125,245,163,.14)' : 'rgba(255,255,255,.05)';
        btn.style.borderColor = active ? 'rgba(125,245,163,.35)' : 'rgba(255,255,255,.16)';
        btn.style.boxShadow = active ? 'inset 0 0 0 1px rgba(125,245,163,.2)' : 'none';
    }});
}}

function applySecurityAuditFilterLabels(mode) {{
    const activeLabel = document.querySelector('[data-security-audit-active-label]');
    if (activeLabel) {{
        activeLabel.textContent = mode;
        activeLabel.dataset.securityAuditActiveLabel = mode;
    }}

    const activeViewLabel = document.querySelector('[data-security-audit-view-active-label]');
    if (activeViewLabel) {{
        activeViewLabel.textContent = mode;
        activeViewLabel.dataset.securityAuditViewActiveLabel = mode;
    }}
}}

function applySecurityAuditFilterRows(mode) {{
    document.querySelectorAll('[data-security-audit-filter-row]').forEach(row => {{
        row.style.display = mode === 'all' || row.dataset.securityAuditFilterRow === mode ? '' : 'none';
    }});

    document.querySelectorAll('[data-security-audit-view-row]').forEach(row => {{
        row.style.display = mode === 'all' || row.dataset.securityAuditViewRow === mode ? '' : 'none';
    }});
}}

function syncSecurityAuditFilterUi(mode) {{
    const normalized = normalizeSecurityAuditFilter(mode);
    applySecurityAuditFilterButtons(normalized);
    applySecurityAuditFilterLabels(normalized);
    applySecurityAuditFilterRows(normalized);
}}

function setSecurityAuditFilter(mode) {{
    syncSecurityAuditFilterUi(persistSecurityAuditFilter(mode));
}}

function copySecurityAuditLink(target, label) {{
    let absoluteHref = String(target);
    try {{
        absoluteHref = new URL(target, window.location.href).href;
    }} catch (_err) {{}}

    try {{
        if (navigator.clipboard && navigator.clipboard.writeText) {{
            navigator.clipboard.writeText(absoluteHref);
            if (typeof showSecurityActionFeedback === 'function') {{
                showSecurityActionFeedback(label || 'Audit link copied', 'audit-link-copied');
            }}
            return;
        }}
    }} catch (_err) {{}}

    const textarea = document.createElement('textarea');
    textarea.value = absoluteHref;
    textarea.setAttribute('readonly', 'readonly');
    textarea.style.position = 'absolute';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    try {{
        document.execCommand('copy');
        if (typeof showSecurityActionFeedback === 'function') {{
            showSecurityActionFeedback(label || 'Audit link copied', 'audit-link-copied');
        }}
    }} finally {{
        document.body.removeChild(textarea);
    }}
}}

function setSecurityAuditViewFilter(mode) {{
    syncSecurityAuditFilterUi(persistSecurityAuditFilter(mode));
}}

window.addEventListener('DOMContentLoaded', () => {{
    syncSecurityAuditFilterUi(loadPersistedSecurityAuditFilter());
}});

function setSecurityQuickActionHistoryFilter(mode) {{
    document.querySelectorAll('[data-security-quick-action-history-filter]').forEach(btn => {{
        const active = btn.dataset.securityQuickActionHistoryFilter === mode;
        btn.dataset.securityQuickActionHistoryActive = active ? 'true' : 'false';
        btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        btn.style.background = active ? 'rgba(125,245,163,.14)' : 'rgba(255,255,255,.05)';
        btn.style.borderColor = active ? 'rgba(125,245,163,.35)' : 'rgba(255,255,255,.16)';
        btn.style.boxShadow = active ? 'inset 0 0 0 1px rgba(125,245,163,.2)' : 'none';
    }});

    const activeLabel = document.querySelector('[data-security-quick-action-history-active-label]');
    if (activeLabel) {{
        activeLabel.textContent = mode;
        activeLabel.dataset.securityQuickActionHistoryActiveLabel = mode;
    }}

    let visibleRows = 0;
    document.querySelectorAll('[data-security-quick-action-history-row]').forEach(row => {{
        const visible = mode === 'all' || row.dataset.securityQuickActionHistoryRow === mode;
        row.style.display = visible ? '' : 'none';
        if (visible) visibleRows += 1;
    }});

    const emptyState = document.querySelector('[data-security-quick-action-history-empty="true"]');
    if (emptyState) {{
        emptyState.style.display = visibleRows === 0 ? 'block' : 'none';
    }}

    const countLabel = document.querySelector('[data-security-quick-action-history-count-label]');
    if (countLabel) {{
        const noun = visibleRows === 1 ? 'action' : 'actions';
        let text = `Showing ${{visibleRows}} recent ${{noun}}`;
        if (mode === 'session') text = `Showing ${{visibleRows}} session ${{noun}}`;
        else if (mode === 'cleanup') text = `Showing ${{visibleRows}} cleanup ${{noun}}`;
        else if (mode === 'audit') text = `Showing ${{visibleRows}} audit ${{noun}}`;
        countLabel.textContent = text;
        countLabel.dataset.securityQuickActionHistoryCountLabel = mode;
    }}
}}

function showSecurityActionFeedback(msg, actionKey) {{
    var el = document.getElementById('sec-quick-action-feedback');
    if (!el) return;
    var toneByAction = {{
        'unlock': 'success',
        'lock': 'warning',
        'audit-view-open': 'info',
        'clear-expired': 'neutral',
    }};
    var tone = toneByAction[actionKey] || 'info';
    var styles = {{
        success: {{
            background: 'rgba(125,245,163,.16)',
            borderColor: 'rgba(125,245,163,.38)',
            color: 'var(--text)',
        }},
        warning: {{
            background: 'rgba(255,193,107,.16)',
            borderColor: 'rgba(255,193,107,.38)',
            color: 'var(--text)',
        }},
        info: {{
            background: 'rgba(125,208,255,.16)',
            borderColor: 'rgba(125,208,255,.38)',
            color: 'var(--text)',
        }},
        neutral: {{
            background: 'rgba(255,255,255,.08)',
            borderColor: 'rgba(255,255,255,.22)',
            color: 'var(--text)',
        }},
    }};
    var style = styles[tone] || styles.info;
    el.textContent = msg;
    el.style.background = style.background;
    el.style.borderColor = style.borderColor;
    el.style.color = style.color;
    el.style.display = 'inline-block';
    clearTimeout(el._t);
    el._t = setTimeout(function() {{ el.style.display = 'none'; }}, 3500);
}}

searchBox.addEventListener('input', applyFilters);
vendorSelect.addEventListener('change', applyFilters);
setSecurityAuditFilter('all');
setSecurityAuditViewFilter('all');
setSecurityQuickActionHistoryFilter('all');
</script>

<!-- BLUEHOOD SUMMARY -->
{bluehood_summary}

</body>
</html>
"""


def render_bluehood_summary(
    devices, registry=None, session_id="dashboard-session", seen_at="now"
):
    try:
        enriched = enrich_devices_for_session(
            devices=devices or [],
            registry=registry or {},
            session_id=session_id,
            seen_at=seen_at,
        )
    except Exception as exc:
        return f"""
<section class="panel">
  <h2>Bluehood Summary</h2>
  <ul>
    <li><strong>Status:</strong> error</li>
    <li><strong>Reason:</strong> {escape(str(exc))}</li>
  </ul>
</section>
"""

    correlated_pairs = []
    watch_hits = []

    for item in devices or []:
        if not isinstance(item, dict):
            continue
        address = escape(str(item.get("address", "?")))
        name = escape(str(item.get("name", "Unknown")))

        pair = item.get("correlated_pair") or item.get("correlated_with")
        if pair:
            correlated_pairs.append(
                f"<li>{address} ↔ {escape(str(pair))} (score: {item.get('score', 0)})</li>"
            )
        else:
            correlated_pairs.append(
                f"<li>{name} ({address}) — score: {item.get('score', 0)}</li>"
            )

        watch_hits.append(f"<li>{name} ({address})</li>")

    correlated_html = "".join(correlated_pairs) or "<li>None</li>"
    watch_hits_html = "".join(watch_hits) or "<li>None</li>"

    return f"""
<section class="panel">
  <h2>Bluehood Summary</h2>
  <div class="kv"><strong>Total devices:</strong> {len(enriched or [])}</div>
  <h3>Top correlated</h3>
  <ul>
    {correlated_html}
  </ul>
  <h3>Watch hits details</h3>
  <ul>
    {watch_hits_html}
  </ul>
</section>
"""


def render_alert_history_panel():
    alerts = get_recent_alerts()

    html = "<section class='panel'><h3>Alert History</h3><ul>"

    for a in reversed(alerts):
        html += (
            f"<li>{a['timestamp']} | {a['device']} | {a['score']} | {a['profile']}</li>"
        )

    html += "</ul></section>"
    return html
