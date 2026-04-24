from ble_radar.intel.threat_context import build_threat_context


def test_tracking_context_is_high():
    ctx = build_threat_context(["PERSISTENT_DEVICE", "RANDOMIZED_BLE_ADDRESS", "TRACKING_SUSPECT"])
    assert ctx["level"] == "high"
    assert "randomized" in ctx["summary"].lower()
    assert "review" in ctx["recommendation"].lower()


def test_persistent_context_is_medium():
    ctx = build_threat_context(["PERSISTENT_DEVICE", "HIGH_ACTIVITY"])
    assert ctx["level"] == "medium"
    assert "persistent" in ctx["summary"].lower()


def test_empty_context_is_low():
    ctx = build_threat_context([])
    assert ctx["level"] == "low"
    assert "no immediate" in ctx["summary"].lower()
