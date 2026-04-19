"""Lightweight operator lifecycle lineage / multi-cycle history system."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple


_ALLOWED_SCOPE_TYPES = {"device", "case", "cluster", "campaign", "evidence_pack", "queue_item"}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _slug(value: Any) -> str:
    return str(value or "unknown").replace(":", "").replace("/", "-").replace(" ", "_").lower()


def _scope_identity(row: Dict[str, Any]) -> Tuple[str, str]:
    scope_type = _norm(row.get("scope_type") or "device")
    scope_id = str(row.get("scope_id") or row.get("item_id") or row.get("campaign_id") or row.get("pack_id") or "").strip()
    return scope_type, scope_id


def _register_scope(scope_map: Dict[Tuple[str, str], Dict[str, Any]], scope_type: str, scope_id: str) -> None:
    if scope_type not in _ALLOWED_SCOPE_TYPES:
        return
    if not scope_id:
        return
    key = (scope_type, _norm(scope_id))
    if key not in scope_map:
        scope_map[key] = {
            "scope_type": scope_type,
            "scope_id": scope_id,
        }


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


def _timeline_summary(opened_count: int, escalations: int, closures: int, reopens: int) -> str:
    return f"opened={opened_count} | escalations={escalations} | closures={closures} | reopens={reopens}"


def _current_lifecycle_state(
    *,
    queue_state: str,
    closure_count: int,
    reopened_count: int,
    escalation_count: int,
    monitoring_mode: str,
) -> str:
    q = _norm(queue_state)
    m = _norm(monitoring_mode)

    if reopened_count > 0 and closure_count > reopened_count and q in {"resolved", "closed", "monitoring", "archived"}:
        return "stabilized_after_reopen"
    if reopened_count > 0 and q in {"in_review", "ready", "waiting", "blocked"}:
        return "reopened_active"
    if escalation_count > 0 and q in {"in_review", "ready", "waiting", "blocked", "escalated"}:
        return "escalated_active"
    if closure_count > 0 and m in {"watch_for_recurrence", "scheduled_recheck", "high_attention_post_closure"}:
        return "monitoring_post_closure"
    if closure_count > 0:
        return "closed"
    if q in {"in_review", "ready", "waiting", "blocked", "new"}:
        return "active"
    return "active"


def _recurring_pattern_summary(
    *,
    pattern_rows: List[Dict[str, Any]],
    match_rows: List[Dict[str, Any]],
    reopen_rows: List[Dict[str, Any]],
) -> str:
    names: List[str] = []

    for row in match_rows[:3]:
        pid = str(row.get("pattern_id") or "").strip()
        if pid:
            names.append(pid)

    if not names:
        for row in pattern_rows[:3]:
            title = str(row.get("title") or row.get("pattern_id") or "").strip()
            if title:
                names.append(title)

    if not names and reopen_rows:
        names.append("reopen_pattern_history")

    if not names:
        return "none"

    deduped: List[str] = []
    seen: Set[str] = set()
    for item in names:
        key = _norm(item)
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)

    return " | ".join(deduped[:3])


def build_operator_lifecycle_lineage_records(
    lineage_scopes: Optional[List[Dict[str, Any]]] = None,
    *,
    outcomes: Optional[List[Dict[str, Any]]] = None,
    closure_packages: Optional[List[Dict[str, Any]]] = None,
    post_closure_monitoring_policies: Optional[List[Dict[str, Any]]] = None,
    reopen_policy_records: Optional[List[Dict[str, Any]]] = None,
    escalation_packages: Optional[List[Dict[str, Any]]] = None,
    escalation_feedback: Optional[List[Dict[str, Any]]] = None,
    session_journal: Optional[Dict[str, Any]] = None,
    pattern_library: Optional[List[Dict[str, Any]]] = None,
    pattern_matches: Optional[List[Dict[str, Any]]] = None,
    operator_queue_context: Optional[List[Dict[str, Any]]] = None,
    campaign_tracking: Optional[List[Dict[str, Any]]] = None,
    evidence_packs: Optional[List[Dict[str, Any]]] = None,
    generated_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build compact lifecycle lineage records from existing project signals."""
    scope_rows = list(lineage_scopes or [])
    outcome_rows = list(outcomes or [])
    closure_rows = list(closure_packages or [])
    monitoring_rows = list(post_closure_monitoring_policies or [])
    reopen_rows = list(reopen_policy_records or [])
    escalation_rows = list(escalation_packages or [])
    feedback_rows = list(escalation_feedback or [])
    pattern_rows = list(pattern_library or [])
    match_rows = list(pattern_matches or [])
    queue_rows = list(operator_queue_context or [])
    campaign_rows = list(campaign_tracking or [])
    pack_rows = list(evidence_packs or [])
    journal = session_journal if isinstance(session_journal, dict) else {}

    stamp = str(generated_at or _now())

    scopes: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for row in scope_rows:
        scope_type, scope_id = _scope_identity(row)
        _register_scope(scopes, scope_type, scope_id)

    for row in queue_rows:
        scope_type, scope_id = _scope_identity(row)
        _register_scope(scopes, scope_type, scope_id)
        item_id = str(row.get("item_id") or "").strip()
        if item_id:
            _register_scope(scopes, "queue_item", item_id)

    for row in campaign_rows:
        campaign_id = str(row.get("campaign_id") or row.get("scope_id") or "").strip()
        _register_scope(scopes, "campaign", campaign_id)

    for row in pack_rows:
        pack_id = str(row.get("pack_id") or row.get("scope_id") or "").strip()
        _register_scope(scopes, "evidence_pack", pack_id)

    for row in closure_rows:
        scope_type, scope_id = _scope_identity(row)
        _register_scope(scopes, scope_type, scope_id)

    lineage_rows: List[Dict[str, Any]] = []

    for _, scope in scopes.items():
        scope_type = str(scope.get("scope_type"))
        scope_id = str(scope.get("scope_id"))

        scoped_outcomes = _find_scope_rows(scope_id, outcome_rows, ["scope_id"])
        scoped_closures = _find_scope_rows(scope_id, closure_rows, ["scope_id"])
        scoped_monitoring = _find_scope_rows(scope_id, monitoring_rows, ["scope_id"])
        scoped_reopens = _find_scope_rows(scope_id, reopen_rows, ["scope_id"])
        scoped_escalations = _find_scope_rows(scope_id, escalation_rows, ["scope_id"])
        scoped_feedback = _find_scope_rows(scope_id, feedback_rows, ["scope_id"])
        scoped_patterns = _find_scope_rows(scope_id, pattern_rows, ["scope_id", "pattern_id"])
        scoped_matches = _find_scope_rows(scope_id, match_rows, ["scope_id"])
        scoped_queue = _find_scope_rows(scope_id, queue_rows, ["scope_id", "item_id"])
        scoped_campaigns = _find_scope_rows(scope_id, campaign_rows, ["campaign_id", "scope_id"])
        scoped_packs = _find_scope_rows(scope_id, pack_rows, ["pack_id", "scope_id"])

        opened_count = max(1, len(scoped_queue) or len(scoped_outcomes) or len(scoped_campaigns) or len(scoped_packs))
        closure_count = len(scoped_closures)
        reopen_from_outcomes = len(
            [
                r for r in scoped_outcomes
                if bool(r.get("reopened")) or _norm(r.get("outcome_label")) in {"resolved_but_returned", "reopened", "reopen"}
            ]
        )
        reopened_count = max(len(scoped_reopens), reopen_from_outcomes)
        escalation_count = max(len(scoped_escalations), len(scoped_feedback))

        cycle_count = max(1, closure_count + reopened_count)

        last_trigger_type = "none"
        if scoped_reopens:
            last_trigger_type = str(scoped_reopens[0].get("trigger_type") or "none")
        elif scoped_monitoring:
            triggers = list((scoped_monitoring[0].get("reopen_triggers") or []))
            if triggers:
                last_trigger_type = str(triggers[0])
        elif scoped_escalations:
            last_trigger_type = str(scoped_escalations[0].get("escalation_reason") or "none")

        queue_state = str((scoped_queue[0] if scoped_queue else {}).get("queue_state") or "new")
        monitoring_mode = str((scoped_monitoring[0] if scoped_monitoring else {}).get("monitoring_mode") or "")

        timeline_summary = _timeline_summary(opened_count, escalation_count, closure_count, reopened_count)
        recurring_summary = _recurring_pattern_summary(
            pattern_rows=scoped_patterns,
            match_rows=scoped_matches,
            reopen_rows=scoped_reopens,
        )
        lifecycle_state = _current_lifecycle_state(
            queue_state=queue_state,
            closure_count=closure_count,
            reopened_count=reopened_count,
            escalation_count=escalation_count,
            monitoring_mode=monitoring_mode,
        )

        if not scoped_outcomes and not scoped_closures and not scoped_reopens and not scoped_escalations and not scoped_feedback:
            # Keep lineage compact by only retaining scopes with observable lifecycle signals.
            continue

        lineage_rows.append(
            {
                "lineage_id": f"lineage-{scope_type}-{_slug(scope_id)}",
                "scope_type": scope_type,
                "scope_id": scope_id,
                "cycle_count": cycle_count,
                "opened_count": opened_count,
                "reopened_count": reopened_count,
                "closure_count": closure_count,
                "escalation_count": escalation_count,
                "last_trigger_type": str(last_trigger_type or "none"),
                "recurring_pattern_summary": recurring_summary,
                "timeline_summary": timeline_summary,
                "current_lifecycle_state": lifecycle_state,
                "updated_at": stamp,
            }
        )

    lineage_rows.sort(
        key=lambda r: (
            int(r.get("cycle_count", 0)),
            int(r.get("reopened_count", 0)),
            int(r.get("escalation_count", 0)),
            str(r.get("updated_at", "")),
        ),
        reverse=True,
    )

    return lineage_rows[:64]


def summarize_operator_lifecycle_lineage(
    lineage_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build compact dashboard sections for lifecycle lineage panel."""
    rows = list(lineage_rows or [])

    repeated_reopeners = [
        r for r in rows
        if int(r.get("reopened_count", 0)) >= 2
    ][:10]

    recurring_triggers = [
        {
            "scope_type": str(r.get("scope_type", "-")),
            "scope_id": str(r.get("scope_id", "-")),
            "last_trigger_type": str(r.get("last_trigger_type", "none")),
            "reopened_count": int(r.get("reopened_count", 0)),
        }
        for r in rows
        if _norm(r.get("last_trigger_type")) not in {"", "none"}
    ][:10]

    multi_cycle_cases = [
        r for r in rows
        if str(r.get("scope_type")) == "case" and int(r.get("cycle_count", 0)) >= 2
    ][:10]

    stabilized_after_reopen = [
        r for r in rows
        if _norm(r.get("current_lifecycle_state")) == "stabilized_after_reopen"
    ][:10]

    return {
        "lifecycle_lineage": rows[:12],
        "repeated_reopeners": repeated_reopeners,
        "recurring_triggers": recurring_triggers,
        "multi_cycle_cases": multi_cycle_cases,
        "stabilized_after_reopen": stabilized_after_reopen,
    }
