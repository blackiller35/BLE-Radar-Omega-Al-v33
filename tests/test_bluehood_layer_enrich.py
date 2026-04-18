from ble_radar.bluehood_layer import enrich_devices_for_session


def test_enrich_devices_for_session():
    devices = [
        {"address": "AA:BB", "name": "Tile Tracker", "vendor": "Tile", "rssi": -58},
        {"address": "CC:DD", "name": "Beacon", "vendor": "Acme", "rssi": -77},
    ]
    result = enrich_devices_for_session(devices, {}, "sess-1", "2026-04-17T21:00:00")
    assert len(result["devices_enriched"]) == 2
    assert len(result["watch_hits"]) >= 1
