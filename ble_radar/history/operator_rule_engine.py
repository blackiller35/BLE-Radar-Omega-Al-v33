"""Lightweight operator rule engine with safe auto-actions.

This module evaluates simple local rules for one device/case using existing
signals and can persist a lightweight automation event log.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ble_radar.config import HISTORY_DIR
from ble_radar.state import load_json, save_json

AUTOMATION_EVENTS_FILE = HISTORY_DIR / "automation_events.json"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_address(address: Any) -> str:
    return str(address or "").strip().upper()


def _has_incident_pack(
    investigation_profile: Optional[Dict[str, Any]],
    timeline_events: Optional[List[Dict[str, Any]]],
) -> bool:
    refs = (investigation_profile or {}).get("incident_refs", {})
    if refs.get("device_packs") or refs.get("incident_packs"):
        return True

    for ev in timeline_events or []:
        src = str(ev.get("source", "")).strip().lower()
        act = str(ev.get("action", "")).strip().lower()
        if src == "incident_pack" or act in {"generated", "incident_pack_generated"}:
            return True
    return False


def _triage_fields(
    triage_row: Optional[Dict[str, Any]],
    investigation_profile: Optional[Dict[str, Any]],
) -> tuple[int, str]:
    if triage_row:
        score = _safe_int(triage_row.get("triage_score", 0), 0)
        bucket = str(triage_row.get("triage_bucket", "normal")).strip().lower()
        return score, bucket

    triage = (investigation_profile or {}).get("triage", {})
    score = _safe_int(triage.get("triage_score", 0), 0)
    bucket = str(triage.get("triage_bucket", "normal")).strip().lower()
    return score, bucket


def _case_status(
    case_record: Optional[Dict[str, Any]],
    investigation_profile: Optional[Dict[str, Any]],
) -> str:
    if case_record and case_record.get("status"):
        return str(case_record.get("status", "none")).strip().lower()
    return str((investigation_profile or {}).get("case", {}).get("status", "none")).strip().lower()


def _new_result(
    rule_id: str,
    matched: bool,
    recommended_action: str,
    requires_confirmation: bool,
    reason: str,
) -> Dict[str, Any]:
    return {
        "rule_id": rule_id,
        "matched": bool(matched),
        "recommended_action": str(recommended_action),
        "auto_applied": False,
        "requires_confirmation": bool(requires_confirmation),
        "reason": str(reason),
    }


def load_automation_events(address: Optional[Any] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load automation events, optionally filtered by address and limited."""
    rows = load_json(AUTOMATION_EVENTS_FILE, [])
    events = rows if isinstance(rows, list) else []

    if address is not None:
        addr = _normalize_address(address)
        events = [e for e in events if str(e.get("address", "")).upper() == addr]

    if isinstance(limit, int) and limit >= 0:
        events = events[-limit:]

    return events


def log_automation_event(
    address: Any,
    rule_result: Dict[str, Any],
    *,
    source: str = "operator_rule_engine",
) -> Dict[str, Any]:
    """Append one lightweight automation event to local storage."""
    addr = _normalize_address(address)
    if not addr:
        raise ValueError("address must not be empty")

    event = {
        "timestamp": _now(),
        "source": source,
        "address": addr,
        "rule_id": str(rule_result.get("rule_id", "-")),
        "matched": bool(rule_result.get("matched", False)),
        "auto_applied": bool(rule_result.get("auto_applied", False)),
        "requires_confirmation": bool(rule_result.get("requires_confirmation", False)),
        "recommended_action": str(rule_result.get("recommended_action", "-")),
        "reason": str(rule_result.get("reason", "-")),
    }

    events = load_automation_events()
    events.append(event)
    save_json(AUTOMATION_EVENTS_FILE, events)
    return event


def evaluate_operator_rules(
    address: Any,
    *,
    playbook_recommendation: Optional[Dict[str, Any]] = None,
    case_record: Optional[Dict[str, Any]] = None,
    timeline_events: Optional[List[Dict[str, Any]]] = None,
    triage_row: Optional[Dict[str, Any]] = None,
    investigation_profile: Optional[Dict[str, Any]] = None,
    apply_auto: bool = True,
    persist_log: bool = True,
) -> List[Dict[str, Any]]:
    """Evaluate explicit local rules and return rule result rows.

    Each row returns: rule_id, matched, recommended_action, auto_applied,
    requires_confirmation, reason.
    """
    addr = _normalize_address(address)
    if not addr:
        raise ValueError("address must not be empty")

    playbook_id = str((playbook_recommendation or {}).get("playbook_id", ""))
    playbook_action = str((playbook_recommendation or {}).get("recommended_action", ""))
    triage_score, triage_bucket = _triage_fields(triage_row, investigation_profile)
    status = _case_status(case_record, investigation_profile)
    pack_available = _has_incident_pack(investigation_profile, timeline_events)

    results: List[Dict[str, Any]] = []

    # Rule 1: critical requires human confirmation, never auto-applied.
    critical_match = (
        triage_bucket == "critical"
        or triage_score >= 45
        or playbook_id in {"pb-critical-pack", "pb-critical-investigate"}
    )
    results.append(
        _new_result(
            "re-critical-confirm",
            critical_match,
            playbook_action or "Escalate to manual investigation",
            True,
            f"critical triage={triage_score}/{triage_bucket} | pack_available={pack_available}",
        )
    )

    # Rule 2: review triage requires confirmation.
    review_match = (
        triage_bucket == "review"
        or playbook_id == "pb-review-triage"
        or status in {"new", "review"}
    )
    results.append(
        _new_result(
            "re-review-confirm",
            review_match and not critical_match,
            "Run review triage workflow",
            True,
            f"status={status} | triage={triage_score}/{triage_bucket}",
        )
    )

    # Rule 3: safe watch monitor action can auto-apply.
    watch_match = (
        triage_bucket == "watch"
        or playbook_id == "pb-watch-monitor"
        or status in {"watch", "investigating"}
    )
    results.append(
        _new_result(
            "re-watch-auto-monitor",
            watch_match and not critical_match and not review_match,
            "Enable passive watch monitoring",
            False,
            f"watch-level signals | status={status}",
        )
    )

    # Rule 4: resolved/ignored safe close action can auto-apply.
    close_match = status in {"resolved", "ignored"} or playbook_id == "pb-close-monitor"
    results.append(
        _new_result(
            "re-close-auto",
            close_match,
            "Close case and keep recurrence monitor",
            False,
            f"terminal status={status}",
        )
    )

    # Rule 5: baseline observation can auto-apply.
    baseline_match = playbook_id == "pb-observe-baseline" or (triage_bucket == "normal" and status in {"none", ""})
    results.append(
        _new_result(
            "re-baseline-auto",
            baseline_match,
            "Keep baseline passive observation",
            False,
            f"baseline triage={triage_score}/{triage_bucket}",
        )
    )

    # Apply auto-actions only for matched rules that do not require confirmation.
    for row in results:
        if row["matched"] and not row["requires_confirmation"] and apply_auto:
            row["auto_applied"] = True

        if row["matched"] and persist_log:
            try:
                log_automation_event(addr, row)
            except Exception:
                pass

    return results


def summarize_rule_results(rule_results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Build compact dashboard-friendly groups from rule result rows."""
    matched = [r for r in rule_results if r.get("matched")]
    auto_applied = [r for r in matched if r.get("auto_applied")]
    pending = [r for r in matched if r.get("requires_confirmation")]
    recent = matched[-8:]
    return {
        "auto_applied": auto_applied,
        "pending_confirmations": pending,
        "recent_matched": recent,
    }
