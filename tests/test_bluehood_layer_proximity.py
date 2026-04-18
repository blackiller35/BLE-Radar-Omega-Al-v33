from ble_radar.analysis.proximity import proximity_zone


def test_proximity_zone():
    assert proximity_zone(-50) == "immediate"
    assert proximity_zone(-63) == "near"
    assert proximity_zone(-75) == "mid"
    assert proximity_zone(-90) == "far"
