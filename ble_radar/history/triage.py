"""Lightweight operator triage scoring.

``compute_triage`` takes a device dict plus optional context (registry record,
watch/case record, movement status) and returns a triage assessment:

    {
        "triage_score":  int   0–100,
        "short_reason":  str   human-readable signal list,
        "triage_bucket": str   "critical" | "review" | "watch" | "normal",
    }

Scoring table (additive, capped at 100):

    Signal                              Points
    ─────────────────────────────────── ──────
    alert_level == "critique"             60
    alert_level == "élevé"                25
    alert_level == "moyen"                10
    watch_hit == True                     20
    case status == "escalated"            25
    case status == "watch"                15
    possible_suivi == True                15
    "tracker" in profile (lower)          15
    follow_score >= 3                     10
    movement_status == "new"              10
    registry_score >= 80                  15
    registry_score in [60, 79]            10

Bucket thresholds:
    critical : triage_score >= 45
    review   : triage_score >= 25
    watch    : triage_score >= 10
    normal   : triage_score <  10
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Scoring rules  —  each rule is a (label, points) pair or callable
# ---------------------------------------------------------------------------

def _score_rules(
    device: Dict[str, Any],
    registry_record: Optional[Dict[str, Any]],
    case_record: Optional[Dict[str, Any]],
    movement_status: Optional[str],
    registry_score: int,
) -> List[Tuple[str, int]]:
    """Return a list of (label, points) for every fired rule."""
    hits: List[Tuple[str, int]] = []

    alert = str(device.get("alert_level", "")).lower()
    if alert == "critique":
        hits.append(("alert:critique", 60))
    elif alert == "élevé":
        hits.append(("alert:élevé", 25))
    elif alert == "moyen":
        hits.append(("alert:moyen", 10))

    if device.get("watch_hit"):
        hits.append(("watch_hit", 20))

    if case_record:
        cs = str(case_record.get("status", "")).lower()
        if cs == "escalated":
            hits.append(("case:escalated", 25))
        elif cs == "watch":
            hits.append(("case:watch", 15))

    if device.get("possible_suivi"):
        hits.append(("possible_suivi", 15))
    elif "tracker" in str(device.get("profile", "")).lower():
        hits.append(("tracker_profile", 15))

    if _safe_int(device.get("follow_score", 0)) >= 3:
        hits.append(("follow_score≥3", 10))

    if movement_status == "new":
        hits.append(("movement:new", 10))

    if registry_score >= 80:
        hits.append(("registry_score≥80", 15))
    elif registry_score >= 60:
        hits.append(("registry_score≥60", 10))

    return hits


def _bucket(score: int) -> str:
    if score >= 45:
        return "critical"
    if score >= 25:
        return "review"
    if score >= 10:
        return "watch"
    return "normal"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_triage(
    device: Dict[str, Any],
    *,
    registry_record: Optional[Dict[str, Any]] = None,
    case_record: Optional[Dict[str, Any]] = None,
    movement_status: Optional[str] = None,
    registry_score: Optional[int] = None,
) -> Dict[str, Any]:
    """Compute a triage assessment for *device*.

    Parameters
    ----------
    device:
        Normalised device dict (fields: alert_level, watch_hit,
        possible_suivi, profile, follow_score, …).
    registry_record:
        Entry from ``load_registry()`` for this address (may be ``None``).
    case_record:
        Entry from ``load_cases()`` for this address (may be ``None``).
    movement_status:
        String from ``_movement_for_address()`` or equivalent: ``"new"``,
        ``"recurring"``, ``"disappeared"``, ``"unknown"``.
    registry_score:
        Pre-computed score from ``compute_device_score()``.  If ``None``,
        defaults to 0 (no penalty — caller can omit it safely).

    Returns
    -------
    dict with keys ``triage_score`` (int), ``short_reason`` (str),
    ``triage_bucket`` (str).
    """
    reg_score = _safe_int(registry_score, 0)

    hits = _score_rules(
        device,
        registry_record=registry_record,
        case_record=case_record,
        movement_status=movement_status,
        registry_score=reg_score,
    )

    raw = sum(pts for _, pts in hits)
    score = min(100, raw)
    reason = ", ".join(label for label, _ in hits) if hits else "no signals"

    return {
        "triage_score": score,
        "short_reason": reason,
        "triage_bucket": _bucket(score),
    }


def triage_device_list(
    devices: List[Dict[str, Any]],
    *,
    registry: Optional[Dict[str, Any]] = None,
    watch_cases: Optional[Dict[str, Any]] = None,
    movement: Optional[Dict[str, Any]] = None,
    registry_scores: Optional[Dict[str, int]] = None,
) -> List[Dict[str, Any]]:
    """Triage a full device list; return results sorted by score descending.

    Each result dict:
        address, name, triage_score, short_reason, triage_bucket
    """
    results = []
    for d in devices:
        addr = str(d.get("address", "")).strip().upper()
        reg_rec = (registry or {}).get(addr)
        case_rec = (watch_cases or {}).get(addr)

        mov_status: Optional[str] = None
        if movement:
            for entry in movement.get("new", []):
                if str(entry.get("address", "")).upper() == addr:
                    mov_status = "new"
                    break
            if mov_status is None:
                for entry in movement.get("recurring", []):
                    if str(entry.get("address", "")).upper() == addr:
                        mov_status = "recurring"
                        break

        reg_score = (registry_scores or {}).get(addr)

        triage = compute_triage(
            d,
            registry_record=reg_rec,
            case_record=case_rec,
            movement_status=mov_status,
            registry_score=reg_score,
        )

        results.append({
            "address": addr,
            "name": d.get("name", "Inconnu"),
            **triage,
        })

    results.sort(key=lambda r: r["triage_score"], reverse=True)
    return results
