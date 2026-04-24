from ble_radar.triggers.live_firmware_trigger import (
    build_live_firmware_trigger,
    build_live_firmware_triggers,
    should_trigger_firmware_analysis,
)


def test_unknown_device_triggers_firmware_analysis():
    device = {"name": "Unknown", "vendor": "Unknown", "address": "AA:BB:CC:DD:EE:FF"}
    assert should_trigger_firmware_analysis(device)


def test_high_score_triggers_firmware_analysis():
    device = {"name": "Beacon", "vendor": "Nordic", "score": 75, "rssi": -70}
    trigger = build_live_firmware_trigger(device)
    assert trigger["triggered"] is True
    assert "high BLE risk score" in trigger["reasons"]


def test_suspicious_tag_triggers_firmware_analysis():
    device = {"name": "IoT", "vendor": "Unknown", "tags": ["UNTRUSTED_IOT"]}
    trigger = build_live_firmware_trigger(device)
    assert trigger["triggered"] is True
    assert any("UNTRUSTED_IOT" in reason for reason in trigger["reasons"])


def test_baseline_device_does_not_trigger():
    device = {"name": "Keyboard", "vendor": "Logitech", "score": 10, "rssi": -80, "tags": []}
    trigger = build_live_firmware_trigger(device)
    assert trigger["triggered"] is False
    assert "baseline BLE behavior" in trigger["reasons"]


def test_build_live_firmware_triggers_batch():
    devices = [
        {"name": "Unknown", "vendor": "Unknown"},
        {"name": "Keyboard", "vendor": "Logitech", "score": 10, "rssi": -80},
    ]
    triggers = build_live_firmware_triggers(devices)
    assert len(triggers) == 2
    assert triggers[0]["triggered"] is True
    assert triggers[1]["triggered"] is False
