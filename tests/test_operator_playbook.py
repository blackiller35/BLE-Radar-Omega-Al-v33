"""Tests for ble_radar.history.operator_playbook (step 12)."""
from __future__ import annotations

import pytest


def _mod():
    import ble_radar.history.operator_playbook as m
    return m


def test_recommend_operator_playbook_empty_address_raises():
    m = _mod()
    with pytest.raises(ValueError):
        m.recommend_operator_playbook("")


def test_returns_required_keys():
    m = _mod()
    out = m.recommend_operator_playbook("AA:BB:CC:DD:EE:FF")
    for key in ("playbook_id", "recommended_action", "reason", "priority", "suggested_steps"):
        assert key in out


def test_resolved_case_returns_close_monitor_playbook():
    m = _mod()
    out = m.recommend_operator_playbook(
        "AA:BB:CC:DD:EE:FF",
        case_record={"status": "resolved"},
        triage_row={"triage_score": 90, "triage_bucket": "critical", "short_reason": "x"},
    )
    assert out["playbook_id"] == "pb-close-monitor"
    assert out["priority"] == "low"


def test_critical_without_pack_recommends_pack_generation():
    m = _mod()
    out = m.recommend_operator_playbook(
        "AA:BB:CC:DD:EE:FF",
        triage_row={"triage_score": 60, "triage_bucket": "critical", "short_reason": "alert:critique"},
        investigation_profile={"incident_refs": {"device_packs": [], "incident_packs": []}},
    )
    assert out["playbook_id"] == "pb-critical-pack"
    assert out["priority"] == "critical"
    assert any("incident pack" in s.lower() for s in out["suggested_steps"])


def test_critical_with_pack_recommends_active_investigation():
    m = _mod()
    out = m.recommend_operator_playbook(
        "AA:BB:CC:DD:EE:FF",
        triage_row={"triage_score": 52, "triage_bucket": "critical", "short_reason": "alert:critique"},
        investigation_profile={"incident_refs": {"device_packs": ["AABB_2026"], "incident_packs": []}},
    )
    assert out["playbook_id"] == "pb-critical-investigate"


def test_pack_detected_from_timeline_event():
    m = _mod()
    out = m.recommend_operator_playbook(
        "AA:BB:CC:DD:EE:FF",
        triage_row={"triage_score": 50, "triage_bucket": "critical", "short_reason": "alert:critique"},
        timeline_events=[{"source": "incident_pack", "action": "generated"}],
    )
    assert out["playbook_id"] == "pb-critical-investigate"


def test_review_bucket_returns_review_playbook():
    m = _mod()
    out = m.recommend_operator_playbook(
        "AA:BB:CC:DD:EE:FF",
        triage_row={"triage_score": 31, "triage_bucket": "review", "short_reason": "watch_hit"},
        case_record={"status": "review"},
    )
    assert out["playbook_id"] == "pb-review-triage"
    assert out["priority"] == "high"


def test_review_playbook_adds_score_change_step_when_timeline_has_hint():
    m = _mod()
    out = m.recommend_operator_playbook(
        "AA:BB:CC:DD:EE:FF",
        triage_row={"triage_score": 27, "triage_bucket": "review", "short_reason": "registry_score≥60"},
        timeline_events=[{"action": "change_hint"}],
    )
    joined = " | ".join(out["suggested_steps"])
    assert "score-change" in joined.lower() or "score-change trend" in joined.lower() or "score-change" in joined


def test_watch_bucket_returns_watch_playbook():
    m = _mod()
    out = m.recommend_operator_playbook(
        "AA:BB:CC:DD:EE:FF",
        triage_row={"triage_score": 12, "triage_bucket": "watch", "short_reason": "watch_hit"},
        case_record={"status": "watch"},
    )
    assert out["playbook_id"] == "pb-watch-monitor"
    assert out["priority"] == "medium"


def test_triage_fallback_from_investigation_profile_when_row_missing():
    m = _mod()
    out = m.recommend_operator_playbook(
        "AA:BB:CC:DD:EE:FF",
        investigation_profile={
            "triage": {"triage_score": 29, "triage_bucket": "review", "short_reason": "fallback"},
            "case": {"status": "new"},
            "incident_refs": {"device_packs": [], "incident_packs": []},
        },
    )
    assert out["playbook_id"] == "pb-review-triage"


def test_normal_default_returns_observe_baseline():
    m = _mod()
    out = m.recommend_operator_playbook(
        "AA:BB:CC:DD:EE:FF",
        triage_row={"triage_score": 0, "triage_bucket": "normal", "short_reason": "no signals"},
        case_record={"status": "none"},
    )
    assert out["playbook_id"] == "pb-observe-baseline"
    assert out["priority"] == "low"
