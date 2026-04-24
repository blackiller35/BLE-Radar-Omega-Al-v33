from ble_radar.intel.ble_fingerprint import classify_ble_device


def test_classifies_logitech_mx_master_as_hid_active_device():
    result = classify_ble_device(
        {
            "name": "MX Master 3S",
            "vendor": "Logitech",
            "has_active_connection": True,
            "notification_rate": 25,
            "services": ["Human Interface Device"],
        }
    )

    assert result["category"] == "mouse_keyboard"
    assert "ACTIVE_DEVICE" in result["tags"]
    assert "HID_DEVICE" in result["tags"]
    assert "LOGITECH_DEVICE" in result["tags"]
    assert result["confidence"] >= 80


def test_classifies_passive_apple_broadcast_as_possible_airtag():
    result = classify_ble_device(
        {
            "name": "",
            "vendor": "Apple",
            "company_id": "0x004c",
            "has_active_connection": False,
            "notification_rate": 0,
        }
    )

    assert result["category"] == "possible_airtag"
    assert "APPLE_BLE" in result["tags"]
    assert "PASSIVE_BROADCAST" in result["tags"]


def test_classifies_talkative_unknown_active_ble_as_iot_or_sensor():
    result = classify_ble_device(
        {
            "name": "Unknown",
            "has_active_connection": True,
            "notification_rate": 15,
        }
    )

    assert result["category"] == "active_iot_or_sensor"
    assert "ACTIVE_DEVICE" in result["tags"]
    assert "TALKATIVE_BLE" in result["tags"]
