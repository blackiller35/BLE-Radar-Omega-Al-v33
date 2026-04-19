"""Lightweight operator post-closure monitoring policy / recurrence watch system."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


_ALLOWED_SCOPE_TYPES = {"device", "case", "cluster", "campaign", "evidence_pack", "queue_item"}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _slug(value: Any) -> str:
    return str(value or "unknown").replace(":", "").replace("/", "-").replace(" ", "_").lower()


def _find_scope_records(scope_id: str, rows: List[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
    sid = _norm(scope_id)
    if not sid:
        return []

    found = []
    for row in rows:
        for key in keys:
            if _norm(row.get(key)) == sid:
                found.append(row)
                break
    return found


def _monitoring_mode(
    *,
    final_disposition: str,
    final_risk_level: str,
    followup_mode: str,
    archive_recommendation: str,
) -> str:
    """Determine monitoring mode from closure disposition and risk factors."""
    if archive_recommendation == "archive_now":
        return "archive_only"
    if final_disposition == "false_positive":
        return "archive_only"
    if followup_mode == "none" and final_risk_level == "low":
        return "archive_only"
    if archive_recommendation == "archive_after_brief_hold":
        return "light_monitoring"
    if followup_mode == "monitor" and final_risk_level == "medium":
        return "scheduled_recheck"
    if followup_mode == "monitor" and final_risk_level == "high":
        return "watch_for_recurrence"
    if followup_mode == "specialist_followup" or final_risk_level == "high":
        return "high_attention_post_closure"
    if final_disposition == "resolved_with_followup" and final_risk_level == "medium":
        return "scheduled_recheck"
    return "light_monitoring"


def _monitoring_reason(
    *,
    final_disposition: str,
    escalation_reason: str,
    review_result: str,
    outcome_labels: List[str],
) -> str:
    """Derive monitoring reason from closure context."""
    reasons = []

    if escalation_reason:
        reasons.append(f"escalated_for:{escalation_reason}")
    if review_result == "escalate_further":
        reasons.append("specialist_needs_followup")
    if review_result == "needs_more_data":
        reasons.append("incomplete_data_at_close")
    if "false_positive" in outcome_labels:
        reasons.append("confirmed_false_positive")
    if "repeated_reopen" in outcome_labels:
        reasons.append("history_of_reopens")
    if "weak_confidence" in outcome_labels:
        reasons.append("low_confidence_resolution")
    if final_disposition == "resolved_with_followup":
        reasons.append("requires_followup_checks")

    if not reasons:
        reasons.append("standard_closure_review")

    return "|".join(reasons[:4])


def _watch_signals(
    *,
    pattern_matches: List[Dict[str, Any]],
    outcome_labels: List[str],
    escalation_reason: str,
    scope_id: str,
) -> List[str]:
    """Extract relevant watch signals for post-closure monitoring."""
    signals = []

    for pm in pattern_matches[:3]:
        pattern_name = str(pm.get("pattern_name", "unknown")).strip()
        if pattern_name:
            signals.append(f"pattern:{pattern_name}")

    for label in outcome_labels[:3]:
        if label and label.strip():
            signals.append(f"outcome:{label}")

    if escalation_reason:
        signals.append(f"escalation:{escalation_reason}")

    if len(signals) < 4:
        signals.append(f"scope_recurrence_monitor:{_slug(scope_id)}")

    return signals[:6]


def _reopen_triggers(
    *,
    final_risk_level: str,
    outcome_labels: List[str],
    monitoring_mode: str,
) -> List[str]:
    """Define conditions that should trigger reopening."""
    triggers = []

    if monitoring_mode in {"watch_for_recurrence", "high_attention_post_closure"}:
        triggers.append("signal_pattern_detected")
        triggers.append("new_alert_on_scope")

    if final_risk_level == "high":
        triggers.append("high_risk_indicator")
        triggers.append("pattern_match_recurrence")

    if "repeated_reopen" in outcome_labels:
        triggers.append("recurrence_of_previous_pattern")

    if "weak_confidence" in outcome_labels:
        triggers.append("confidence_threshold_breached")

    if monitoring_mode == "scheduled_recheck":
        triggers.append("scheduled_review_time_reached")

    if not triggers:
        triggers.append("manual_review_requested")

    return triggers[:5]


def _review_window(monitoring_mode: str, final_risk_level: str) -> str:
    """Determine review window/interval based on monitoring mode and risk."""
    if monitoring_mode == "archive_only":
        return "no_review"
    if monitoring_mode == "light_monitoring":
        return "30_days"
    if monitoring_mode == "scheduled_recheck":
        if final_risk_level == "high":
            return "7_days"
        return "14_days"
    if monitoring_mode == "watch_for_recurrence":
        return "immediate"
    if monitoring_mode == "high_attention_post_closure":
        return "immediate"
    return "30_days"


def _priority_after_closure(
    *,
    final_risk_level: str,
    followup_mode: str,
    monitoring_mode: str,
) -> str:
    """Determine post-closure priority for monitoring tasks."""
    if monitoring_mode in {"archive_only"}:
        return "no_priority"
    if monitoring_mode == "high_attention_post_closure":
        return "critical"
    if final_risk_level == "high" and followup_mode == "specialist_followup":
        return "high"
    if final_risk_level == "high":
        return "high"
    if final_risk_level == "medium" and followup_mode == "monitor":
        return "medium"
    if monitoring_mode == "watch_for_recurrence":
        return "high"
    return "low"


def build_operator_post_closure_monitoring_policies(
    monitoring_scopes: Optional[List[Dict[str, Any]]] = None,
    *,
    closure_packages: Optional[List[Dict[str, Any]]] = None,
    escalation_feedback: Optional[List[Dict[str, Any]]] = None,
    outcomes: Optional[List[Dict[str, Any]]] = None,
    recommendation_profiles: Optional[List[Dict[str, Any]]] = None,
    pattern_matches: Optional[List[Dict[str, Any]]] = None,
    campaign_records: Optional[List[Dict[str, Any]]] = None,
    queue_health_snapshot: Optional[Dict[str, Any]] = None,
    alerts_history: Optional[List[Dict[str, Any]]] = None,
    review_readiness: Optional[List[Dict[str, Any]]] = None,
    session_journal: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build compact post-closure monitoring policies from closure packages and signals."""
    scope_rows = list(monitoring_scopes or [])
    closure_rows = list(closure_packages or [])
    feedback_rows = list(escalation_feedback or [])
    outcome_rows = list(outcomes or [])
    rec_rows = list(recommendation_profiles or [])
    match_rows = list(pattern_matches or [])
    campaign_rows = list(campaign_records or [])
    alert_rows = list(alerts_history or [])
    readiness_rows = list(review_readiness or [])
    health = queue_health_snapshot if isinstance(queue_health_snapshot, dict) else {}
    journal = session_journal if isinstance(session_journal, dict) else {}

    stamp = str(generated_at or _now())

    policies: List[Dict[str, Any]] = []
    seen = set()

    for scope in scope_rows:
        scope_type = _norm(scope.get("scope_type") or "device")
        if scope_type not in _ALLOWED_SCOPE_TYPES:
            continue

        scope_id = str(scope.get("scope_id") or "-").strip()
        if not scope_id:
            continue

        key = (scope_type, _norm(scope_id))
        if key in seen:
            continue
        seen.add(key)

        scope_closures = _find_scope_records(scope_id, closure_rows, ["scope_id"])
        scope_feedback = _find_scope_records(scope_id, feedback_rows, ["scope_id"])
        scope_outcomes = _find_scope_records(scope_id, outcome_rows, ["scope_id"])
        scope_recs = _find_scope_records(scope_id, rec_rows, ["scope_id"])
        scope_matches = _find_scope_records(scope_id, match_rows, ["scope_id"])
        scope_campaigns = _find_scope_records(scope_id, campaign_rows, ["campaign_id", "scope_id"])
        scope_alerts = _find_scope_records(scope_id, alert_rows, ["scope_id", "device_id"])
        scope_readiness = _find_scope_records(scope_id, readiness_rows, ["scope_id"])

        if not scope_closures:
            continue

        last_closure = scope_closures[0]
        last_feedback = scope_feedback[0] if scope_feedback else {}
        closure_id = str(last_closure.get("closure_id", f"closure-{_slug(scope_id)}-{_slug(stamp)}"))

        final_disposition = _norm(last_closure.get("final_disposition") or "resolved")
        final_risk_level = _norm(last_closure.get("final_risk_level") or "medium")
        followup_mode = _norm(last_closure.get("followup_mode") or "none")
        archive_recommendation = _norm(last_closure.get("archive_recommendation") or "keep_active")

        review_result = _norm(last_feedback.get("review_result") or "confirmed")
        escalation_reason = _norm(last_closure.get("final_disposition") or "")
        outcome_labels = [_norm(r.get("outcome_label")) for r in scope_outcomes]

        monitoring_mode = _monitoring_mode(
            final_disposition=final_disposition,
            final_risk_level=final_risk_level,
            followup_mode=followup_mode,
            archive_recommendation=archive_recommendation,
        )

        monitoring_reason = _monitoring_reason(
            final_disposition=final_disposition,
            escalation_reason=escalation_reason,
            review_result=review_result,
            outcome_labels=outcome_labels,
        )

        watch_signals_list = _watch_signals(
            pattern_matches=scope_matches,
            outcome_labels=outcome_labels,
            escalation_reason=escalation_reason,
            scope_id=scope_id,
        )

        reopen_triggers_list = _reopen_triggers(
            final_risk_level=final_risk_level,
            outcome_labels=outcome_labels,
            monitoring_mode=monitoring_mode,
        )

        review_window = _review_window(monitoring_mode, final_risk_level)
        priority_after_closure = _priority_after_closure(
            final_risk_level=final_risk_level,
            followup_mode=followup_mode,
            monitoring_mode=monitoring_mode,
        )

        policies.append(
            {
                "policy_id": f"policy-{scope_type}-{_slug(scope_id)}-{_slug(stamp)}",
                "scope_type": scope_type,
                "scope_id": scope_id,
                "closure_id": closure_id,
                "monitoring_mode": monitoring_mode,
                "monitoring_reason": monitoring_reason,
                "watch_signals": watch_signals_list,
                "reopen_triggers": reopen_triggers_list,
                "review_window": review_window,
                "priority_after_closure": priority_after_closure,
                "created_at": stamp,
            }
        )

    policies.sort(
        key=lambda r: (
            {
                "high_attention_post_closure": 5,
                "watch_for_recurrence": 4,
                "scheduled_recheck": 3,
                "light_monitoring": 2,
                "archive_only": 1,
            }.get(_norm(r.get("monitoring_mode")), 0),
            str(r.get("created_at", "")),
        ),
        reverse=True,
    )

    return policies[:48]


def summarize_operator_post_closure_monitoring_policies(
    policies: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build compact dashboard sections for post-closure monitoring policy panel."""
    rows = list(policies or [])

    monitoring_policies = rows[:12]

    watch_for_recurrence = [
        r for r in rows
        if _norm(r.get("monitoring_mode")) == "watch_for_recurrence"
    ][:10]

    scheduled_rechecks = [
        r for r in rows
        if _norm(r.get("monitoring_mode")) == "scheduled_recheck"
    ][:10]

    high_attention = [
        r for r in rows
        if _norm(r.get("monitoring_mode")) == "high_attention_post_closure"
    ][:10]

    recent_reopen = [
        r for r in rows
        if any(trigger in str(r.get("reopen_triggers", [])) for trigger in ["signal_pattern", "new_alert", "recurrence"])
    ][:10]

    return {
        "monitoring_policies": monitoring_policies,
        "watch_for_recurrence": watch_for_recurrence,
        "scheduled_rechecks": scheduled_rechecks,
        "high_attention": high_attention,
        "recent_reopen_triggers": recent_reopen,
    }
