from ble_radar.linking.firmware_device_link import (
    firmware_matches_device,
    link_firmware_to_devices,
)


def test_firmware_matches_device_by_name():
    device = {"name": "TrackerX", "vendor": "Unknown", "address": "AA:BB:CC:DD:EE:FF"}
    report = {
        "name": "trackerx_firmware.bin",
        "interesting_strings": ["debug", "admin_password"],
    }

    assert firmware_matches_device(device, report)


def test_link_firmware_to_devices_adds_tags_and_score():
    devices = [
        {"name": "TrackerX", "vendor": "Unknown", "address": "AA:BB:CC:DD:EE:FF", "tags": []}
    ]
    reports = [
        {
            "name": "trackerx.bin",
            "path": "samples/firmware/trackerx.bin",
            "interesting_strings": ["TrackerX", "mqtt://broker", "admin_password=demo"],
            "risk": {
                "score": 72,
                "level": "HIGH",
                "hits": [
                    {"marker": "password", "string": "admin_password=demo"},
                    {"marker": "mqtt", "string": "mqtt://broker"},
                ],
            },
        }
    ]

    linked = link_firmware_to_devices(devices, reports)

    assert linked[0]["firmware_risk_score"] == 72
    assert linked[0]["firmware_links"][0]["firmware"] == "trackerx.bin"
    assert "FIRMWARE_LINKED" in linked[0]["tags"]
    assert "FIRMWARE_HIGH_RISK" in linked[0]["tags"]


def test_link_firmware_to_devices_leaves_unmatched_device_clean():
    devices = [{"name": "Keyboard", "vendor": "Logitech", "address": "11:22:33:44:55:66"}]
    reports = [{"name": "tracker.bin", "interesting_strings": ["unrelated"], "risk": {"score": 80}}]

    linked = link_firmware_to_devices(devices, reports)

    assert "firmware_links" not in linked[0]
    assert "firmware_risk_score" not in linked[0]
