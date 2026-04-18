from ble_radar.bluehood_layer import enrich_devices_for_session
from html import escape

from ble_radar.device_contract import explain_device, normalize_device
from ble_radar.intel import get_tracker_candidates, get_vendor_summary
from ble_radar.investigation import list_cases
from ble_radar.session_diff import latest_session_diff
from ble_radar.session_catalog import build_session_catalog, latest_session_overview
from ble_radar.artifact_index import build_artifact_index
from ble_radar.history.device_registry import load_registry
from ble_radar.history.device_scoring import compute_device_score
from ble_radar.history.cases import load_cases as load_watch_cases
from ble_radar.history.case_workflow import case_workflow_summary, next_action
from ble_radar.history.investigation_workspace import build_investigation_profile
from ble_radar.history.operator_alerting import build_operator_alerts, load_alert_log, summarize_alerts
from ble_radar.history.operator_briefing import build_operator_briefing
from ble_radar.history.operator_campaign_tracking import build_campaign_lifecycle, load_campaign_records, summarize_campaigns
from ble_radar.history.operator_correlation import build_correlation_clusters, summarize_clusters
from ble_radar.history.operator_evidence_pack import build_evidence_packs, load_evidence_packs, summarize_evidence_packs
from ble_radar.history.operator_outcomes import build_operator_outcomes, summarize_operator_outcomes
from ble_radar.history.operator_playbook import recommend_operator_playbook
from ble_radar.history.operator_queue import build_operator_queue, summarize_operator_queue
from ble_radar.history.operator_queue_health import build_queue_health_snapshot, summarize_queue_health
from ble_radar.history.operator_session_journal import build_operator_session_journal, summarize_operator_session_journal
from ble_radar.history.recommendation_tuning import (
  build_recommendation_tuning_profiles,
  summarize_recommendation_tuning_profiles,
)
from ble_radar.history.review_readiness import build_review_readiness_profiles, summarize_review_readiness
from ble_radar.history.operator_rule_engine import (
  evaluate_operator_rules,
  load_automation_events,
  summarize_rule_results,
)
from ble_radar.history.operator_timeline import build_operator_timeline, recent_timeline_events
from ble_radar.history.triage import triage_device_list
from ble_radar.session.session_movement import build_session_movement
from ble_radar.state import load_last_scan, load_scan_history


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


_BUCKET_STYLE = {
    "critical": "color:var(--pink);font-weight:700",
    "review":   "color:var(--red)",
    "watch":    "color:var(--yellow)",
    "normal":   "color:var(--green)",
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
            f"<li style=\"{style}\">"
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
        return '<ul><li class="muted">Aucun profil d\'investigation disponible.</li></ul>'

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
        f"<li>Triage: <strong>{escape(str(triage.get('triage_bucket', 'normal')).upper())}</strong> | score={escape(str(triage.get('triage_score', 0)))} | reason={escape(str(triage.get('short_reason', 'no signals')))}</li>",
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
        f"En cours d\'investigation : <strong>{len(investigating)}</strong> | "
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
        f"<li><span class=\"muted\">{escape(str(e.get('timestamp') or 'n/a'))}</span> | "
        f"<strong>{escape(str(e.get('source', '?')))}</strong> | "
        f"{escape(str(e.get('summary', '-')))}</li>"
        for e in events
    )
    return f"<ul>{items}</ul>"


def render_operator_playbook_panel(recommendations: list) -> str:
    """Render compact operator playbook recommendations."""
    if not recommendations:
        return '<ul><li class="muted">Aucune recommandation opérateur disponible.</li></ul>'

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
    pending_rows = summary.get("pending_confirmations", []) if isinstance(summary, dict) else []
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
            f"<li><span class=\"muted\">{escape(str(e.get('timestamp', '-')))}</span> "
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
        f"<li><span class=\"muted\">{escape(str(a.get('created_at', '-')))}</span> "
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
      return '<ul><li class="muted">Aucun cluster de corrélation disponible.</li></ul>'

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
        reasons_html = "<ul>" + "".join(f"<li>{escape(str(r))}</li>" for r in reasons[:5]) + "</ul>"
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


def render_watch_cases_panel(watch_cases: dict) -> str:
    """Render a compact HTML fragment for local watch/case entries."""
    if not watch_cases:
        return '<ul><li class="muted">Aucun cas enregistré (history/cases.json vide).</li></ul>'

    rows = sorted(watch_cases.values(), key=lambda r: r.get("updated_at", ""), reverse=True)[:10]
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
            f"<li class=\"new-device\">{escape(str(d.get('name', 'Inconnu')))} "
            f"| <code>{escape(str(d.get('address', '?')).upper())}</code></li>"
            for d in new_devs
        )
        lines.append(f"<li>Détail nouveaux (top 5) : <ul>{items}</ul></li>")

    gone_devs = movement.get("disappeared", [])[:5]
    if gone_devs:
        items = "".join(
            f"<li class=\"muted\">{escape(str(d.get('name', 'Inconnu')))} "
            f"| <code>{escape(str(d.get('address', '?')).upper())}</code></li>"
            for d in gone_devs
        )
        lines.append(f"<li>Détail disparus (top 5) : <ul>{items}</ul></li>")

    score_changes = movement.get("score_changes", [])[:5]
    if score_changes:
        items = "".join(
            f"<li>{escape(str(sc['name']))} | <code>{escape(sc['address'])}</code> "
            f"| score {sc['prev_score']} → {sc['curr_score']} "
            f"({'<span style=\"color:var(--green)\">+' + str(sc['delta']) + '</span>' if sc['delta'] > 0 else '<span style=\"color:var(--red)\">' + str(sc['delta']) + '</span>'})</li>"
            for sc in score_changes
        )
        lines.append(f"<li>Score changes (top 5) : <ul>{items}</ul></li>")

    if not any([new_devs, gone_devs, score_changes]) and counts.get("new", 0) == 0 and counts.get("disappeared", 0) == 0:
        lines.append('<li class="muted">Aucun mouvement détecté vs scan précédent.</li>')

    return f"<ul>{''.join(lines)}</ul>"


def render_dashboard_html(devices, stamp: str) -> str:
    bluehood_summary = render_bluehood_summary(devices)
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
        operator_playbook_recommendations.append({
          "address": focus_address,
          **focus_rec,
        })
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
        operator_playbook_recommendations.append({
          "address": addr,
          **rec,
        })
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
        (r for r in triage_results if str(r.get("address", "")).strip().upper() == focus_address),
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
        operator_rule_results.extend([{"address": focus_address, **r} for r in rows])
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
        (r for r in triage_results if str(r.get("address", "")).strip().upper() == addr),
        None,
      )
      rule_rows = [r for r in operator_rule_results if str(r.get("address", "")).strip().upper() == addr]
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
      correlation_timeline_by_address[focus_address] = operator_timeline.get("events", [])

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
    recommendation_tuning_summary = summarize_recommendation_tuning_profiles(recommendation_profiles)

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

    history = load_scan_history()[-8:]
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

    vendor_bars = []
    max_vendor = vendor_counts[0][1] if vendor_counts else 1
    for name, count in vendor_counts:
        pct = int((count / max_vendor) * 100) if max_vendor else 0
        vendor_bars.append(
            f"""
        <div class="bar-row">
            <div class="bar-label">{escape(name)}</div>
            <div class="bar-wrap"><div class="bar-fill" style="width:{pct}%"></div></div>
            <div class="bar-count">{count}</div>
        </div>
        """
        )

    vendor_options = ['<option value="">Tous les vendors</option>']
    for name, _ in vendor_counts:
        vendor_options.append(f'<option value="{escape(str(name))}">{escape(str(name))}</option>')

    hot_list = []
    for d in top_hot:
        hot_list.append(
            f"<li>{escape(str(d.get('name', 'Inconnu')))} | {escape(str(d.get('address', '-')))} | "
            f"vendor={escape(str(d.get('vendor', 'Unknown')))} | score={_safe_int(d.get('final_score', 0))} | "
            f"{escape(str(d.get('alert_level', '-')))}</li>"
        )

    tracker_list = []
    for d in top_trackers:
        tracker_list.append(
            f"<li>{escape(str(d.get('name', 'Inconnu')))} | {escape(str(d.get('address', '-')))} | "
            f"follow={_safe_int(d.get('follow_score', 0))} | profile={escape(str(d.get('profile', '-')))}</li>"
        )

    case_list = []
    for case in cases:
        case_list.append(
            f"<li>{escape(str(case.get('title', 'Untitled Case')))} | "
            f"status={escape(str(case.get('status', '-')))} | "
            f"updated={escape(str(case.get('updated_at', '-')))}</li>"
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
        is_tracker = "true" if (d.get("possible_suivi") or d.get("watch_hit") or "tracker" in str(d.get("profile", "")).lower()) else "false"
        is_watch = "true" if d.get("watch_hit") else "false"

        rows.append(
            f"""
        <tr class="{css}" data-alert="{escape(str(d.get('alert_level', 'faible')))}"
            data-vendor="{escape(str(d.get('vendor', 'Unknown')))}"
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
            <td>{escape(explanation)}</td>
            <td>{escape(str(d.get("reason_short", "normal")))}</td>
        </tr>
        """
        )

    try:
        bluehood_summary = render_bluehood_summary(devices)
    except Exception:
        bluehood_summary = ""

    try:
        bluehood_summary = render_bluehood_summary(devices)
    except Exception:
        bluehood_summary = ""

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
  <h1>BLE Radar Omega AI - Dashboard Pro</h1>
  <h2>Résumé global</h2>

  <div class="cards">
    <div class="card"><div>Total</div><div class="big">{len(devices)}</div></div>
    <div class="card"><div>Critiques</div><div class="big">{len(critical)}</div></div>
    <div class="card"><div>Élevés</div><div class="big">{len(high)}</div></div>
    <div class="card"><div>Moyens</div><div class="big">{len(medium)}</div></div>
    <div class="card"><div>Watchlist Hits</div><div class="big">{len(watch_hits)}</div></div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>Résumé comparatif</h2>
      <ul>{''.join(comparison_lines)}</ul>
      <div class="muted">Horodatage : {escape(stamp)}</div>
    </div>
    <div class="panel">
      <h2>Incidents visibles</h2>
      <ul>{''.join(incident_lines)}</ul>
      <div class="muted">Vue rapide des signaux prioritaires du scan courant.</div>
    </div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>Cas d'investigation récents</h2>
      <ul>{''.join(case_list) if case_list else '<li class="muted">Aucun cas récent</li>'}</ul>
    </div>
    <div class="panel">
      <h2>Top appareils chauds</h2>
      <ul>{''.join(hot_list) if hot_list else '<li class="muted">Aucun</li>'}</ul>
    </div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>Top trackers probables</h2>
      <ul>{''.join(tracker_list) if tracker_list else '<li class="muted">Aucun</li>'}</ul>
    </div>
    <div class="panel">
      <h2>Répartition vendors</h2>
      {''.join(vendor_bars) if vendor_bars else '<div class="muted">Aucune donnée</div>'}
    </div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Session diff récent</h2>
    <ul>{''.join(diff_lines)}</ul>
    <div class="muted">Résumé du dernier manifest comparé au précédent.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Artifact index</h2>
    <ul>{''.join(artifact_lines)}</ul>
    <div class="muted">Vue rapide des artefacts locaux générés.</div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>Latest session overview</h2>
      <ul>{''.join(latest_session_lines)}</ul>
    </div>
    <div class="panel">
      <h2>Sessions récentes</h2>
      <ul>{''.join(recent_session_lines) if recent_session_lines else '<li class="muted">Aucune session récente</li>'}</ul>
    </div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Device registry snapshot</h2>
    <ul>{''.join(registry_lines) if registry_lines else '<li class="muted">Aucune donnée registry disponible</li>'}</ul>
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

  <div class="grid2">
    <div class="panel">
      <h2>Filtres rapides</h2>
      <input id="searchBox" placeholder="Recherche nom / adresse / vendor">
      <select id="vendorSelect">
        {''.join(vendor_options)}
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
          {''.join(trend_rows) if trend_rows else '<tr><td colspan="5" class="muted">Aucun historique</td></tr>'}
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
        {''.join(rows)}
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

searchBox.addEventListener('input', applyFilters);
vendorSelect.addEventListener('change', applyFilters);
</script>

<!-- BLUEHOOD SUMMARY -->
{bluehood_summary}

</body>
</html>
"""


def render_bluehood_summary(devices, registry=None, session_id="dashboard-session", seen_at="now"):
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
            correlated_pairs.append(f"<li>{address} ↔ {escape(str(pair))} (score: {item.get("score", 0)})</li>")
        else:
            correlated_pairs.append(f"<li>{name} ({address}) — score: {item.get('score', 0)}</li>")

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

