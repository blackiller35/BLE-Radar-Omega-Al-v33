from wifi_radar.omega_wifi import run_wifi_omega_pipeline


def test_run_wifi_omega_pipeline_with_mocks(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "wifi_radar.omega_wifi.scan_wifi_nmcli",
        lambda: [
            {
                "ssid": "Hidden",
                "bssid": "AA:BB:CC:DD:EE:FF",
                "channel": "6",
                "frequency": "2437 MHz",
                "signal": 95,
                "security": "WPA2",
                "seen_at": "2026-01-01T00:00:00",
            }
        ],
    )

    monkeypatch.setattr(
        "wifi_radar.omega_wifi.save_wifi_scan",
        lambda networks: tmp_path / "scan.json",
    )

    monkeypatch.setattr(
        "wifi_radar.omega_wifi.save_wifi_dashboard",
        lambda: tmp_path / "dashboard.html",
    )

    result = run_wifi_omega_pipeline()

    assert len(result["networks"]) == 1
    assert result["summary"]["hidden_networks"] >= 1
    assert result["scan_path"].endswith("scan.json")
    assert result["dashboard_path"].endswith("dashboard.html")
