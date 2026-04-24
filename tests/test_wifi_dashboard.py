from pathlib import Path

from wifi_radar.dashboard import render_wifi_dashboard, save_wifi_dashboard


def test_render_wifi_dashboard_contains_summary_and_network():
    history = {
        "networks": {
            "AA:BB:CC:DD:EE:FF": {
                "ssid": "Hidden",
                "bssid": "AA:BB:CC:DD:EE:FF",
                "signal": 95,
                "best_signal": 99,
                "channel": "6",
                "seen_count": 3,
                "security": "WPA2",
                "risk_level": "medium",
                "risk_score": 30,
                "risk_tags": ["HIDDEN_SSID", "VERY_CLOSE_SIGNAL"],
                "first_seen": "2026-01-01T00:00:00",
                "last_seen": "2026-01-01T00:01:00",
            }
        }
    }

    html = render_wifi_dashboard(history)

    assert "OMEGA WiFi Dashboard" in html
    assert "AA:BB:CC:DD:EE:FF" in html
    assert "HIDDEN_SSID" in html
    assert "Medium / High risk" in html


def test_save_wifi_dashboard_creates_html(tmp_path: Path):
    history_path = tmp_path / "wifi_history.json"
    history_path.write_text('{"networks": {}}', encoding="utf-8")

    path = save_wifi_dashboard(history_path=history_path, output_dir=tmp_path)

    assert path.exists()
    assert path.suffix == ".html"
    assert "OMEGA WiFi Dashboard" in path.read_text(encoding="utf-8")
