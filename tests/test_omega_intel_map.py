from ble_radar.intel.omega_intel_map import build_omega_intel_map, build_omega_intel_maps


def test_tracking_suspect_high_risk():
    ctx = build_omega_intel_map({
        "name": "Unknown",
        "address": "AA:BB:CC:DD:EE:FF",
        "vendor": "Unknown",
        "rssi": -45,
        "hits": 8,
        "risk_tags": ["RANDOMIZED_BLE_ADDRESS"],
    })

    assert ctx["risk"]["level"] == "high"
    assert "TRACKING_SUSPECT" in ctx["risk"]["tags"]
    assert "PERSISTENT_DEVICE" in ctx["risk"]["tags"]
    assert ctx["signal"]["bucket"] == "very_close"


def test_persistent_unknown_is_medium():
    ctx = build_omega_intel_map({
        "name": "",
        "vendor": "Unknown",
        "rssi": -72,
        "hits": 6,
        "risk_tags": [],
    })

    assert ctx["risk"]["level"] == "medium"
    assert "WEAK_DEVICE_PROFILE" in ctx["risk"]["tags"]
    assert "UNTRUSTED_IOT" in ctx["risk"]["tags"]


def test_build_many_maps():
    rows = build_omega_intel_maps([{"name": "Phone"}, {"name": "Beacon"}])
    assert len(rows) == 2
