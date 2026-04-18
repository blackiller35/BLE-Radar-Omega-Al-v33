from ble_radar.dashboard import render_dashboard_html

def test_dashboard_html_contains_bluehood_summary():
    devices = [
        {"address": "AA:BB", "name": "Tile Tracker", "vendor": "Tile", "rssi": -58},
        {"address": "CC:DD", "name": "Beacon", "vendor": "Acme", "rssi": -77},
    ]
    html = render_dashboard_html(devices, "2026-04-17_23-10-00")
    assert "Bluehood Summary" in html
