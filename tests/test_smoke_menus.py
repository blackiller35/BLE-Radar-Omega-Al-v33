import pytest

from ble_radar.snapshots import list_snapshots
from ble_radar.sentinel import build_sentinel_report
from ble_radar.oracle import build_oracle_report
from ble_radar.aegis import evaluate_aegis
from ble_radar.commander import build_commander_brief


@pytest.fixture
def sample_devices():
    return [
        {
            "name": "Tracker Alpha",
            "address": "AA:BB:CC:DD:EE:01",
            "vendor": "TestVendor",
            "profile": "tracker_probable",
            "alert_level": "elev\u00e9",
            "final_score": 78,
            "score": 78,
            "watch_hit": True,
            "possible_suivi": True,
            "persistent_nearby": True,
            "random_mac": False,
        },
        {
            "name": "Beacon Beta",
            "address": "AA:BB:CC:DD:EE:02",
            "vendor": "TestVendor",
            "profile": "general_ble",
            "alert_level": "faible",
            "final_score": 12,
            "score": 12,
            "watch_hit": False,
            "possible_suivi": False,
            "persistent_nearby": False,
            "random_mac": True,
        },
    ]


@pytest.fixture
def sample_history(sample_devices):
    return [
        {"devices": []},
        {"devices": sample_devices},
    ]


def test_snapshot_smoke_non_destructive_callable():
    snaps = list_snapshots()
    assert isinstance(snaps, list)


def test_sentinel_smoke_callable_without_traceback(sample_devices, sample_history):
    previous_devices = sample_history[-2].get("devices", []) if len(sample_history) >= 2 else []
    report = build_sentinel_report(sample_devices, previous_devices, sample_history)

    assert isinstance(report, dict)
    assert "threat_state" in report
    assert "watch_hits" in report


def test_oracle_smoke_callable_without_traceback(sample_devices, sample_history):
    report = build_oracle_report(sample_devices, sample_history)

    assert isinstance(report, dict)
    assert "outlook" in report
    assert "targets" in report


def test_aegis_smoke_callable_without_traceback(sample_devices, sample_history):
    result = evaluate_aegis(sample_devices, sample_history)

    assert isinstance(result, dict)
    assert "enabled" in result
    assert "incidents" in result


def test_commander_smoke_callable_without_traceback(sample_devices, sample_history):
    brief = build_commander_brief(sample_devices, sample_history)

    assert isinstance(brief, dict)
    assert "next_action" in brief
    assert "threat_state" in brief


@pytest.mark.parametrize(
    "call_center",
    [
        lambda devices, history: list_snapshots(),
        lambda devices, history: build_sentinel_report(
            devices,
            history[-2].get("devices", []) if len(history) >= 2 else [],
            history,
        ),
        lambda devices, history: build_oracle_report(devices, history),
        lambda devices, history: evaluate_aegis(devices, history),
        lambda devices, history: build_commander_brief(devices, history),
    ],
)
def test_all_target_centers_smoke_no_traceback(call_center, sample_devices, sample_history):
    result = call_center(sample_devices, sample_history)
    assert result is not None
