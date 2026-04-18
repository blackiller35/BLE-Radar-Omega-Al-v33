from ble_radar.dashboard import render_bluehood_summary

def test_render_bluehood_summary_contains_watch_hit_details():
    devices = [
        {"address": "AA:BB", "name": "Tile Tracker", "vendor": "Tile", "rssi": -58},
        {"address": "CC:DD", "name": "Beacon", "vendor": "Acme", "rssi": -77},
    ]
    html = render_bluehood_summary(devices)
    assert "Watch hits details" in html
    assert "Tile Tracker" in html
