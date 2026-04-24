from ble_radar.fusion import (
    correlate_ble_wifi,
    compute_fusion_risk,
    generate_operator_summary,
)


def test_correlate_ble_wifi_detects_same_oui_and_vendor():
    ble = [
        {
            "name": "Omega Sensor",
            "address": "AA:BB:CC:11:22:33",
            "vendor": "Nordic",
            "rssi": -44,
        }
    ]
    wifi = [
        {
            "ssid": "Omega Sensor AP",
            "bssid": "AA:BB:CC:44:55:66",
            "vendor": "Nordic",
            "rssi": -47,
        }
    ]

    result = correlate_ble_wifi(ble, wifi)

    assert len(result) == 1
    assert result[0]["match_score"] >= 80
    assert result[0]["risk"] == "high"
    assert "same OUI prefix" in result[0]["reasons"]


def test_correlate_ble_wifi_ignores_unrelated_devices():
    result = correlate_ble_wifi(
        [{"address": "AA:BB:CC:11:22:33", "vendor": "Nordic", "rssi": -44}],
        [{"bssid": "DD:EE:FF:44:55:66", "vendor": "Apple", "rssi": -80}],
    )

    assert result == []


def test_compute_fusion_risk_medium_for_partial_match():
    risk = compute_fusion_risk(
        50,
        {"rssi": -75},
        {"rssi": -72},
    )

    assert risk == "medium"


def test_generate_operator_summary_contains_risk_score_and_reasons():
    summary = generate_operator_summary(85, "high", ["same vendor"])

    assert "HIGH" in summary
    assert "85%" in summary
    assert "same vendor" in summary
