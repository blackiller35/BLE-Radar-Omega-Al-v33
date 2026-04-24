from wifi_radar.analyzer import classify_wifi_network, analyze_wifi_networks


def test_classify_hidden_close_network():
    result = classify_wifi_network({
        "ssid": "Hidden",
        "security": "WPA2",
        "signal": 95,
    })

    assert result["risk_level"] in {"medium", "high"}
    assert "HIDDEN_SSID" in result["risk_tags"]
    assert "VERY_CLOSE_SIGNAL" in result["risk_tags"]


def test_classify_open_network_high_risk():
    result = classify_wifi_network({
        "ssid": "Cafe",
        "security": "OPEN",
        "signal": 70,
    })

    assert result["risk_score"] >= 40
    assert "OPEN_NETWORK" in result["risk_tags"]


def test_analyze_wifi_networks_returns_list():
    result = analyze_wifi_networks([
        {"ssid": "Test", "security": "WPA2", "signal": 50}
    ])

    assert len(result) == 1
    assert "risk_score" in result[0]
