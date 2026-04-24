from pathlib import Path

from wifi_radar.scanner import save_wifi_scan


def test_save_wifi_scan_creates_json(tmp_path: Path):
    networks = [
        {
            "ssid": "TestNet",
            "bssid": "AA:BB:CC:DD:EE:FF",
            "channel": "6",
            "frequency": "2437 MHz",
            "signal": 80,
            "security": "WPA2",
            "seen_at": "2026-01-01T00:00:00",
        }
    ]

    path = save_wifi_scan(networks, tmp_path)

    assert path.exists()
    assert "TestNet" in path.read_text(encoding="utf-8")
