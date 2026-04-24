from ble_radar.intel.omega_core import (
    build_omega_intel,
    build_omega_intel_batch,
    summarize_omega_intel,
)


def test_omega_core_builds_high_context_without_required_live_alert():
    row = build_omega_intel(
        {
            "name": "Unknown BLE",
            "address": "AA:BB",
            "vendor": "Unknown",
            "hits": 1800,
        }
    )

    assert row["threat_level"] == "high"
    assert row["confidence"] >= 0.9
    assert row["risk_tags"]
    assert row["has_live_alert"] in {True, False}


def test_omega_core_detects_tracker_type():
    row = build_omega_intel(
        {
            "name": "Tile Tracker",
            "address": "CC:DD",
            "vendor": "Tile",
            "hits": 20,
            "rssi": -50,
        }
    )

    assert row["device_type"] == "tracking_or_beacon"
    assert row["threat_level"] in {"medium", "high"}
    assert row["recommended_actions"]


def test_omega_core_batch_summary():
    rows = build_omega_intel_batch(
        [
            {"name": "Unknown BLE", "address": "AA:BB", "hits": 1800},
            {"name": "Keyboard", "address": "CC:DD", "hits": 1},
        ]
    )
    summary = summarize_omega_intel(rows)

    assert summary["total"] == 2
    assert summary["high"] >= 1
    assert summary["live_alerts"] >= 0
