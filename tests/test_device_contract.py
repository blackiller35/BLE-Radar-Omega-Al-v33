from ble_radar import device_contract


def test_required_device_keys_contains_expected_fields():
    keys = set(device_contract.REQUIRED_DEVICE_KEYS)

    assert "name" in keys
    assert "address" in keys
    assert "vendor" in keys
    assert "risk_score" in keys
    assert "follow_score" in keys
    assert "confidence_score" in keys
    assert "final_score" in keys
    assert "reason_short" in keys
    assert "flags" in keys


def test_normalize_device_fills_defaults():
    item = device_contract.normalize_device({"name": "Beacon-One", "address": "AA:BB"})

    assert item["name"] == "Beacon-One"
    assert item["address"] == "AA:BB"
    assert item["vendor"] == "Unknown"
    assert item["profile"] == "general_ble"
    assert item["reason_short"] == "normal"
    assert item["flags"] == []


def test_normalize_device_keeps_existing_values():
    item = device_contract.normalize_device(
        {
            "name": "Tracker-Two",
            "vendor": "TrackCorp",
            "risk_score": 17,
            "follow_score": 9,
            "confidence_score": 33,
            "final_score": 48,
            "reason_short": "tracker",
            "flags": ["follow", "watch"],
        }
    )

    assert item["vendor"] == "TrackCorp"
    assert item["risk_score"] == 17
    assert item["follow_score"] == 9
    assert item["confidence_score"] == 33
    assert item["final_score"] == 48
    assert item["reason_short"] == "tracker"
    assert item["flags"] == ["follow", "watch"]


def test_normalize_devices_returns_same_count():
    items = device_contract.normalize_devices([{"name": "A"}, {"name": "B"}])

    assert len(items) == 2
    assert items[0]["name"] == "A"
    assert items[1]["name"] == "B"


def test_score_breakdown_returns_int_scores():
    scores = device_contract.score_breakdown(
        {
            "risk_score": 11,
            "follow_score": 7,
            "confidence_score": 29,
            "final_score": 41,
        }
    )

    assert scores == {
        "risk_score": 11,
        "follow_score": 7,
        "confidence_score": 29,
        "final_score": 41,
    }


def test_explain_device_returns_summary():
    info = device_contract.explain_device(
        {
            "name": "Beacon-One",
            "address": "AA:BB:CC:DD:EE:01",
            "alert_level": "moyen",
            "risk_score": 12,
            "follow_score": 4,
            "confidence_score": 21,
            "final_score": 37,
            "reason_short": "watch_hit",
            "flags": ["watch"],
        }
    )

    assert info["name"] == "Beacon-One"
    assert info["address"] == "AA:BB:CC:DD:EE:01"
    assert info["alert_level"] == "moyen"
    assert info["reason_short"] == "watch_hit"
    assert info["flags"] == ["watch"]
    assert info["scores"]["final_score"] == 37
    assert "risk=12" in info["summary"]
    assert "follow=4" in info["summary"]
    assert "confidence=21" in info["summary"]
    assert "final=37" in info["summary"]
    assert "reason=watch_hit" in info["summary"]
