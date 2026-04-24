from ble_radar.dashboard import render_omega_firmware_intel_panel


def test_render_empty_firmware_panel():
    html = render_omega_firmware_intel_panel([])
    assert "OMEGA Firmware Intel" in html
    assert "No firmware analysis loaded" in html


def test_render_firmware_report_panel():
    report = {
        "name": "tracker.bin",
        "path": "samples/firmware/tracker.bin",
        "size_bytes": 1234,
        "sha256": "a" * 64,
        "strings_count": 7,
        "risk": {
            "score": 55,
            "level": "MEDIUM",
            "hits": [
                {"marker": "password", "string": "admin_password=demo"},
                {"marker": "mqtt", "string": "mqtt://broker"},
            ],
        },
        "tool_hint": {"radare2": "r2 -AA samples/firmware/tracker.bin"},
    }

    html = render_omega_firmware_intel_panel([report])

    assert "tracker.bin" in html
    assert "MEDIUM" in html
    assert "55/100" in html
    assert "admin_password=demo" in html
    assert "r2 -AA samples/firmware/tracker.bin" in html
