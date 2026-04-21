from ble_radar import dashboard


def test_recurring_device_summary_appears():
    device = {"name": "Beacon-A", "address": "AA:BB", "rssi": -67}
    registry_row = {"seen_count": 12}
    observations = [
        {"scan_pos": 0, "name": "Beacon-A", "rssi": -68},
        {"scan_pos": 1, "name": "Beacon-A", "rssi": -66},
        {"scan_pos": 2, "name": "Beacon-A", "rssi": -67},
        {"scan_pos": 3, "name": "Beacon-A", "rssi": -65},
    ]

    summary = dashboard.build_compact_device_behavior_summary(
        device, registry_row=registry_row, observations=observations
    )

    assert "Likely recurring device" in summary


def test_name_change_summary_appears_when_applicable():
    device = {"name": "Tracker-New", "address": "AA:CC", "rssi": -72}
    registry_row = {"seen_count": 4}
    observations = [
        {"scan_pos": 0, "name": "Tracker-Old", "rssi": -73},
        {"scan_pos": 1, "name": "Tracker-New", "rssi": -72},
    ]

    summary = dashboard.build_compact_device_behavior_summary(
        device, registry_row=registry_row, observations=observations
    )

    assert "Name changed recently" in summary


def test_unstable_signal_summary_appears_when_applicable():
    device = {"name": "TV", "address": "AA:DD", "rssi": -92}
    registry_row = {"seen_count": 5}
    observations = [
        {"scan_pos": 0, "name": "TV", "rssi": -55},
        {"scan_pos": 1, "name": "TV", "rssi": -86},
        {"scan_pos": 2, "name": "TV", "rssi": -74},
    ]

    summary = dashboard.build_compact_device_behavior_summary(
        device, registry_row=registry_row, observations=observations
    )

    assert "Signal pattern unstable" in summary


def test_empty_minimal_history_case_remains_clean_and_safe():
    device = {"name": "Inconnu", "address": "AA:EE", "rssi": -80}

    summary = dashboard.build_compact_device_behavior_summary(
        device, registry_row={}, observations=[]
    )

    assert summary == ""
