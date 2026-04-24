from ble_radar.dashboard import render_omega_live_firmware_alert_panel


def test_render_empty_live_firmware_alert_panel():
    html = render_omega_live_firmware_alert_panel([])
    assert "OMEGA Live Firmware Alerts" in html
    assert "No active firmware alerts" in html


def test_render_only_triggered_live_firmware_alerts():
    triggers = [
        {
            "triggered": True,
            "device": {
                "name": "Unknown BLE",
                "address": "AA:BB:CC:DD:EE:FF",
                "vendor": "Unknown",
            },
            "recommended_action": "Run local firmware reverse analysis if a firmware image is available.",
            "reasons": ["unknown device identity/vendor", "close-proximity signal"],
        },
        {
            "triggered": False,
            "device": {"name": "Keyboard", "address": "11:22:33:44:55:66", "vendor": "Logitech"},
            "recommended_action": "No firmware action required; continue baseline monitoring.",
            "reasons": ["baseline BLE behavior"],
        },
    ]

    html = render_omega_live_firmware_alert_panel(triggers)

    assert "Unknown BLE" in html
    assert "AA:BB:CC:DD:EE:FF" in html
    assert "unknown device identity/vendor" in html
    assert "close-proximity signal" in html
    assert "Keyboard" not in html
