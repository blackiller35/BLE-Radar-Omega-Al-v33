"""Lightweight operator alerting and escalation system.

Generates compact alerts from existing operator signals and supports a local
alert log for recent escalation visibility.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ble_radar.config import HISTORY_DIR
from ble_radar.state import load_json, save_json

ALERT_LOG_FILE = HISTORY_DIR / "operator_alerts.json"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_address(address: Any) -> str:
    return str(address or "").strip().upper()


def _slug(address: str) -> str:
    return address.replace(":", "")


def _timeline_actions(timeline_events: Optional[List[Dict[str, Any]]]) -> set[str]:
    out: set[str] = set()
    for ev in timeline_events or []:
        out.add(str(ev.get("action", "")).strip().lower())
    return out


def _new_alert(
    *,
    alert_id: str,
    severity: str,
    title: str,
    reason: str,
    device_address: str,
    recommended_followup: str,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "alert_id": alert_id,
        "severity": severity,
        "title": title,
        "reason": reason,
        "device_address": device_address,
        "recommended_followup": recommended_followup,
        "created_at": created_at or _now(),
    }


def load_alert_log(limit: Optional[int] = None, address: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Load alert log rows, optionally filtered by address and limited."""
    rows = load_json(ALERT_LOG_FILE, [])
    events = rows if isinstance(rows, list) else []

    if address is not None:
        addr = _normalize_address(address)
        events = [e for e in events if str(e.get("device_address", "")).upper() == addr]

    if isinstance(limit, int) and limit >= 0:
        events = events[-limit:]

    return events


def log_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Append one alert row to local alert log."""
    events = load_alert_log()
    events.append(alert)
    save_json(ALERT_LOG_FILE, events)
    return alert


def log_alerts(alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Append many alerts to local alert log."""
    if not alerts:
        return []
    events = load_alert_log()
    events.extend(alerts)
    save_json(ALERT_LOG_FILE, events)
    return alerts


def build_operator_alerts(
    address: Any,
    *,
    triage_row: Optional[Dict[str, Any]] = None,
    investigation_profile: Optional[Dict[str, Any]] = None,
    case_record: Optional[Dict[str, Any]] = None,
    timeline_events: Optional[List[Dict[str, Any]]] = None,
    playbook_recommendation: Optional[Dict[str, Any]] = None,
    rule_results: Optional[List[Dict[str, Any]]] = None,
    pending_confirmations_count: int = 0,
    persist_log: bool = False,
) -> List[Dict[str, Any]]:
    """Generate compact alerts for one device/case address."""
    addr = _normalize_address(address)
    if not addr:
        raise ValueError("address must not be empty")

    triage_score = _safe_int((triage_row or {}).get("triage_score", 0), 0)
    triage_bucket = str((triage_row or {}).get("triage_bucket", "normal")).strip().lower()
    triage_reason = str((triage_row or {}).get("short_reason", "no signals"))

    if not triage_row and investigation_profile:
        triage = (investigation_profile or {}).get("triage", {})
        triage_score = _safe_int(triage.get("triage_score", 0), 0)
        triage_bucket = str(triage.get("triage_bucket", "normal")).strip().lower()
        triage_reason = str(triage.get("short_reason", "no signals"))

    status = str((case_record or {}).get("status", "none")).strip().lower()
    if status == "none" and investigation_profile:
        status = str((investigation_profile or {}).get("case", {}).get("status", "none")).strip().lower()

    playbook_id = str((playbook_recommendation or {}).get("playbook_id", ""))
    playbook_action = str((playbook_recommendation or {}).get("recommended_action", ""))

    actions = _timeline_actions(timeline_events)
    has_timeline_change = bool(actions.intersection({"score_change", "change_hint", "new"}))

    has_auto_action = any(bool(r.get("auto_applied")) for r in (rule_results or []))

    alerts: List[Dict[str, Any]] = []

    if triage_bucket == "critical" or triage_score >= 45:
        alerts.append(
            _new_alert(
                alert_id=f"alt-critical-{_slug(addr)}",
                severity="critical",
                title="Critical triage escalation",
                reason=f"triage={triage_score}/{triage_bucket} | {triage_reason}",
                device_address=addr,
                recommended_followup=playbook_action or "Escalate to incident response",
            )
        )

    if pending_confirmations_count > 0:
        alerts.append(
            _new_alert(
                alert_id=f"alt-confirm-{_slug(addr)}",
                severity="high",
                title="Pending confirmation required",
                reason=f"{pending_confirmations_count} operator confirmations pending",
                device_address=addr,
                recommended_followup="Review and approve/deny pending rule actions",
            )
        )

    if playbook_id in {"pb-critical-pack", "pb-critical-investigate"}:
        alerts.append(
            _new_alert(
                alert_id=f"alt-playbook-{_slug(addr)}",
                severity="high",
                title="Playbook escalation recommended",
                reason=f"playbook={playbook_id}",
                device_address=addr,
                recommended_followup=playbook_action or "Execute escalation playbook",
            )
        )

    if status in {"investigating", "review"} and has_timeline_change:
        alerts.append(
            _new_alert(
                alert_id=f"alt-investigation-{_slug(addr)}",
                severity="medium",
                title="Investigation context changed",
                reason=f"status={status} with timeline changes",
                device_address=addr,
                recommended_followup="Refresh investigation notes and re-evaluate priority",
            )
        )

    if has_auto_action:
        alerts.append(
            _new_alert(
                alert_id=f"alt-auto-{_slug(addr)}",
                severity="low",
                title="Safe auto-action executed",
                reason="At least one safe rule action auto-applied",
                device_address=addr,
                recommended_followup="Verify auto-action outcome and keep monitoring",
            )
        )

    # De-duplicate by alert_id.
    unique = {}
    for a in alerts:
        unique[a["alert_id"]] = a
    out = list(unique.values())

    if persist_log and out:
        try:
            log_alerts(out)
        except Exception:
            pass

    return out


def summarize_alerts(
    alerts: Optional[List[Dict[str, Any]]] = None,
    recent_log_events: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Build compact dashboard groups for alert panel."""
    current = list(alerts or [])

    active_alerts = [a for a in current if str(a.get("severity", "")).lower() in {"critical", "high", "medium"}]

    immediate = [
        a for a in current
        if str(a.get("severity", "")).lower() == "critical"
        or "pending confirmation" in str(a.get("title", "")).lower()
    ]

    escalations = [
        a for a in current
        if str(a.get("severity", "")).lower() in {"critical", "high"}
    ]

    # If no current escalations, fallback to recent log history
    if not escalations:
        for e in (recent_log_events or [])[::-1]:
            sev = str(e.get("severity", "")).lower()
            if sev in {"critical", "high"}:
                escalations.append(e)
            if len(escalations) >= 8:
                break

    return {
        "active_alerts": active_alerts,
        "recent_escalations": escalations[:8],
        "needs_immediate_review": immediate[:8],
    }
