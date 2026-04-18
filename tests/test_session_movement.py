"""Focused tests for ble_radar/session/session_movement.py (step 5)."""
from datetime import datetime

from ble_radar.session.session_movement import build_session_movement

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PREV = [
    {"address": "AA:BB", "name": "Alpha"},
    {"address": "CC:DD", "name": "Beta"},
]

CURR = [
    {"address": "AA:BB", "name": "Alpha"},   # recurring
    {"address": "EE:FF", "name": "Gamma"},   # new
    # CC:DD disappeared
]


# ---------------------------------------------------------------------------
# Classification tests
# ---------------------------------------------------------------------------

def test_new_device_detected():
    mv = build_session_movement(CURR, PREV)
    addrs = [d["address"].upper() for d in mv["new"]]
    assert "EE:FF" in addrs


def test_disappeared_device_detected():
    mv = build_session_movement(CURR, PREV)
    addrs = [d["address"].upper() for d in mv["disappeared"]]
    assert "CC:DD" in addrs


def test_recurring_device_detected():
    mv = build_session_movement(CURR, PREV)
    addrs = [d["address"].upper() for d in mv["recurring"]]
    assert "AA:BB" in addrs


def test_counts_are_correct():
    mv = build_session_movement(CURR, PREV)
    c = mv["counts"]
    assert c["new"] == 1
    assert c["disappeared"] == 1
    assert c["recurring"] == 1
    assert c["total_current"] == 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_previous_all_are_new():
    mv = build_session_movement(CURR, [])
    assert mv["counts"]["new"] == 2
    assert mv["counts"]["disappeared"] == 0
    assert mv["counts"]["recurring"] == 0


def test_empty_current_all_disappeared():
    mv = build_session_movement([], PREV)
    assert mv["counts"]["new"] == 0
    assert mv["counts"]["disappeared"] == 2
    assert mv["counts"]["recurring"] == 0


def test_both_empty_no_movement():
    mv = build_session_movement([], [])
    assert mv["counts"] == {"new": 0, "disappeared": 0, "recurring": 0, "total_current": 0}


def test_devices_without_address_are_ignored():
    curr = [{"name": "NoAddr"}, {"address": "", "name": "EmptyAddr"}]
    mv = build_session_movement(curr, [])
    assert mv["counts"]["new"] == 0
    assert mv["counts"]["total_current"] == 0


# ---------------------------------------------------------------------------
# Score change tests
# ---------------------------------------------------------------------------

def test_score_change_present_when_registry_has_data():
    registry = {
        "AA:BB": {
            "address": "AA:BB",
            "seen_count": 5,
            "session_count": 2,
            "last_seen": "2026-04-18 11:00:00",
        }
    }
    mv = build_session_movement(CURR, PREV, registry=registry)
    # seen_count=5 means prev_score used seen_count=4; delta should be positive
    changes = {sc["address"]: sc for sc in mv["score_changes"]}
    assert "AA:BB" in changes
    assert changes["AA:BB"]["curr_score"] > changes["AA:BB"]["prev_score"]
    assert changes["AA:BB"]["delta"] > 0


def test_no_score_change_when_registry_empty():
    mv = build_session_movement(CURR, PREV, registry={})
    # With empty registry both scores are 0 → delta is 0 → no entry
    assert mv["score_changes"] == []


def test_score_changes_sorted_by_abs_delta_descending():
    registry = {
        "AA:BB": {"seen_count": 20, "session_count": 10, "last_seen": "2026-04-18 11:00:00"},
        "CC:DD": {"seen_count": 2, "session_count": 1, "last_seen": "2026-04-18 11:00:00"},
    }
    curr = [{"address": "AA:BB", "name": "A"}, {"address": "CC:DD", "name": "B"}]
    prev = [{"address": "AA:BB", "name": "A"}, {"address": "CC:DD", "name": "B"}]
    mv = build_session_movement(curr, prev, registry=registry)
    if len(mv["score_changes"]) >= 2:
        assert abs(mv["score_changes"][0]["delta"]) >= abs(mv["score_changes"][1]["delta"])


# ---------------------------------------------------------------------------
# Dashboard integration test
# ---------------------------------------------------------------------------

def test_dashboard_html_contains_session_movement_panel(monkeypatch):
    from ble_radar import dashboard

    monkeypatch.setattr(dashboard, "load_scan_history", lambda: [])
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda d: [("Vendor", 1)])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda d: [])
    monkeypatch.setattr(dashboard, "load_registry", lambda: {})
    monkeypatch.setattr(dashboard, "load_last_scan", lambda: [])

    devices = [{"address": "AA:BB", "name": "Alpha", "vendor": "Vendor", "rssi": -50}]
    html = dashboard.render_dashboard_html(devices, "2026-04-18_12-00-00")

    assert "Session movement summary" in html
    assert "Nouveaux appareils" in html
    assert "Appareils disparus" in html
    assert "Appareils récurrents" in html
