from ble_radar.intel.threat_context import build_threat_context, build_threat_contexts


def test_threat_context_detects_high_activity_persistent_device():
    ctx = build_threat_context(
        {
            "name": "Unknown BLE",
            "address": "AA:BB",
            "hits": 1200,
            "risk_tags": ["PERSISTENT_DEVICE", "HIGH_ACTIVITY"],
        }
    )

    assert ctx["severity"] == "high"
    assert "activité BLE élevée détectée" in ctx["reasons"]
    assert "surveiller la réapparition sur plusieurs scans" in ctx["recommended_actions"]


def test_threat_context_detects_tracker_like_profile():
    ctx = build_threat_context(
        {
            "name": "Tile Tracker",
            "address": "CC:DD",
            "vendor": "Tile",
            "rssi": -50,
            "risk_tags": [],
        }
    )

    assert ctx["severity"] == "medium"
    assert "profil compatible avec balise ou tracker BLE" in ctx["reasons"]
    assert "signal proche ou fort" in ctx["reasons"]


def test_build_threat_contexts_handles_empty_list():
    assert build_threat_contexts([]) == []
