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

    assert result["base_score"] == 6
    assert result["anomaly_boost"] == 5
    assert "STABILITY_BREAK" in result["anomaly_flags"]
    assert "REAPPEAR_ALERT" in result["anomaly_flags"]
    assert result["score"] == 11
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

    assert result["base_score"] == 0
    assert result["anomaly_boost"] == 1
    assert "NEW_DEVICE" in result["anomaly_flags"]
    assert result["score"] == 1
    assert result["label"] == "normal"


def test_stronger_anomaly_produces_larger_boost_than_weaker_anomaly():
    weak = dashboard.compute_device_interest_score(
        {"name": "Inconnu", "address": "AA:45", "rssi": -78},
        registry_row={
            "seen_count": 1,
            "first_seen": "2026-04-21 10:00:00",
            "last_seen": "2026-04-21 10:00:00",
        },
        observations=[],
    )
    strong = dashboard.compute_device_interest_score(
        {"name": "Beacon", "address": "AA:46", "rssi": -90},
        registry_row={"seen_count": 10},
        observations=[
            {"scan_pos": 0, "name": "Beacon", "rssi": -55},
            {"scan_pos": 1, "name": "Beacon", "rssi": -86},
            {"scan_pos": 2, "name": "Beacon", "rssi": -74},
            {"scan_pos": 3, "name": "Beacon", "rssi": -89},
        ],
    )

    assert weak["anomaly_boost"] < strong["anomaly_boost"]


def test_score_label_mapping_still_behaves_correctly_after_anomaly_boost():
    normal = dashboard.compute_device_interest_score(
        {"name": "Inconnu", "address": "AA:47", "rssi": -80},
        registry_row={
            "seen_count": 1,
            "first_seen": "2026-04-21 10:00:00",
            "last_seen": "2026-04-21 10:00:00",
        },
        observations=[],
    )
    interesting = dashboard.compute_device_interest_score(
        {"name": "Beacon", "address": "AA:48", "rssi": -72},
        registry_row={
            "seen_count": 8,
            "first_seen": "2026-04-20 10:00:00",
            "last_seen": "2026-04-21 10:00:00",
        },
        observations=[],
    )
    suspicious = dashboard.compute_device_interest_score(
        {"name": "Beacon-New", "address": "AA:49", "rssi": -92},
        registry_row={"seen_count": 8},
        observations=[
            {"scan_pos": 0, "name": "Beacon-Old", "rssi": -55},
            {"scan_pos": 4, "name": "Beacon-New", "rssi": -84},
        ],
    )

    assert normal["label"] == "normal"
    assert interesting["label"] == "interesting"
    assert suspicious["label"] == "suspicious"


def test_devices_without_anomalies_keep_normal_deterministic_scoring_path():
    result = dashboard.compute_device_interest_score(
        {"name": "Beacon", "address": "AA:50", "rssi": -74},
        registry_row={
            "seen_count": 8,
            "first_seen": "2026-04-20 10:00:00",
            "last_seen": "2026-04-21 10:00:00",
        },
        observations=[
            {"scan_pos": 0, "name": "Beacon", "rssi": -74},
            {"scan_pos": 1, "name": "Beacon", "rssi": -73},
        ],
    )

    assert result["base_score"] == 2
    assert result["anomaly_boost"] == 0
    assert result["score"] == 2
    assert result["label"] == "interesting"
    assert result["anomaly_flags"] == []


def test_compact_dashboard_rendering_still_works_with_boosted_scores(monkeypatch):
    sample_devices = [
        {
            "name": "Beacon-New",
            "address": "AA:51",
            "vendor": "TestVendor",
            "profile": "general_ble",
            "rssi": -92,
            "risk_score": 10,
            "follow_score": 10,
            "confidence_score": 10,
            "final_score": 30,
            "alert_level": "moyen",
            "seen_count": 2,
            "reason_short": "normal",
            "flags": [],
        }
    ]

    monkeypatch.setattr(
        dashboard,
        "load_scan_history",
        lambda: [
            {
                "stamp": "2026-04-21_10-00-00",
                "count": 1,
                "critical": 0,
                "high": 0,
                "medium": 1,
                "devices": [
                    {"address": "AA:51", "name": "Beacon-Old", "rssi": -55},
                ],
            },
            {
                "stamp": "2026-04-21_10-05-00",
                "count": 1,
                "critical": 0,
                "high": 0,
                "medium": 1,
                "devices": [
                    {"address": "AA:51", "name": "Beacon-New", "rssi": -84},
                ],
            },
        ],
    )
    monkeypatch.setattr(
        dashboard,
        "load_registry",
        lambda: {
            "AA:51": {
                "address": "AA:51",
                "seen_count": 8,
                "session_count": 2,
                "first_seen": "2026-04-20 10:00:00",
                "last_seen": "2026-04-21 10:05:00",
            }
        },
    )
    monkeypatch.setattr(dashboard, "load_last_scan", lambda: [])
    monkeypatch.setattr(dashboard, "load_watch_cases", lambda: {})
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: [])

    html = dashboard.render_dashboard_html(sample_devices, "2026-04-21_10-06-00")

    assert 'data-device-interest-badge="true"' in html
    assert 'data-device-interest-boost="' in html
    assert 'data-device-anomaly-flags="true"' in html


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


def test_live_alert_appears_for_new_anomaly():
    alerts = dashboard.detect_device_live_alerts(
        {"name": "Inconnu", "address": "AB:01", "rssi": -80},
        registry_row={
            "seen_count": 1,
            "first_seen": "2026-04-21 10:00:00",
            "last_seen": "2026-04-21 10:00:00",
        },
        observations=[],
    )

    assert "New device anomaly detected" in alerts


def test_live_alert_appears_for_stability_break():
    alerts = dashboard.detect_device_live_alerts(
        {"name": "Beacon", "address": "AB:02", "rssi": -91},
        registry_row={"seen_count": 10},
        observations=[
            {"scan_pos": 0, "name": "Beacon", "rssi": -55},
            {"scan_pos": 1, "name": "Beacon", "rssi": -56},
            {"scan_pos": 2, "name": "Beacon", "rssi": -57},
        ],
    )

    assert "Device stability break detected" in alerts


def test_live_alert_appears_for_risk_spike():
    alerts = dashboard.detect_device_live_alerts(
        {"name": "Beacon-New", "address": "AB:03", "rssi": -92},
        registry_row={"seen_count": 8},
        observations=[
            {"scan_pos": 0, "name": "Beacon-Old", "rssi": -55},
            {"scan_pos": 4, "name": "Beacon-New", "rssi": -84},
        ],
    )

    assert "Risk spike detected" in alerts


def test_quiet_minimal_history_devices_do_not_produce_noisy_live_alerts():
    alerts = dashboard.detect_device_live_alerts(
        {"name": "Inconnu", "address": "AB:04", "rssi": -79},
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

    assert alerts == []


def test_dashboard_rendering_remains_clean_with_live_alert_support(monkeypatch):
    sample_devices = [
        {
            "name": "Beacon-New",
            "address": "AB:05",
            "vendor": "TestVendor",
            "profile": "general_ble",
            "rssi": -92,
            "risk_score": 10,
            "follow_score": 10,
            "confidence_score": 10,
            "final_score": 30,
            "alert_level": "moyen",
            "seen_count": 2,
            "reason_short": "normal",
            "flags": [],
        }
    ]

    monkeypatch.setattr(
        dashboard,
        "load_scan_history",
        lambda: [
            {
                "stamp": "2026-04-21_10-00-00",
                "count": 1,
                "critical": 0,
                "high": 0,
                "medium": 1,
                "devices": [
                    {"address": "AB:05", "name": "Beacon-Old", "rssi": -55},
                ],
            },
            {
                "stamp": "2026-04-21_10-05-00",
                "count": 1,
                "critical": 0,
                "high": 0,
                "medium": 1,
                "devices": [
                    {"address": "AB:05", "name": "Beacon-New", "rssi": -84},
                ],
            },
        ],
    )
    monkeypatch.setattr(
        dashboard,
        "load_registry",
        lambda: {
            "AB:05": {
                "address": "AB:05",
                "seen_count": 8,
                "session_count": 2,
                "first_seen": "2026-04-20 10:00:00",
                "last_seen": "2026-04-21 10:05:00",
            }
        },
    )
    monkeypatch.setattr(dashboard, "load_last_scan", lambda: [])
    monkeypatch.setattr(dashboard, "load_watch_cases", lambda: {})
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: [])

    html = dashboard.render_dashboard_html(sample_devices, "2026-04-21_10-06-00")

    assert 'data-device-interest-badge="true"' in html
    assert 'data-device-anomaly-flags="true"' in html
    assert 'data-device-live-alerts="true"' in html


def test_profile_renders_for_normal_recurring_device():
    profile = dashboard.build_compact_device_profile(
        {"name": "Beacon", "address": "AC:01", "rssi": -74},
        registry_row={"seen_count": 10},
        observations=[
            {"scan_pos": 0, "name": "Beacon", "rssi": -74},
            {"scan_pos": 1, "name": "Beacon", "rssi": -73},
        ],
    )

    assert profile["total_sightings"] == 10
    assert profile["anomaly_count"] == 0
    assert profile["trust_level"] == "high"


def test_profile_anomaly_count_appears_when_anomalies_exist():
    profile = dashboard.build_compact_device_profile(
        {"name": "Beacon-New", "address": "AC:02", "rssi": -92},
        registry_row={"seen_count": 8},
        observations=[
            {"scan_pos": 0, "name": "Beacon-Old", "rssi": -55},
            {"scan_pos": 4, "name": "Beacon-New", "rssi": -84},
        ],
    )

    assert profile["anomaly_count"] >= 1


def test_profile_trust_level_mapping_behaves_correctly():
    high = dashboard.build_compact_device_profile(
        {"name": "Beacon", "address": "AC:03", "rssi": -74},
        registry_row={"seen_count": 10},
        observations=[
            {"scan_pos": 0, "name": "Beacon", "rssi": -74},
            {"scan_pos": 1, "name": "Beacon", "rssi": -73},
        ],
    )
    medium = dashboard.build_compact_device_profile(
        {"name": "Beacon", "address": "AC:04", "rssi": -75},
        registry_row={"seen_count": 4},
        observations=[
            {"scan_pos": 0, "name": "Beacon", "rssi": -75},
            {"scan_pos": 1, "name": "Beacon", "rssi": -74},
        ],
    )
    low = dashboard.build_compact_device_profile(
        {"name": "Beacon-New", "address": "AC:05", "rssi": -92},
        registry_row={"seen_count": 8},
        observations=[
            {"scan_pos": 0, "name": "Beacon-Old", "rssi": -55},
            {"scan_pos": 4, "name": "Beacon-New", "rssi": -84},
        ],
    )

    assert high["trust_level"] == "high"
    assert medium["trust_level"] == "medium"
    assert low["trust_level"] == "low"


def test_profile_minimal_history_device_remains_safe_and_compact():
    profile = dashboard.build_compact_device_profile(
        {"name": "Inconnu", "address": "AC:06", "rssi": -80},
        registry_row={},
        observations=[],
    )

    assert profile["total_sightings"] == 0
    assert profile["anomaly_count"] >= 0
    assert profile["trust_level"] in {"low", "medium", "high"}


def test_dashboard_rendering_remains_clean_with_profile_support(monkeypatch):
    sample_devices = [
        {
            "name": "Beacon-New",
            "address": "AC:07",
            "vendor": "TestVendor",
            "profile": "general_ble",
            "rssi": -92,
            "risk_score": 10,
            "follow_score": 10,
            "confidence_score": 10,
            "final_score": 30,
            "alert_level": "moyen",
            "seen_count": 2,
            "reason_short": "normal",
            "flags": [],
        }
    ]

    monkeypatch.setattr(
        dashboard,
        "load_scan_history",
        lambda: [
            {
                "stamp": "2026-04-21_10-00-00",
                "count": 1,
                "critical": 0,
                "high": 0,
                "medium": 1,
                "devices": [
                    {"address": "AC:07", "name": "Beacon-Old", "rssi": -55},
                ],
            },
            {
                "stamp": "2026-04-21_10-05-00",
                "count": 1,
                "critical": 0,
                "high": 0,
                "medium": 1,
                "devices": [
                    {"address": "AC:07", "name": "Beacon-New", "rssi": -84},
                ],
            },
        ],
    )
    monkeypatch.setattr(
        dashboard,
        "load_registry",
        lambda: {
            "AC:07": {
                "address": "AC:07",
                "seen_count": 8,
                "session_count": 2,
                "first_seen": "2026-04-20 10:00:00",
                "last_seen": "2026-04-21 10:05:00",
            }
        },
    )
    monkeypatch.setattr(dashboard, "load_last_scan", lambda: [])
    monkeypatch.setattr(dashboard, "load_watch_cases", lambda: {})
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: [])

    html = dashboard.render_dashboard_html(sample_devices, "2026-04-21_10-06-00")

    assert 'data-device-interest-badge="true"' in html
    assert 'data-device-anomaly-flags="true"' in html
    assert 'data-device-live-alerts="true"' in html
    assert 'data-device-profile="true"' in html
