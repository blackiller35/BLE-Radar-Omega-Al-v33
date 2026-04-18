from ble_radar.dashboard import render_bluehood_summary

def test_render_bluehood_summary_has_title():
    devices = [
        {"address": "AA:BB", "name": "Tile Tracker", "vendor": "Tile", "rssi": -58},
        {"address": "CC:DD", "name": "Beacon", "vendor": "Acme", "rssi": -77},
    ]
    html = render_bluehood_summary(devices)
    assert "Bluehood Summary" in html
    assert "Watch hits" in html
