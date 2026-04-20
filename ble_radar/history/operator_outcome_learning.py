"""Lightweight operator outcome learning / historical effectiveness feedback system."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple


_ALLOWED_SCOPE_TYPES = {"device", "case", "cluster", "campaign", "evidence_pack", "queue_item"}
_LEARNING_RESULT_TYPES = {
    "high_value_action_pattern",
    "mixed_result_pattern",
    "fragile_followup_pattern",
    "reopen_reduction_pattern",
    "needs_more_history",
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _slug(value: Any) -> str:
    return str(value or "unknown").replace(":", "").replace("/", "-").replace(" ", "_").lower()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _scope_key(scope_type: str, scope_id: str) -> Tuple[str, str]:
    return _norm(scope_type), _norm(scope_id)


def _build_scope_filter(learning_scopes: Optional[List[Dict[str, Any]]]) -> Optional[Set[Tuple[str, str]]]:
    rows = list(learning_scopes or [])
    if not rows:
        return None

    out: Set[Tuple[str, str]] = set()
    for row in rows:
        scope_type = _norm(row.get("scope_type") or "device")
        scope_id = str(row.get("scope_id") or "").strip()
        if scope_type in _ALLOWED_SCOPE_TYPES and scope_id:
            out.add(_scope_key(scope_type, scope_id))
    return out or None


def _find_scope_rows(
    scope_type: str,
    scope_id: str,
    rows: List[Dict[str, Any]],
    keys: List[str],
) -> List[Dict[str, Any]]:
    sid = _norm(scope_id)
    stype = _norm(scope_type)
    if not sid or not stype:
        return []

    out: List[Dict[str, Any]] = []
    for row in rows:
        row_scope_type = _norm(row.get("scope_type") or row.get("pattern_type") or row.get("type") or "")
        if row_scope_type and row_scope_type != stype:
            continue
        for key in keys:
            if _norm(row.get(key)) == sid:
                out.append(row)
                break
    return out


def _top_action_pattern(plan_rows: List[Dict[str, Any]], outcome_rows: List[Dict[str, Any]]) -> str:
    if plan_rows:
        actions = list(plan_rows[0].get("recommended_actions") or [])
        if actions:
            return str(actions[0])
        goal = str(plan_rows[0].get("improvement_goal") or "")
        if goal:
            return goal

    if outcome_rows:
        action = str(outcome_rows[0].get("source_action") or "")
        if action:
            return action
        playbook = str(outcome_rows[0].get("source_playbook") or "")
        if playbook:
            return playbook

    return "baseline_operator_review"


def _compute_observed_outcome(outcome_rows: List[Dict[str, Any]], quality_level: str) -> str:
    if not outcome_rows:
        return "insufficient_history"

    labels = {_norm(r.get("outcome_label")) for r in outcome_rows}
    reopened = any(bool(r.get("reopened")) for r in outcome_rows)
    if reopened or "resolved_but_returned" in labels:
        if "resolved_cleanly" in labels or "stabilized" in labels:
            return "mixed_with_reopen"
        return "reopened_after_action"
    if "resolved_cleanly" in labels or "stabilized" in labels:
        return "stabilized_after_action"
    if quality_level in {"fragile", "likely_to_reopen"}:
        return "fragile_followup_only"
    return "mixed_signals"


def _compute_learning_type(
    *,
    observed_outcome: str,
    avg_effectiveness: int,
    quality_level: str,
    baseline_reopens: int,
    recent_reopens: int,
    confidence_level: str,
) -> str:
    if observed_outcome == "insufficient_history" or confidence_level == "low":
        return "needs_more_history"
    if recent_reopens == 0 and baseline_reopens > 0 and avg_effectiveness >= 60:
        return "reopen_reduction_pattern"
    if observed_outcome == "stabilized_after_action" and avg_effectiveness >= 75 and quality_level in {"durable", "mostly_stable"}:
        return "high_value_action_pattern"
    if observed_outcome in {"reopened_after_action", "fragile_followup_only"} or quality_level in {"fragile", "likely_to_reopen"}:
        return "fragile_followup_pattern"
    return "mixed_result_pattern"


def build_operator_outcome_learning_records(
    learning_scopes: Optional[List[Dict[str, Any]]] = None,
    *,
    resolution_quality_records: Optional[List[Dict[str, Any]]] = None,
    improvement_plans: Optional[List[Dict[str, Any]]] = None,
    lifecycle_lineage: Optional[List[Dict[str, Any]]] = None,
    operator_outcomes: Optional[List[Dict[str, Any]]] = None,
    closure_packages: Optional[List[Dict[str, Any]]] = None,
    reopen_policy_records: Optional[List[Dict[str, Any]]] = None,
    post_closure_monitoring_policies: Optional[List[Dict[str, Any]]] = None,
    escalation_feedback: Optional[List[Dict[str, Any]]] = None,
    recommendation_tuning: Optional[List[Dict[str, Any]]] = None,
    pattern_library: Optional[List[Dict[str, Any]]] = None,
    generated_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build compact outcome learning records from existing project signals."""
    scope_filter = _build_scope_filter(learning_scopes)
    quality_rows = list(resolution_quality_records or [])
    plan_rows = list(improvement_plans or [])
    lineage_rows = list(lifecycle_lineage or [])
    outcome_rows = list(operator_outcomes or [])
    closure_rows = list(closure_packages or [])
    reopen_rows = list(reopen_policy_records or [])
    monitoring_rows = list(post_closure_monitoring_policies or [])
    feedback_rows = list(escalation_feedback or [])
    tuning_rows = list(recommendation_tuning or [])
    pattern_rows = list(pattern_library or [])
    stamp = str(generated_at or _now())

    learning_rows: List[Dict[str, Any]] = []

    for q in quality_rows:
        scope_type = str(q.get("scope_type") or "device").strip().lower()
        scope_id = str(q.get("scope_id") or "-").strip()
        if scope_type not in _ALLOWED_SCOPE_TYPES or not scope_id or scope_id == "-":
            continue
        if scope_filter is not None and _scope_key(scope_type, scope_id) not in scope_filter:
            continue

        scoped_plans = _find_scope_rows(scope_type, scope_id, plan_rows, ["scope_id"])
        scoped_lineage = _find_scope_rows(scope_type, scope_id, lineage_rows, ["scope_id"])
        scoped_outcomes = _find_scope_rows(scope_type, scope_id, outcome_rows, ["scope_id"])
        scoped_closures = _find_scope_rows(scope_type, scope_id, closure_rows, ["scope_id"])
        scoped_reopens = _find_scope_rows(scope_type, scope_id, reopen_rows, ["scope_id"])
        scoped_monitoring = _find_scope_rows(scope_type, scope_id, monitoring_rows, ["scope_id"])
        scoped_feedback = _find_scope_rows(scope_type, scope_id, feedback_rows, ["scope_id"])
        scoped_tuning = _find_scope_rows(scope_type, scope_id, tuning_rows, ["scope_id", "sample_scope_id"])
        scoped_patterns = _find_scope_rows(scope_type, scope_id, pattern_rows, ["scope_id", "item_id", "campaign_id", "pack_id"])

        quality_id = str(q.get("quality_id") or f"quality-{scope_type}-{_slug(scope_id)}")
        lineage_id = str((scoped_lineage[0] if scoped_lineage else {}).get("lineage_id") or q.get("lineage_id") or "unknown")
        action_pattern = _top_action_pattern(scoped_plans, scoped_outcomes)

        observed_outcome = _compute_observed_outcome(scoped_outcomes, str(q.get("resolution_quality") or "unknown"))

        current_stability = _safe_int(q.get("stability_score"), 50)
        expected_gain = _safe_int((scoped_plans[0] if scoped_plans else {}).get("expected_stability_gain"), 0)
        stability_delta = max(-25, min(40, expected_gain))

        baseline_reopens = max(
            _safe_int((scoped_lineage[0] if scoped_lineage else {}).get("reopened_count"), 0),
            len(scoped_reopens),
        )
        recent_reopens = len(
            [
                r for r in scoped_outcomes
                if bool(r.get("reopened")) or _norm(r.get("outcome_label")) in {"resolved_but_returned", "reopened", "reopen"}
            ]
        )
        if recent_reopens == 0 and baseline_reopens > 0 and current_stability >= 55:
            reopen_delta = -min(2, baseline_reopens)
        elif recent_reopens > 0:
            reopen_delta = min(3, recent_reopens)
        else:
            reopen_delta = 0

        effectiveness_values = [_safe_int(r.get("effectiveness"), 0) for r in scoped_outcomes if r.get("effectiveness") is not None]
        avg_effectiveness = int(sum(effectiveness_values) / len(effectiveness_values)) if effectiveness_values else 0

        signal_count = sum(
            [
                1 if scoped_plans else 0,
                1 if scoped_lineage else 0,
                1 if scoped_outcomes else 0,
                1 if scoped_closures else 0,
                1 if scoped_reopens else 0,
                1 if scoped_monitoring else 0,
                1 if scoped_feedback else 0,
                1 if scoped_tuning else 0,
                1 if scoped_patterns else 0,
            ]
        )

        if scoped_tuning and any(_norm(t.get("confidence_level")) == "high" for t in scoped_tuning) and signal_count >= 4:
            confidence_level = "high"
        elif signal_count >= 4 and avg_effectiveness >= 55:
            confidence_level = "medium"
        else:
            confidence_level = "low"

        learning_type = _compute_learning_type(
            observed_outcome=observed_outcome,
            avg_effectiveness=avg_effectiveness,
            quality_level=str(q.get("resolution_quality") or "unknown"),
            baseline_reopens=baseline_reopens,
            recent_reopens=recent_reopens,
            confidence_level=confidence_level,
        )
        if learning_type not in _LEARNING_RESULT_TYPES:
            learning_type = "needs_more_history"

        caution_flags: List[str] = []
        if str(q.get("resolution_quality") or "") in {"fragile", "likely_to_reopen", "insufficient_resolution"}:
            caution_flags.append("fragile_resolution_quality")
        if reopen_delta > 0:
            caution_flags.append("reopen_pressure_increasing")
        if confidence_level == "low":
            caution_flags.append("low_learning_confidence")
        if not scoped_outcomes:
            caution_flags.append("missing_outcome_history")

        if learning_type in {"high_value_action_pattern", "reopen_reduction_pattern"} and confidence_level in {"high", "medium"}:
            recommended_reuse = "reuse_with_similar_scope"
        elif learning_type == "mixed_result_pattern":
            recommended_reuse = "reuse_with_operator_review"
        else:
            recommended_reuse = "do_not_reuse_without_more_history"

        learning_summary = (
            f"pattern={action_pattern} | outcome={observed_outcome} | "
            f"stability_delta={stability_delta} | reopen_delta={reopen_delta} | confidence={confidence_level}"
        )

        learning_rows.append(
            {
                "learning_id": f"learning-{scope_type}-{_slug(scope_id)}",
                "scope_type": scope_type,
                "scope_id": scope_id,
                "quality_id": quality_id,
                "lineage_id": lineage_id,
                "action_pattern": action_pattern,
                "observed_outcome": observed_outcome,
                "stability_delta": stability_delta,
                "reopen_delta": reopen_delta,
                "confidence_level": confidence_level,
                "learning_summary": learning_summary,
                "recommended_reuse": recommended_reuse,
                "caution_flags": caution_flags[:5],
                "learning_type": learning_type,
                "updated_at": stamp,
            }
        )

    learning_rows.sort(
        key=lambda r: (
            {
                "high_value_action_pattern": 0,
                "reopen_reduction_pattern": 1,
                "mixed_result_pattern": 2,
                "fragile_followup_pattern": 3,
                "needs_more_history": 4,
            }.get(str(r.get("learning_type")), 5),
            -_safe_int(r.get("stability_delta"), 0),
            _safe_int(r.get("reopen_delta"), 0),
        ),
    )

    return learning_rows[:64]


def summarize_operator_outcome_learning(
    learning_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build compact dashboard sections for outcome learning panel."""
    rows = list(learning_rows or [])

    high_value = [
        r for r in rows
        if str(r.get("learning_type")) == "high_value_action_pattern"
    ][:10]

    reopen_reduction = [
        r for r in rows
        if str(r.get("learning_type")) == "reopen_reduction_pattern" or _safe_int(r.get("reopen_delta"), 0) < 0
    ][:10]

    mixed_results = [
        r for r in rows
        if str(r.get("learning_type")) in {"mixed_result_pattern", "fragile_followup_pattern"}
    ][:10]

    recommended_reuse = [
        {
            "scope_type": str(r.get("scope_type", "-")),
            "scope_id": str(r.get("scope_id", "-")),
            "action_pattern": str(r.get("action_pattern", "-")),
            "recommended_reuse": str(r.get("recommended_reuse", "do_not_reuse_without_more_history")),
        }
        for r in rows
        if str(r.get("recommended_reuse", "")).startswith("reuse_")
    ][:10]

    return {
        "outcome_learning": rows[:12],
        "high_value_action_patterns": high_value,
        "reopen_reduction_signals": reopen_reduction,
        "mixed_result_patterns": mixed_results,
        "recommended_reuse": recommended_reuse,
    }
