from ble_radar.history import device_registry as dr


def test_update_registry_tracks_seen_and_session_counts():
    devices = [
        {"address": "aa:bb", "name": "One"},
        {"address": "AA:BB", "name": "One again"},
        {"address": "cc:dd", "name": "Two"},
    ]

    updated = dr.update_registry_with_devices(
        devices,
        registry={},
        session_id="session-1",
        seen_at="2026-04-18 10:00:00",
    )

    assert updated["AA:BB"]["first_seen"] == "2026-04-18 10:00:00"
    assert updated["AA:BB"]["last_seen"] == "2026-04-18 10:00:00"
    assert updated["AA:BB"]["seen_count"] == 2
    assert updated["AA:BB"]["session_count"] == 1

    updated = dr.update_registry_with_devices(
        [{"address": "AA:BB"}],
        registry=updated,
        session_id="session-1",
        seen_at="2026-04-18 10:01:00",
    )
    assert updated["AA:BB"]["seen_count"] == 3
    assert updated["AA:BB"]["session_count"] == 1

    updated = dr.update_registry_with_devices(
        [{"address": "AA:BB"}],
        registry=updated,
        session_id="session-2",
        seen_at="2026-04-18 10:02:00",
    )
    assert updated["AA:BB"]["seen_count"] == 4
    assert updated["AA:BB"]["session_count"] == 2


def test_load_and_save_registry_roundtrip(tmp_path, monkeypatch):
    path = tmp_path / "device_registry.json"
    monkeypatch.setattr(dr, "DEVICE_REGISTRY_FILE", path)

    assert dr.load_registry() == {}

    data = {
        "aa:bb": {
            "address": "aa:bb",
            "first_seen": "2026-04-18 11:00:00",
            "last_seen": "2026-04-18 11:01:00",
            "seen_count": "3",
            "session_count": 2,
        }
    }
    dr.save_registry(data)

    loaded = dr.load_registry()
    assert "AA:BB" in loaded
    assert loaded["AA:BB"]["seen_count"] == 3
    assert loaded["AA:BB"]["session_count"] == 2
