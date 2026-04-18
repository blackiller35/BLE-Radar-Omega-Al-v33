from ble_radar.history.device_history import new_device_record, update_device_record


def test_device_history_create_and_update():
    base = {"address": "AA:BB", "name": "Tag", "vendor": "Acme", "rssi": -60}
    record = new_device_record(base, "sess-1", "2026-04-17T21:00:00")
    assert record["times_seen"] == 1
    assert record["first_seen"] == "2026-04-17T21:00:00"

    updated = update_device_record(record, {"address": "AA:BB", "name": "Tag2", "vendor": "Acme", "rssi": -55}, "sess-2", "2026-04-17T22:00:00")
    assert updated["times_seen"] == 2
    assert updated["last_seen"] == "2026-04-17T22:00:00"
    assert "Tag2" in updated["aliases"]
