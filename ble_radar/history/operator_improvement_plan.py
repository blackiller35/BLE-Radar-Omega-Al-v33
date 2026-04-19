"""Lightweight operator resolution improvement plan / corrective guidance system."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple


_ALLOWED_SCOPE_TYPES = {"device", "case", "cluster", "campaign", "evidence_pack", "queue_item"}
_IMPROVEMENT_PLAN_TYPES = {
    "collect_more_evidence",
    "increase_monitoring",
    "tighten_closure",
    "request_specialist_review",
    "improve_followup",
    "reclassify_scope",
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _slug(value: Any) -> str:
    return str(value or "unknown").replace(":", "").replace("/", "-").replace(" ", "_").lower()


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


def _scope_key(scope_type: str, scope_id: str) -> Tuple[str, str]:
    return _norm(scope_type), _norm(scope_id)


def _build_scope_filter(plan_scopes: Optional[List[Dict[str, Any]]]) -> Optional[Set[Tuple[str, str]]]:
    rows = list(plan_scopes or [])
    if not rows:
        return None

    out: Set[Tuple[str, str]] = set()
    for row in rows:
        scope_type = _norm(row.get("scope_type") or "device")
        scope_id = str(row.get("scope_id") or "").strip()
        if scope_type in _ALLOWED_SCOPE_TYPES and scope_id:
            out.add(_scope_key(scope_type, scope_id))
    return out or None


def _compute_priority_level(
    *,
    resolution_quality: str,
    reopen_risk: int,
    weak_factors_count: int,
    stability_score: int,
) -> str:
    """Determine priority level for improvement plan."""
    if resolution_quality == "insufficient_resolution":
        return "critical"
    if resolution_quality == "likely_to_reopen" or reopen_risk >= 80:
        return "high"
    if resolution_quality == "fragile" or reopen_risk >= 60 or stability_score < 40:
        return "medium"
    if resolution_quality == "mostly_stable" or weak_factors_count > 0:
        return "low"
    return "maintenance"


def _compute_improvement_goal(
    *,
    scope_type: str,
    resolution_quality: str,
    weak_factors: List[str],
    stability_score: int,
    reopen_risk: int,
    escalation_count: int,
    monitoring_active: bool,
    has_pattern_pressure: bool,
    low_tuning_confidence: bool,
    mentioned_in_handoff: bool,
) -> str:
    """Select one compact improvement plan type."""
    if "insufficient_evidence" in weak_factors or "weak_closure_confidence" in weak_factors:
        return "collect_more_evidence"
    if "requires_escalation" in weak_factors or escalation_count > 0:
        return "request_specialist_review"
    if resolution_quality in {"likely_to_reopen", "insufficient_resolution"} or "multiple_reopens" in weak_factors:
        return "tighten_closure"
    if monitoring_active and (reopen_risk >= 55 or "high_attention_monitoring_required" in weak_factors):
        return "increase_monitoring"
    if "resolution_not_durable" in weak_factors or mentioned_in_handoff:
        return "improve_followup"
    if scope_type in {"cluster", "campaign", "queue_item"} and (has_pattern_pressure or low_tuning_confidence):
        return "reclassify_scope"
    if stability_score < 60:
        return "tighten_closure"
    return "improve_followup"


def _compute_recommended_actions(
    *,
    improvement_goal: str,
    scope_type: str,
    weak_factors: List[str],
    weak_factors_count: int,
    reopened_count: int,
    escalation_count: int,
    closure_confidence: float,
) -> List[str]:
    """Generate list of recommended corrective actions."""
    actions: List[str] = []

    if improvement_goal == "collect_more_evidence":
        actions.append("collect_additional_supporting_evidence")
        actions.append("attach_evidence_pack_summary")
        if weak_factors_count > 2:
            actions.append("request_peer_review")
    elif improvement_goal == "increase_monitoring":
        actions.append("increase_monitoring_frequency")
        actions.append("add_recurrence_detection_rules")
        if reopened_count > 0:
            actions.append("set_early_reopen_threshold")
    elif improvement_goal == "tighten_closure":
        actions.append("review_closure_decision_logic")
        actions.append("require_closure_checklist")
        if closure_confidence < 0.7:
            actions.append("raise_closure_confidence_threshold")
    elif improvement_goal == "request_specialist_review":
        actions.append("route_to_specialist")
        actions.append("provide_detailed_briefing")
    elif improvement_goal == "reclassify_scope":
        actions.append("revalidate_scope_classification")
        actions.append(f"cross_check_{scope_type}_patterns")
    else:  # improve_followup
        actions.append("schedule_structured_followup")
        actions.append("add_handoff_note_for_next_shift")

    if escalation_count > 0 and "route_to_specialist" not in actions:
        actions.append("confirm_escalation_resolution")
    if "insufficient_evidence" in weak_factors and "collect_additional_supporting_evidence" not in actions:
        actions.append("collect_additional_supporting_evidence")
    if len(actions) < 3:
        actions.append("document_improvement_actions")

    return actions[:6]


def _compute_supporting_rationale(
    *,
    improvement_goal: str,
    resolution_quality: str,
    stability_score: int,
    reopen_risk: int,
    weak_factors: List[str],
) -> str:
    """Generate explanation for improvement plan."""
    goal_desc = {
        "collect_more_evidence": f"Resolution quality={resolution_quality} with low confidence signals; evidence reinforcement needed (stability={stability_score}).",
        "increase_monitoring": f"Risk profile remains elevated (reopen_risk={reopen_risk}%); stronger monitoring is required.",
        "tighten_closure": f"Closure appears fragile for this scope; stricter closure controls can reduce reopen risk.",
        "request_specialist_review": "Escalation-related factors detected; specialist review should validate the final posture.",
        "improve_followup": "Follow-up and handoff continuity need strengthening to avoid post-closure drift.",
        "reclassify_scope": "Signal mix suggests current scope classification may hide root-cause patterns.",
    }
    return goal_desc.get(improvement_goal, "Improvement plan to enhance resolution quality.")


def _compute_blocking_gaps(
    *,
    weak_factors: List[str],
    escalation_count: int,
    closure_confidence: float,
    monitoring_active: bool,
) -> List[str]:
    """Identify obstacles preventing resolution quality improvement."""
    gaps: List[str] = []

    if "insufficient_evidence" in weak_factors:
        gaps.append("missing_evidence_data")
    if closure_confidence < 0.5:
        gaps.append("low_closure_confidence")
    if "weak_closure_confidence" in weak_factors:
        gaps.append("confidence_validation_needed")
    if escalation_count > 0 and not monitoring_active:
        gaps.append("escalation_without_monitoring")
    if "requires_escalation" in weak_factors:
        gaps.append("specialist_expertise_unavailable")
    if "multiple_reopens" in weak_factors:
        gaps.append("pattern_recurrence_unresolved")

    return gaps[:4]


def _compute_expected_stability_gain(
    *,
    improvement_goal: str,
    current_stability_score: int,
) -> int:
    """Estimate stability gain points after implementing plan."""
    gains = {
        "collect_more_evidence": 18,
        "increase_monitoring": 14,
        "tighten_closure": 22,
        "request_specialist_review": 20,
        "improve_followup": 12,
        "reclassify_scope": 10,
    }
    gain = gains.get(improvement_goal, 10)
    if current_stability_score >= 85:
        return min(gain, 8)
    return max(0, min(40, gain))


def _compute_followup_mode(
    *,
    improvement_goal: str,
    priority_level: str,
) -> str:
    """Determine follow-up strategy."""
    if priority_level == "critical":
        return "immediate_specialist_handoff"
    if priority_level == "high":
        if improvement_goal in {"tighten_closure", "request_specialist_review"}:
            return "specialist_followup"
        return "enhanced_monitoring"
    if priority_level == "medium":
        return "scheduled_review"
    if priority_level == "low":
        return "routine_monitoring"
    return "periodic_check"


def build_operator_improvement_plan_records(
    plan_scopes: Optional[List[Dict[str, Any]]] = None,
    *,
    quality_records: Optional[List[Dict[str, Any]]] = None,
    lineage_records: Optional[List[Dict[str, Any]]] = None,
    closure_packages: Optional[List[Dict[str, Any]]] = None,
    reopen_policy_records: Optional[List[Dict[str, Any]]] = None,
    post_closure_monitoring_policies: Optional[List[Dict[str, Any]]] = None,
    escalation_feedback: Optional[List[Dict[str, Any]]] = None,
    operator_outcomes: Optional[List[Dict[str, Any]]] = None,
    recommendation_tuning: Optional[List[Dict[str, Any]]] = None,
    pattern_library: Optional[List[Dict[str, Any]]] = None,
    session_journal: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build compact improvement plan records from quality and closure signals."""
    scope_filter = _build_scope_filter(plan_scopes)
    quality_rows = list(quality_records or [])
    lineage_rows = list(lineage_records or [])
    closure_rows = list(closure_packages or [])
    reopen_rows = list(reopen_policy_records or [])
    monitoring_rows = list(post_closure_monitoring_policies or [])
    feedback_rows = list(escalation_feedback or [])
    outcome_rows = list(operator_outcomes or [])
    tuning_rows = list(recommendation_tuning or [])
    pattern_rows = list(pattern_library or [])
    journal = session_journal if isinstance(session_journal, dict) else {}

    stamp = str(generated_at or _now())
    plan_rows: List[Dict[str, Any]] = []

    # Build plans for each quality record that needs improvement
    for quality_record in quality_rows:
        quality_id = str(quality_record.get("quality_id", "unknown"))
        scope_type = str(quality_record.get("scope_type", "device")).strip().lower()
        scope_id = str(quality_record.get("scope_id", "-")).strip()
        resolution_quality = str(quality_record.get("resolution_quality", "unknown"))

        if scope_type not in _ALLOWED_SCOPE_TYPES or not scope_id or scope_id == "-":
            continue
        if scope_filter is not None and _scope_key(scope_type, scope_id) not in scope_filter:
            continue

        # Skip if already at durable state (no improvement needed)
        if resolution_quality == "durable":
            continue

        # Extract metrics from quality record
        stability_score = _safe_int(quality_record.get("stability_score"), 50)
        reopen_risk = _safe_int(quality_record.get("reopen_risk"), 0)
        weak_factors = list(quality_record.get("weak_factors") or [])
        weak_factors_count = len(weak_factors)

        # Find related lineage and operational signals for same scope.
        scoped_lineage = _find_scope_rows(scope_type, scope_id, lineage_rows, ["scope_id"])

        # Find related closure data
        scoped_closures = _find_scope_rows(scope_type, scope_id, closure_rows, ["scope_id"])
        scoped_reopens = _find_scope_rows(scope_type, scope_id, reopen_rows, ["scope_id"])
        scoped_monitoring = _find_scope_rows(scope_type, scope_id, monitoring_rows, ["scope_id"])
        scoped_feedback = _find_scope_rows(scope_type, scope_id, feedback_rows, ["scope_id"])
        scoped_outcomes = _find_scope_rows(scope_type, scope_id, outcome_rows, ["scope_id"])
        scoped_tuning = _find_scope_rows(scope_type, scope_id, tuning_rows, ["scope_id", "sample_scope_id"])
        scoped_patterns = _find_scope_rows(scope_type, scope_id, pattern_rows, ["scope_id", "item_id", "campaign_id", "pack_id"])

        # Extract metrics
        closure_confidence = _safe_float((scoped_closures[0] if scoped_closures else {}).get("closure_confidence"), 0.5)
        lineage_reopened_count = _safe_int((scoped_lineage[0] if scoped_lineage else {}).get("reopened_count"), 0)
        lineage_escalation_count = _safe_int((scoped_lineage[0] if scoped_lineage else {}).get("escalation_count"), 0)
        reopened_count = max(len(scoped_reopens), lineage_reopened_count)
        escalation_count = max(len(scoped_feedback), lineage_escalation_count)
        monitoring_active = len(scoped_monitoring) > 0
        low_tuning_confidence = any(
            _norm(row.get("confidence_level")) in {"low", "uncertain"}
            or _safe_int(row.get("effectiveness_score"), 100) < 50
            for row in scoped_tuning
        )
        has_pattern_pressure = len(scoped_patterns) > 0
        handoff_text = " ".join(
            [str(journal.get("handoff_summary", ""))]
            + [str(x) for x in list(journal.get("next_shift_priorities", []) or [])]
        ).lower()
        mentioned_in_handoff = _norm(scope_id) in handoff_text

        # Compute improvement plan elements
        priority_level = _compute_priority_level(
            resolution_quality=resolution_quality,
            reopen_risk=reopen_risk,
            weak_factors_count=weak_factors_count,
            stability_score=stability_score,
        )

        improvement_goal = _compute_improvement_goal(
            scope_type=scope_type,
            resolution_quality=resolution_quality,
            weak_factors=weak_factors,
            stability_score=stability_score,
            reopen_risk=reopen_risk,
            escalation_count=escalation_count,
            monitoring_active=monitoring_active,
            has_pattern_pressure=has_pattern_pressure,
            low_tuning_confidence=low_tuning_confidence,
            mentioned_in_handoff=mentioned_in_handoff,
        )
        if improvement_goal not in _IMPROVEMENT_PLAN_TYPES:
            improvement_goal = "improve_followup"

        recommended_actions = _compute_recommended_actions(
            improvement_goal=improvement_goal,
            scope_type=scope_type,
            weak_factors=weak_factors,
            weak_factors_count=weak_factors_count,
            reopened_count=reopened_count,
            escalation_count=escalation_count,
            closure_confidence=closure_confidence,
        )

        supporting_rationale = _compute_supporting_rationale(
            improvement_goal=improvement_goal,
            resolution_quality=resolution_quality,
            stability_score=stability_score,
            reopen_risk=reopen_risk,
            weak_factors=weak_factors,
        )

        blocking_gaps = _compute_blocking_gaps(
            weak_factors=weak_factors,
            escalation_count=escalation_count,
            closure_confidence=closure_confidence,
            monitoring_active=monitoring_active,
        )

        expected_stability_gain = _compute_expected_stability_gain(
            improvement_goal=improvement_goal,
            current_stability_score=stability_score,
        )

        followup_mode = _compute_followup_mode(
            improvement_goal=improvement_goal,
            priority_level=priority_level,
        )

        plan_rows.append(
            {
                "plan_id": f"plan-{scope_type}-{_slug(scope_id)}",
                "scope_type": scope_type,
                "scope_id": scope_id,
                "quality_id": quality_id,
                "resolution_quality": resolution_quality,
                "priority_level": priority_level,
                "improvement_goal": improvement_goal,
                "recommended_actions": recommended_actions,
                "supporting_rationale": supporting_rationale,
                "blocking_gaps": blocking_gaps,
                "expected_stability_gain": expected_stability_gain,
                "current_stability_score": stability_score,
                "followup_mode": followup_mode,
                "created_at": stamp,
            }
        )

    # Sort by priority (critical > high > medium > low > maintenance), then by expected gain.
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "maintenance": 4}
    plan_rows.sort(
        key=lambda r: (
            priority_order.get(str(r.get("priority_level")), 5),
            -_safe_int(r.get("expected_stability_gain"), 0),
            str(r.get("scope_type", "")),
            str(r.get("scope_id", "")),
        ),
    )

    return plan_rows[:64]


def summarize_operator_improvement_plans(
    plan_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build compact dashboard sections for improvement plan panel."""
    rows = list(plan_rows or [])

    # Count by priority
    priority_counts = {
        "critical": len([r for r in rows if str(r.get("priority_level")) == "critical"]),
        "high": len([r for r in rows if str(r.get("priority_level")) == "high"]),
        "medium": len([r for r in rows if str(r.get("priority_level")) == "medium"]),
        "low": len([r for r in rows if str(r.get("priority_level")) == "low"]),
        "maintenance": len([r for r in rows if str(r.get("priority_level")) == "maintenance"]),
    }

    # Top plans by priority
    improvement_plans = [
        r for r in rows
        if str(r.get("priority_level")) in {"critical", "high"}
    ][:10]

    # Fragile closures needing action (fragile or likely_to_reopen quality)
    fragile_needing_action = [
        r for r in rows
        if str(r.get("resolution_quality")) in {"fragile", "likely_to_reopen"}
    ][:8]

    # Top blocking gaps (most common)
    gap_counter: Dict[str, int] = {}
    for r in rows:
        for gap in r.get("blocking_gaps", []):
            gap_counter[gap] = gap_counter.get(gap, 0) + 1

    top_blocking_gaps = sorted(
        gap_counter.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:5]

    # Expected stability gains (sorted by gain)
    stability_gains = sorted(
        [
            {
                "scope_type": str(r.get("scope_type")),
                "scope_id": str(r.get("scope_id")),
                "current_stability": _safe_int(r.get("current_stability_score"), 50),
                "projected_stability": min(
                    100,
                    _safe_int(r.get("current_stability_score"), 50) + _safe_int(r.get("expected_stability_gain"), 0),
                ),
                "improvement_goal": str(r.get("improvement_goal", "none")),
            }
            for r in rows
        ],
        key=lambda x: (x["projected_stability"] - x["current_stability"]),
        reverse=True,
    )[:8]

    # Follow-up modes
    followup_modes = [
        {
            "scope_type": str(r.get("scope_type")),
            "scope_id": str(r.get("scope_id")),
            "followup_mode": str(r.get("followup_mode", "periodic_check")),
            "priority": str(r.get("priority_level", "low")),
        }
        for r in rows[:10]
    ]

    return {
        "priority_counts": priority_counts,
        "improvement_plans": improvement_plans,
        "fragile_closures_needing_action": fragile_needing_action,
        "top_blocking_gaps": top_blocking_gaps,
        "expected_stability_gains": stability_gains,
        "suggested_followup_modes": followup_modes,
    }
