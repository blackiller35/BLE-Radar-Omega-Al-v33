from ble_radar import dashboard


def test_recurring_device_summary_appears():
    device = {"name": "Beacon-A", "address": "AA:BB", "rssi": -67}
    registry_row = {"seen_count": 12}
    observations = [
        {"scan_pos": 0, "name": "Beacon-A", "rssi": -68},
        {"scan_pos": 1, "name": "Beacon-A", "rssi": -66},
        {"scan_pos": 2, "name": "Beacon-A", "rssi": -67},
        {"scan_pos": 3, "name": "Beacon-A", "rssi": -65},
    ]

    summary = dashboard.build_compact_device_behavior_summary(
        device, registry_row=registry_row, observations=observations
    )

    assert "Likely recurring device" in summary


def test_name_change_summary_appears_when_applicable():
    device = {"name": "Tracker-New", "address": "AA:CC", "rssi": -72}
    registry_row = {"seen_count": 4}
    observations = [
        {"scan_pos": 0, "name": "Tracker-Old", "rssi": -73},
        {"scan_pos": 1, "name": "Tracker-New", "rssi": -72},
    ]

    summary = dashboard.build_compact_device_behavior_summary(
        device, registry_row=registry_row, observations=observations
    )

    assert "Name changed recently" in summary


def test_unstable_signal_summary_appears_when_applicable():
    device = {"name": "TV", "address": "AA:DD", "rssi": -92}
    registry_row = {"seen_count": 5}
    observations = [
        {"scan_pos": 0, "name": "TV", "rssi": -55},
        {"scan_pos": 1, "name": "TV", "rssi": -86},
        {"scan_pos": 2, "name": "TV", "rssi": -74},
    ]

    summary = dashboard.build_compact_device_behavior_summary(
        device, registry_row=registry_row, observations=observations
    )

    assert "Signal pattern unstable" in summary


def test_empty_minimal_history_case_remains_clean_and_safe():
    device = {"name": "Inconnu", "address": "AA:EE", "rssi": -80}

    summary = dashboard.build_compact_device_behavior_summary(
        device, registry_row={}, observations=[]
    )

    assert summary == ""


def test_device_interest_score_calculation_correctness():
    device = {"name": "Tracker-New", "address": "AA:FF", "rssi": -90}
    registry_row = {"seen_count": 10}
    observations = [
        {"scan_pos": 0, "name": "Tracker-Old", "rssi": -55},
        {"scan_pos": 4, "name": "Tracker-New", "rssi": -86},
    ]

    result = dashboard.compute_device_interest_score(
        device, registry_row=registry_row, observations=observations
    )

    assert result["score"] == 6
    assert result["label"] == "suspicious"


def test_device_interest_score_label_mapping():
    normal = dashboard.compute_device_interest_score(
        {"name": "Inconnu", "address": "AA:11", "rssi": -80},
        registry_row={"seen_count": 0},
        observations=[],
    )
    interesting = dashboard.compute_device_interest_score(
        {"name": "Beacon", "address": "AA:22", "rssi": -75},
        registry_row={"seen_count": 8},
        observations=[],
    )
    suspicious = dashboard.compute_device_interest_score(
        {"name": "Beacon-New", "address": "AA:33", "rssi": -92},
        registry_row={"seen_count": 8},
        observations=[
            {"scan_pos": 0, "name": "Beacon-Old", "rssi": -55},
            {"scan_pos": 1, "name": "Beacon-New", "rssi": -84},
        ],
    )

    assert normal["label"] == "normal"
    assert interesting["label"] == "interesting"
    assert suspicious["label"] == "suspicious"


def test_device_interest_score_minimal_history_edge_case_safe():
    result = dashboard.compute_device_interest_score(
        {"name": "Inconnu", "address": "AA:44", "rssi": -79},
        registry_row={},
        observations=[],
    )

    assert result["score"] == 0
    assert result["label"] == "normal"


def test_new_device_anomaly_appears_when_applicable():
    flags = dashboard.detect_device_anomaly_flags(
        {"name": "Inconnu", "address": "AA:55", "rssi": -80},
        registry_row={
            "seen_count": 1,
            "first_seen": "2026-04-21 10:00:00",
            "last_seen": "2026-04-21 10:00:00",
        },
        observations=[],
    )

    assert "NEW_DEVICE" in flags


def test_stability_break_anomaly_appears_when_applicable():
    flags = dashboard.detect_device_anomaly_flags(
        {"name": "Beacon", "address": "AA:66", "rssi": -90},
        registry_row={"seen_count": 10},
        observations=[
            {"scan_pos": 0, "name": "Beacon", "rssi": -55},
            {"scan_pos": 1, "name": "Beacon", "rssi": -86},
            {"scan_pos": 2, "name": "Beacon", "rssi": -74},
            {"scan_pos": 3, "name": "Beacon", "rssi": -89},
        ],
    )

    assert "STABILITY_BREAK" in flags


def test_name_change_spike_anomaly_appears_when_applicable():
    flags = dashboard.detect_device_anomaly_flags(
        {"name": "Name-C", "address": "AA:77", "rssi": -72},
        registry_row={"seen_count": 6},
        observations=[
            {"scan_pos": 0, "name": "Name-A", "rssi": -71},
            {"scan_pos": 1, "name": "Name-B", "rssi": -70},
            {"scan_pos": 2, "name": "Name-C", "rssi": -72},
        ],
    )

    assert "NAME_CHANGE_SPIKE" in flags


def test_reappear_alert_anomaly_appears_when_applicable():
    flags = dashboard.detect_device_anomaly_flags(
        {"name": "Beacon", "address": "AA:88", "rssi": -73},
        registry_row={"seen_count": 5},
        observations=[
            {"scan_pos": 0, "name": "Beacon", "rssi": -72},
            {"scan_pos": 4, "name": "Beacon", "rssi": -73},
        ],
    )

    assert "REAPPEAR_ALERT" in flags


def test_quiet_minimal_history_device_remains_clean_without_noise():
    flags = dashboard.detect_device_anomaly_flags(
        {"name": "Inconnu", "address": "AA:99", "rssi": -79},
        registry_row={
            "seen_count": 3,
            "first_seen": "2026-04-20 10:00:00",
            "last_seen": "2026-04-21 10:00:00",
        },
        observations=[
            {"scan_pos": 0, "name": "Inconnu", "rssi": -79},
            {"scan_pos": 1, "name": "Inconnu", "rssi": -78},
        ],
    )

    assert flags == []
