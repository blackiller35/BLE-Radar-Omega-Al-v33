from pathlib import Path

from wifi_radar.history import load_wifi_history, summarize_wifi_history, update_wifi_history


def test_load_missing_wifi_history_returns_empty(tmp_path: Path):
    data = load_wifi_history(tmp_path / "missing.json")
    assert data == {"networks": {}}


def test_update_wifi_history_tracks_seen_count(tmp_path: Path):
    path = tmp_path / "wifi_history.json"

    networks = [
        {
            "ssid": "TestNet",
            "bssid": "aa:bb:cc:dd:ee:ff",
            "signal": 50,
            "risk_level": "low",
            "risk_tags": ["WPA2"],
        }
    ]

    update_wifi_history(networks, path)
    history = update_wifi_history(networks, path)

    item = history["networks"]["AA:BB:CC:DD:EE:FF"]
    assert item["seen_count"] == 2
    assert item["first_seen"]
    assert item["last_seen"]
    assert item["best_signal"] == 50


def test_summarize_wifi_history_counts_categories():
    history = {
        "networks": {
            "AA": {
                "ssid": "Hidden",
                "risk_level": "medium",
                "risk_tags": ["VERY_CLOSE_SIGNAL"],
            },
            "BB": {
                "ssid": "Home",
                "risk_level": "low",
                "risk_tags": [],
            },
        }
    }

    summary = summarize_wifi_history(history)

    assert summary["total_known_networks"] == 2
    assert summary["hidden_networks"] == 1
    assert summary["medium_or_high_risk"] == 1
    assert summary["very_close"] == 1
