"""Tests for ble_radar/history/triage.py — operator triage system."""
import pytest
from ble_radar.history.triage import compute_triage, triage_device_list


# ---------------------------------------------------------------------------
# compute_triage — bucket boundaries
# ---------------------------------------------------------------------------

def test_normal_bucket_no_signals():
    result = compute_triage({})
    assert result["triage_bucket"] == "normal"
    assert result["triage_score"] == 0
    assert result["short_reason"] == "no signals"


def test_watch_bucket_medium_alert():
    result = compute_triage({"alert_level": "moyen"})
    assert result["triage_bucket"] == "watch"
    assert result["triage_score"] == 10


def test_review_bucket_high_alert():
    result = compute_triage({"alert_level": "élevé"})
    assert result["triage_bucket"] == "review"
    assert result["triage_score"] == 25


def test_critical_bucket_critique_alert():
    result = compute_triage({"alert_level": "critique"})
    assert result["triage_bucket"] == "critical"
    assert result["triage_score"] == 60


def test_critical_bucket_high_with_watch_hit():
    # élevé(25) + watch_hit(20) = 45 → critical
    result = compute_triage({"alert_level": "élevé", "watch_hit": True})
    assert result["triage_bucket"] == "critical"
    assert result["triage_score"] == 45


# ---------------------------------------------------------------------------
# compute_triage — individual signal points
# ---------------------------------------------------------------------------

def test_watch_hit_adds_20():
    result = compute_triage({"watch_hit": True})
    assert result["triage_score"] == 20
    assert "watch_hit" in result["short_reason"]


def test_case_watch_adds_15():
    case = {"status": "watch"}
    result = compute_triage({}, case_record=case)
    assert result["triage_score"] == 15
    assert "case:watch" in result["short_reason"]


def test_case_escalated_adds_25():
    case = {"status": "escalated"}
    result = compute_triage({}, case_record=case)
    assert result["triage_score"] == 25
    assert "case:escalated" in result["short_reason"]


def test_possible_suivi_adds_15():
    result = compute_triage({"possible_suivi": True})
    assert result["triage_score"] == 15
    assert "possible_suivi" in result["short_reason"]


def test_tracker_profile_adds_15():
    result = compute_triage({"profile": "tracker_ble"})
    assert result["triage_score"] == 15
    assert "tracker_profile" in result["short_reason"]


def test_possible_suivi_takes_precedence_over_tracker_profile():
    # Both set — only possible_suivi rule fires (no double-count)
    result = compute_triage({"possible_suivi": True, "profile": "tracker_ble"})
    assert result["triage_score"] == 15


def test_follow_score_ge_3_adds_10():
    result = compute_triage({"follow_score": 5})
    assert result["triage_score"] == 10
    assert "follow_score≥3" in result["short_reason"]


def test_follow_score_lt_3_no_points():
    result = compute_triage({"follow_score": 2})
    assert result["triage_score"] == 0


def test_movement_new_adds_10():
    result = compute_triage({}, movement_status="new")
    assert result["triage_score"] == 10
    assert "movement:new" in result["short_reason"]


def test_movement_recurring_no_points():
    result = compute_triage({}, movement_status="recurring")
    assert result["triage_score"] == 0


def test_registry_score_80_adds_15():
    result = compute_triage({}, registry_score=80)
    assert result["triage_score"] == 15
    assert "registry_score≥80" in result["short_reason"]


def test_registry_score_60_adds_10():
    result = compute_triage({}, registry_score=65)
    assert result["triage_score"] == 10
    assert "registry_score≥60" in result["short_reason"]


def test_registry_score_lt_60_no_points():
    result = compute_triage({}, registry_score=59)
    assert result["triage_score"] == 0


# ---------------------------------------------------------------------------
# compute_triage — additive & cap
# ---------------------------------------------------------------------------

def test_score_capped_at_100():
    device = {
        "alert_level": "critique",   # 60
        "watch_hit": True,            # 20
        "possible_suivi": True,       # 15
        "follow_score": 4,            # 10
    }
    case = {"status": "escalated"}   # 25
    result = compute_triage(
        device,
        case_record=case,
        movement_status="new",        # 10
        registry_score=85,            # 15
    )
    # raw = 60+20+25+15+10+10+15 = 155, capped at 100
    assert result["triage_score"] == 100
    assert result["triage_bucket"] == "critical"


def test_additive_partial_signals():
    # moyen(10) + watch_hit(20) + movement:new(10) = 40
    result = compute_triage(
        {"alert_level": "moyen", "watch_hit": True},
        movement_status="new",
    )
    assert result["triage_score"] == 40
    assert result["triage_bucket"] == "review"


# ---------------------------------------------------------------------------
# triage_device_list
# ---------------------------------------------------------------------------

def test_triage_device_list_empty():
    results = triage_device_list([])
    assert results == []


def test_triage_device_list_sorted_desc():
    devices = [
        {"address": "AA:BB:CC:DD:EE:01", "name": "A", "alert_level": "moyen"},
        {"address": "AA:BB:CC:DD:EE:02", "name": "B", "alert_level": "critique"},
    ]
    results = triage_device_list(devices)
    assert results[0]["triage_score"] >= results[1]["triage_score"]
    assert results[0]["address"] == "AA:BB:CC:DD:EE:02"


def test_triage_device_list_includes_name_and_address():
    devices = [{"address": "AA:BB:CC:DD:EE:FF", "name": "Phone"}]
    results = triage_device_list(devices)
    assert results[0]["address"] == "AA:BB:CC:DD:EE:FF"
    assert results[0]["name"] == "Phone"


def test_triage_device_list_uses_registry_scores():
    devices = [{"address": "AA:BB:CC:DD:EE:FF", "name": "X"}]
    results = triage_device_list(devices, registry_scores={"AA:BB:CC:DD:EE:FF": 85})
    assert results[0]["triage_score"] == 15  # registry_score≥80
    assert "registry_score≥80" in results[0]["short_reason"]


def test_triage_device_list_uses_case_record():
    devices = [{"address": "AA:BB:CC:DD:EE:FF", "name": "X"}]
    watch_cases = {"AA:BB:CC:DD:EE:FF": {"status": "watch"}}
    results = triage_device_list(devices, watch_cases=watch_cases)
    assert results[0]["triage_score"] == 15


def test_triage_device_list_movement_new_detected():
    devices = [{"address": "AA:BB:CC:DD:EE:FF", "name": "X"}]
    movement = {
        "new": [{"address": "AA:BB:CC:DD:EE:FF"}],
        "recurring": [],
        "disappeared": [],
        "score_changes": [],
        "counts": {},
    }
    results = triage_device_list(devices, movement=movement)
    assert results[0]["triage_score"] == 10
    assert "movement:new" in results[0]["short_reason"]


# ---------------------------------------------------------------------------
# Dashboard integration
# ---------------------------------------------------------------------------

def test_dashboard_renders_triage_panel(monkeypatch):
    import ble_radar.dashboard as db

    monkeypatch.setattr(db, "load_registry", lambda: {})
    monkeypatch.setattr(db, "load_last_scan", lambda: [])
    monkeypatch.setattr(db, "load_scan_history", lambda: [])
    monkeypatch.setattr(db, "load_watch_cases", lambda: {})

    html = db.render_dashboard_html(
        [{"address": "AA:BB:CC:DD:EE:FF", "name": "X", "alert_level": "critique"}],
        "2026-04-18T00:00:00",
    )
    assert "Operator Triage Priority" in html
    assert "CRITICAL" in html
    assert "AA:BB:CC:DD:EE:FF" in html


def test_dashboard_triage_panel_empty_devices(monkeypatch):
    import ble_radar.dashboard as db

    monkeypatch.setattr(db, "load_registry", lambda: {})
    monkeypatch.setattr(db, "load_last_scan", lambda: [])
    monkeypatch.setattr(db, "load_scan_history", lambda: [])
    monkeypatch.setattr(db, "load_watch_cases", lambda: {})

    html = db.render_dashboard_html([], "2026-04-18T00:00:00")
    assert "Operator Triage Priority" in html
    assert "Aucun appareil" in html


def test_render_triage_panel_overflow():
    from ble_radar.dashboard import render_triage_panel

    fake = [
        {"address": f"AA:BB:CC:DD:{i:02X}:FF", "name": f"D{i}",
         "triage_score": 100 - i, "triage_bucket": "critical", "short_reason": "x"}
        for i in range(20)
    ]
    html = render_triage_panel(fake)
    assert "… 5 de plus" in html
