from datetime import datetime

from ble_radar.history.device_scoring import compute_device_score

# Fixed reference point used throughout all tests for determinism.
NOW = datetime(2026, 4, 18, 12, 0, 0)


def test_zero_score_for_empty_record():
    assert compute_device_score({}, None, _now=NOW) == 0
    assert compute_device_score({}, {}, _now=NOW) == 0


def test_seen_count_contributes_to_score():
    rec = {"seen_count": 5, "session_count": 0}
    assert compute_device_score({}, rec, _now=NOW) == 10   # 5*2 = 10


def test_seen_count_capped_at_20():
    rec = {"seen_count": 100, "session_count": 0}
    assert compute_device_score({}, rec, _now=NOW) == 40   # min(100,20)*2 = 40


def test_session_count_contributes_to_score():
    rec = {"seen_count": 0, "session_count": 3}
    assert compute_device_score({}, rec, _now=NOW) == 12   # 3*4 = 12


def test_session_count_capped_at_10():
    rec = {"seen_count": 0, "session_count": 50}
    assert compute_device_score({}, rec, _now=NOW) == 40   # min(50,10)*4 = 40


def test_recency_within_24h_adds_20():
    last_seen = datetime(2026, 4, 18, 6, 0, 0).strftime("%Y-%m-%d %H:%M:%S")  # 6h before NOW
    rec = {"seen_count": 0, "session_count": 0, "last_seen": last_seen}
    assert compute_device_score({}, rec, _now=NOW) == 20


def test_recency_within_7_days_adds_10():
    last_seen = datetime(2026, 4, 15, 12, 0, 0).strftime("%Y-%m-%d %H:%M:%S")  # 3 days before NOW
    rec = {"seen_count": 0, "session_count": 0, "last_seen": last_seen}
    assert compute_device_score({}, rec, _now=NOW) == 10


def test_recency_older_than_7_days_adds_0():
    last_seen = datetime(2026, 4, 1, 12, 0, 0).strftime("%Y-%m-%d %H:%M:%S")  # 17 days before NOW
    rec = {"seen_count": 0, "session_count": 0, "last_seen": last_seen}
    assert compute_device_score({}, rec, _now=NOW) == 0


def test_score_combines_all_components():
    last_seen = datetime(2026, 4, 18, 11, 0, 0).strftime("%Y-%m-%d %H:%M:%S")  # 1h before NOW
    rec = {"seen_count": 10, "session_count": 5, "last_seen": last_seen}
    # seen=20, session=20, recency=20 → 60
    assert compute_device_score({}, rec, _now=NOW) == 60


def test_score_capped_at_100():
    last_seen = datetime(2026, 4, 18, 11, 59, 0).strftime("%Y-%m-%d %H:%M:%S")
    rec = {"seen_count": 9999, "session_count": 9999, "last_seen": last_seen}
    assert compute_device_score({}, rec, _now=NOW) == 100


def test_invalid_last_seen_does_not_raise():
    rec = {"seen_count": 2, "session_count": 1, "last_seen": "not-a-date"}
    score = compute_device_score({}, rec, _now=NOW)
    # seen=4, session=4, recency=0 → 8
    assert score == 8


def test_device_arg_is_not_used_in_score():
    """Score is purely registry-driven; device dict content must not affect result."""
    rec = {"seen_count": 4, "session_count": 2}
    score_a = compute_device_score({"final_score": 999, "alert_level": "critique"}, rec, _now=NOW)
    score_b = compute_device_score({}, rec, _now=NOW)
    assert score_a == score_b
