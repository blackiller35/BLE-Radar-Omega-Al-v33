"""Lightweight operator resolution quality / stability assessment system."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


_ALLOWED_SCOPE_TYPES = {"device", "case", "cluster", "campaign", "evidence_pack", "queue_item"}
_QUALITY_LEVELS = {"durable", "mostly_stable", "fragile", "likely_to_reopen", "insufficient_resolution"}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _slug(value: Any) -> str:
    return str(value or "unknown").replace(":", "").replace("/", "-").replace(" ", "_").lower()


def _find_scope_rows(scope_id: str, rows: List[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
    sid = _norm(scope_id)
    if not sid:
        return []

    out: List[Dict[str, Any]] = []
    for row in rows:
        for key in keys:
            if _norm(row.get(key)) == sid:
                out.append(row)
                break
    return out


def _compute_supporting_factors(
    *,
    closure_count: int,
    reopened_count: int,
    escalation_count: int,
    monitoring_active: bool,
    has_strong_evidence: bool,
    timeline_stable: bool,
    matches_resolved_outcome: bool,
) -> List[str]:
    """Extract positive factors that support resolution quality."""
    factors: List[str] = []

    if closure_count > 0:
        factors.append("closed")
    if reopened_count == 0 and closure_count > 0:
        factors.append("no_reopens")
    if escalation_count == 0:
        factors.append("no_escalations")
    if has_strong_evidence:
        factors.append("strong_supporting_evidence")
    if timeline_stable:
        factors.append("stable_timeline")
    if matches_resolved_outcome:
        factors.append("matches_resolved_outcome")
    if monitoring_active:
        factors.append("under_post_closure_watch")

    return factors[:5]  # Top 5


def _compute_weak_factors(
    *,
    reopened_count: int,
    escalation_count: int,
    weak_confidence: bool,
    low_evidence_count: bool,
    monitoring_triggered: bool,
    monitoring_mode: str,
    outcome_labels: List[str],
) -> List[str]:
    """Extract negative factors that undermine resolution quality."""
    factors: List[str] = []

    if reopened_count >= 2:
        factors.append("multiple_reopens")
    elif reopened_count == 1:
        factors.append("previously_reopened")

    if escalation_count > 0:
        factors.append("requires_escalation")

    if weak_confidence:
        factors.append("weak_closure_confidence")

    if low_evidence_count:
        factors.append("insufficient_evidence")

    if monitoring_triggered:
        factors.append("monitoring_triggered_concern")

    if "resolved_but_returned" in outcome_labels:
        factors.append("resolution_not_durable")

    if _norm(monitoring_mode) in {"high_attention_post_closure", "watch_for_recurrence"}:
        factors.append("high_attention_monitoring_required")

    return factors[:5]  # Top 5


def _compute_stability_score(
    *,
    closure_count: int,
    reopened_count: int,
    escalation_count: int,
    weak_evidence_count: int,
    monitoring_mode: str,
    closure_confidence: float,
    timeline_days: int,
) -> int:
    """Compute stability score from 0-100."""
    score = 50  # Baseline

    # Closure increases score
    if closure_count > 0:
        score += 20

    # Reopens decrease score significantly
    if reopened_count >= 2:
        score -= 25
    elif reopened_count == 1:
        score -= 15

    # Escalations decrease score
    if escalation_count > 0:
        score -= 20

    # Weak evidence decreases score
    if weak_evidence_count > 2:
        score -= 15
    elif weak_evidence_count > 0:
        score -= 5

    # Monitoring mode affects score
    m = _norm(monitoring_mode)
    if m == "high_attention_post_closure":
        score -= 20
    elif m == "watch_for_recurrence":
        score -= 10

    # Confidence affects score
    conf = float(closure_confidence or 0.5)
    score += int((conf - 0.5) * 40)

    # Timeline (more stable time = higher score)
    if timeline_days >= 30:
        score += 15
    elif timeline_days >= 14:
        score += 10
    elif timeline_days >= 7:
        score += 5

    return max(0, min(100, score))


def _compute_reopen_risk(
    *,
    reopened_count: int,
    escalation_count: int,
    weak_evidence_count: int,
    monitoring_triggered: bool,
    queue_state: str,
    pattern_count: int,
    timeline_days: int,
) -> int:
    """Compute reopen risk from 0-100."""
    risk = 10  # Base low risk

    # Reopens increase risk
    if reopened_count >= 3:
        risk += 40
    elif reopened_count >= 2:
        risk += 25
    elif reopened_count == 1:
        risk += 15

    # Escalations increase risk
    if escalation_count >= 2:
        risk += 20
    elif escalation_count == 1:
        risk += 10

    # Weak evidence increases risk
    if weak_evidence_count > 2:
        risk += 20
    elif weak_evidence_count > 0:
        risk += 10

    # Monitoring triggered is a sign
    if monitoring_triggered:
        risk += 15

    # Queue state affects risk
    q = _norm(queue_state)
    if q in {"waiting", "blocked"}:
        risk += 10

    # Patterns increase risk
    if pattern_count >= 3:
        risk += 15
    elif pattern_count > 0:
        risk += 5

    # Timeline (less time = higher risk)
    if timeline_days < 3:
        risk += 20
    elif timeline_days < 7:
        risk += 10

    return max(0, min(100, risk))


def _compute_recommended_improvement(
    *,
    weak_factors: List[str],
    resolution_quality: str,
    weak_evidence_count: int,
    monitoring_mode: str,
    reopen_risk: int,
) -> str:
    """Generate recommended improvement based on analysis."""
    if resolution_quality == "durable":
        return "maintain_current_process"
    if resolution_quality == "insufficient_resolution":
        return "require_more_evidence_or_specialists"
    if resolution_quality == "likely_to_reopen":
        if reopen_risk > 70:
            return "proactive_monitoring_or_early_reopen"
        return "enhanced_monitoring_recommended"
    if resolution_quality == "fragile":
        if weak_evidence_count > 2:
            return "supplement_evidence_before_final_closure"
        if "multiple_reopens" in weak_factors:
            return "specialist_review_required"
        return "extended_monitoring_required"
    # mostly_stable
    if "previously_reopened" in weak_factors:
        return "scheduled_recheck_recommended"
    return "continue_with_caution"


def _days_since_closure(closure_timestamp: Optional[str]) -> int:
    """Calculate days since closure."""
    if not closure_timestamp:
        return 0
    try:
        from datetime import datetime as dt
        closure_dt = dt.strptime(str(closure_timestamp)[:10], "%Y-%m-%d")
        now_dt = dt.now()
        delta = now_dt - closure_dt
        return max(0, delta.days)
    except Exception:
        return 0


def build_operator_resolution_quality_records(
    quality_scopes: Optional[List[Dict[str, Any]]] = None,
    *,
    lineage_records: Optional[List[Dict[str, Any]]] = None,
    closure_packages: Optional[List[Dict[str, Any]]] = None,
    reopen_policy_records: Optional[List[Dict[str, Any]]] = None,
    post_closure_monitoring_policies: Optional[List[Dict[str, Any]]] = None,
    operator_outcomes: Optional[List[Dict[str, Any]]] = None,
    escalation_feedback: Optional[List[Dict[str, Any]]] = None,
    recommendation_tuning: Optional[List[Dict[str, Any]]] = None,
    pattern_library: Optional[List[Dict[str, Any]]] = None,
    pattern_matches: Optional[List[Dict[str, Any]]] = None,
    operator_queue_context: Optional[List[Dict[str, Any]]] = None,
    session_journal: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build compact resolution quality records from lineage and closure signals."""
    lineage_rows = list(lineage_records or [])
    closure_rows = list(closure_packages or [])
    reopen_rows = list(reopen_policy_records or [])
    monitoring_rows = list(post_closure_monitoring_policies or [])
    outcome_rows = list(operator_outcomes or [])
    feedback_rows = list(escalation_feedback or [])
    tuning_rows = list(recommendation_tuning or [])
    pattern_rows = list(pattern_library or [])
    match_rows = list(pattern_matches or [])
    queue_rows = list(operator_queue_context or [])
    journal = session_journal if isinstance(session_journal, dict) else {}

    stamp = str(generated_at or _now())
    quality_rows: List[Dict[str, Any]] = []

    # Extract all lineage records to build quality assessment
    for lineage_row in lineage_rows:
        scope_type = str(lineage_row.get("scope_type", "device"))
        scope_id = str(lineage_row.get("scope_id", "-"))
        lineage_id = str(lineage_row.get("lineage_id", "unknown"))

        if scope_type not in _ALLOWED_SCOPE_TYPES or not scope_id or scope_id == "-":
            continue

        # Find related records
        scoped_closures = _find_scope_rows(scope_id, closure_rows, ["scope_id"])
        scoped_reopens = _find_scope_rows(scope_id, reopen_rows, ["scope_id"])
        scoped_monitoring = _find_scope_rows(scope_id, monitoring_rows, ["scope_id"])
        scoped_outcomes = _find_scope_rows(scope_id, outcome_rows, ["scope_id"])
        scoped_feedback = _find_scope_rows(scope_id, feedback_rows, ["scope_id"])
        scoped_patterns = _find_scope_rows(scope_id, pattern_rows, ["scope_id"])
        scoped_matches = _find_scope_rows(scope_id, match_rows, ["scope_id"])
        scoped_queue = _find_scope_rows(scope_id, queue_rows, ["scope_id", "item_id"])

        # Extract metrics from lineage
        closure_count = int(lineage_row.get("closure_count", 0))
        reopened_count = int(lineage_row.get("reopened_count", 0))
        escalation_count = int(lineage_row.get("escalation_count", 0))

        # Closure metadata
        closure_id = str((scoped_closures[0] if scoped_closures else {}).get("closure_id", "unknown"))
        closure_confidence = float((scoped_closures[0] if scoped_closures else {}).get("closure_confidence", 0.5))
        closure_timestamp = str((scoped_closures[0] if scoped_closures else {}).get("closed_at", ""))

        # Evidence and confidence
        weak_evidence_count = len(
            [
                r for r in scoped_outcomes
                if bool(r.get("weak_confidence")) or _norm(r.get("confidence_level")) == "low"
            ]
        )
        has_strong_evidence = weak_evidence_count == 0 and len(scoped_outcomes) > 0
        low_evidence_count = weak_evidence_count > 0

        # Outcome labels
        outcome_labels = []
        for row in scoped_outcomes[:3]:
            label = str(row.get("outcome_label") or "")
            if label:
                outcome_labels.append(label)

        # Monitoring
        monitoring_mode = str((scoped_monitoring[0] if scoped_monitoring else {}).get("monitoring_mode", ""))
        monitoring_active = len(scoped_monitoring) > 0 and _norm(monitoring_mode) != ""
        monitoring_triggered = bool((scoped_monitoring[0] if scoped_monitoring else {}).get("monitoring_triggered"))

        # Timeline stability
        timeline_days = _days_since_closure(closure_timestamp)
        timeline_stable = timeline_days >= 7  # Stable if 7+ days without reopen

        # Queue state
        queue_state = str((scoped_queue[0] if scoped_queue else {}).get("queue_state", "resolved"))

        # Pattern count (as risk indicator)
        pattern_count = len(scoped_matches)

        # Resolution outcome match
        matches_resolved_outcome = any(
            _norm(r.get("outcome_label")) in {"resolved_cleanly", "stabilized"}
            for r in scoped_outcomes
        )

        # Compute quality metrics
        supporting_factors = _compute_supporting_factors(
            closure_count=closure_count,
            reopened_count=reopened_count,
            escalation_count=escalation_count,
            monitoring_active=monitoring_active,
            has_strong_evidence=has_strong_evidence,
            timeline_stable=timeline_stable,
            matches_resolved_outcome=matches_resolved_outcome,
        )

        weak_factors = _compute_weak_factors(
            reopened_count=reopened_count,
            escalation_count=escalation_count,
            weak_confidence=closure_confidence < 0.7,
            low_evidence_count=low_evidence_count,
            monitoring_triggered=monitoring_triggered,
            monitoring_mode=monitoring_mode,
            outcome_labels=outcome_labels,
        )

        stability_score = _compute_stability_score(
            closure_count=closure_count,
            reopened_count=reopened_count,
            escalation_count=escalation_count,
            weak_evidence_count=weak_evidence_count,
            monitoring_mode=monitoring_mode,
            closure_confidence=closure_confidence,
            timeline_days=timeline_days,
        )

        reopen_risk = _compute_reopen_risk(
            reopened_count=reopened_count,
            escalation_count=escalation_count,
            weak_evidence_count=weak_evidence_count,
            monitoring_triggered=monitoring_triggered,
            queue_state=queue_state,
            pattern_count=pattern_count,
            timeline_days=timeline_days,
        )

        # Determine resolution quality level
        if closure_count == 0:
            resolution_quality = "insufficient_resolution"
        elif reopen_risk >= 70:
            resolution_quality = "likely_to_reopen"
        elif reopened_count >= 2 or weak_evidence_count >= 3 or stability_score < 30:
            resolution_quality = "fragile"
        elif reopened_count == 1 or weak_evidence_count > 0 or stability_score < 60:
            resolution_quality = "mostly_stable"
        else:
            resolution_quality = "durable"

        recommended_improvement = _compute_recommended_improvement(
            weak_factors=weak_factors,
            resolution_quality=resolution_quality,
            weak_evidence_count=weak_evidence_count,
            monitoring_mode=monitoring_mode,
            reopen_risk=reopen_risk,
        )

        quality_rows.append(
            {
                "quality_id": f"quality-{scope_type}-{_slug(scope_id)}",
                "scope_type": scope_type,
                "scope_id": scope_id,
                "lineage_id": lineage_id,
                "closure_id": closure_id,
                "resolution_quality": resolution_quality,
                "stability_score": stability_score,
                "reopen_risk": reopen_risk,
                "supporting_factors": supporting_factors,
                "weak_factors": weak_factors,
                "recommended_improvement": recommended_improvement,
                "evaluated_at": stamp,
            }
        )

    # Sort by quality (best to worst) then by stability score
    quality_rows.sort(
        key=lambda r: (
            {"durable": 0, "mostly_stable": 1, "fragile": 2, "likely_to_reopen": 3, "insufficient_resolution": 4}.get(
                str(r.get("resolution_quality")), 5
            ),
            int(r.get("stability_score", 0)),
            int(r.get("reopen_risk", 100)),
        ),
    )

    return quality_rows[:64]


def summarize_operator_resolution_quality(
    quality_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build compact dashboard sections for resolution quality panel."""
    rows = list(quality_rows or [])

    resolution_quality_summary = {
        "durable": len([r for r in rows if str(r.get("resolution_quality")) == "durable"]),
        "mostly_stable": len([r for r in rows if str(r.get("resolution_quality")) == "mostly_stable"]),
        "fragile": len([r for r in rows if str(r.get("resolution_quality")) == "fragile"]),
        "likely_to_reopen": len([r for r in rows if str(r.get("resolution_quality")) == "likely_to_reopen"]),
        "insufficient_resolution": len([r for r in rows if str(r.get("resolution_quality")) == "insufficient_resolution"]),
    }

    durable_closures = [
        r for r in rows
        if str(r.get("resolution_quality")) == "durable"
    ][:8]

    fragile_closures = [
        r for r in rows
        if str(r.get("resolution_quality")) in {"fragile", "likely_to_reopen"}
    ][:8]

    likely_reopeners = [
        r for r in rows
        if int(r.get("reopen_risk", 0)) >= 70
    ][:8]

    improvement_suggestions = []
    for r in rows[:20]:
        rec = str(r.get("recommended_improvement", "none"))
        if rec and rec not in {"none", "maintain_current_process"}:
            improvement_suggestions.append(
                {
                    "scope_type": str(r.get("scope_type")),
                    "scope_id": str(r.get("scope_id")),
                    "recommendation": rec,
                    "quality": str(r.get("resolution_quality")),
                }
            )

    return {
        "resolution_quality": resolution_quality_summary,
        "durable_closures": durable_closures,
        "fragile_closures": fragile_closures,
        "likely_reopeners": likely_reopeners,
        "improvement_suggestions": improvement_suggestions[:8],
    }
