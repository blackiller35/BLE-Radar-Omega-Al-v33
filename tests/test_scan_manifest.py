from ble_radar import scan_manifest


SAMPLE_DEVICES = [
    {
        "name": "Beacon-One",
        "address": "AA:BB:CC:DD:EE:01",
        "vendor": "TestVendor",
        "profile": "general_ble",
        "final_score": 72,
        "alert_level": "critique",
        "reason_short": "watch_hit",
        "watch_hit": True,
    },
    {
        "name": "Tracker-Two",
        "address": "AA:BB:CC:DD:EE:02",
        "vendor": "TrackCorp",
        "profile": "tracker_like",
        "final_score": 44,
        "alert_level": "moyen",
        "reason_short": "tracker",
        "possible_suivi": True,
    },
    {
        "name": "Unknown-Three",
        "address": "AA:BB:CC:DD:EE:03",
        "vendor": "TestVendor",
        "profile": "general_ble",
        "final_score": 10,
        "alert_level": "faible",
        "reason_short": "normal",
    },
]


def test_build_scan_manifest_counts_expected_values():
    manifest = scan_manifest.build_scan_manifest(SAMPLE_DEVICES, "2026-04-17_18-40-00")

    assert manifest["stamp"] == "2026-04-17_18-40-00"
    assert manifest["device_count"] == 3
    assert manifest["alerts"]["critical"] == 1
    assert manifest["alerts"]["medium"] == 1
    assert manifest["alerts"]["low"] == 1
    assert manifest["watch_hits"] == 1
    assert manifest["tracker_candidates"] == 2


def test_build_scan_manifest_keeps_extra_meta():
    manifest = scan_manifest.build_scan_manifest(
        SAMPLE_DEVICES,
        "2026-04-17_18-40-01",
        extra_meta={"source": "manual", "operator": "cedric"},
    )

    assert manifest["extra_meta"]["source"] == "manual"
    assert manifest["extra_meta"]["operator"] == "cedric"


def test_build_scan_manifest_sorts_top_devices():
    manifest = scan_manifest.build_scan_manifest(SAMPLE_DEVICES, "2026-04-17_18-40-02")

    assert manifest["top_devices"][0]["name"] == "Beacon-One"
    assert manifest["top_devices"][0]["final_score"] == 72
    assert manifest["top_devices"][1]["name"] == "Tracker-Two"


def test_save_and_load_scan_manifest_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(scan_manifest, "SCAN_MANIFESTS_DIR", tmp_path / "manifests")

    manifest = scan_manifest.build_scan_manifest(SAMPLE_DEVICES, "2026-04-17_18-40-03")
    path = scan_manifest.save_scan_manifest(manifest)
    loaded = scan_manifest.load_scan_manifest(path)

    assert path.exists()
    assert loaded["stamp"] == "2026-04-17_18-40-03"
    assert loaded["device_count"] == 3


def test_list_scan_manifests_returns_latest_first(tmp_path):
    m1 = tmp_path / "scan_manifest_2026-04-17_18-40-01.json"
    m2 = tmp_path / "scan_manifest_2026-04-17_18-40-02.json"
    m1.write_text("{}", encoding="utf-8")
    m2.write_text("{}", encoding="utf-8")

    items = scan_manifest.list_scan_manifests(tmp_path)

    assert items[0].name == "scan_manifest_2026-04-17_18-40-02.json"
    assert items[1].name == "scan_manifest_2026-04-17_18-40-01.json"


def test_list_scan_manifests_returns_empty_when_missing(tmp_path):
    items = scan_manifest.list_scan_manifests(tmp_path / "missing")
    assert items == []
