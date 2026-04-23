from ble_radar.intel.risk_tags import build_risk_tags, risk_level_from_tags


def test_high_persistent_randomized():
    device = {"address": "26:6a:46:e3:6c:56", "hits": 4252}

    tags = build_risk_tags(device)

    assert "PERSISTENT_DEVICE" in tags
    assert "HIGH_ACTIVITY" in tags
    assert "RANDOMIZED_BLE_ADDRESS" in tags
    assert "TRACKING_SUSPECT" in tags
    assert "PRIORITY_REVIEW" in tags

    level = risk_level_from_tags(tags)
    assert level == "high"


def test_medium_device():
    device = {"address": "b0:f2:f6:60:ca:48", "hits": 3312}

    tags = build_risk_tags(device)

    assert "PERSISTENT_DEVICE" in tags
    assert "HIGH_ACTIVITY" in tags

    level = risk_level_from_tags(tags)
    assert level == "medium"


def test_low_device():
    device = {"address": "4b:86:09:21:12:3e", "hits": 103}

    tags = build_risk_tags(device)

    level = risk_level_from_tags(tags)
    assert level == "low"
