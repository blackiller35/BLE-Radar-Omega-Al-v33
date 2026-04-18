from ble_radar import engine


def test_run_engine_cycle_updates_device_registry(monkeypatch):
    devices = [{"address": "AA:BB", "name": "One"}]

    monkeypatch.setattr(engine, "load_runtime_config", lambda: {"scan_timeout": 5})
    monkeypatch.setattr(engine, "run_engine_scan", lambda seconds: devices)
    monkeypatch.setattr(engine, "load_last_scan", lambda: [])
    monkeypatch.setattr(engine, "compare_device_sets", lambda current, previous: {"added": [], "removed": [], "common": []})
    monkeypatch.setattr(engine, "persist_live_observations", lambda _: None)
    monkeypatch.setattr(engine, "save_all_reports", lambda _: {"html": "x"})
    monkeypatch.setattr(engine, "save_last_scan", lambda _: None)

    calls = {"load": 0, "update": 0, "save": 0}

    def _load_registry():
        calls["load"] += 1
        return {}

    def _update_registry_with_devices(devices_arg, registry=None, session_id=None, seen_at=None):
        calls["update"] += 1
        assert devices_arg == devices
        assert isinstance(registry, dict)
        assert isinstance(session_id, str) and session_id
        assert isinstance(seen_at, str) and seen_at
        return {"AA:BB": {"address": "AA:BB", "seen_count": 1, "session_count": 1}}

    def _save_registry(registry_arg):
        calls["save"] += 1
        assert "AA:BB" in registry_arg

    monkeypatch.setattr(engine, "load_registry", _load_registry)
    monkeypatch.setattr(engine, "update_registry_with_devices", _update_registry_with_devices)
    monkeypatch.setattr(engine, "save_registry", _save_registry)

    result = engine.run_engine_cycle()

    assert result["devices"] == devices
    assert calls == {"load": 1, "update": 1, "save": 1}


def test_run_engine_cycle_registry_failure_is_non_blocking(monkeypatch):
    devices = [{"address": "AA:BB", "name": "One"}]

    monkeypatch.setattr(engine, "load_runtime_config", lambda: {"scan_timeout": 5})
    monkeypatch.setattr(engine, "run_engine_scan", lambda seconds: devices)
    monkeypatch.setattr(engine, "load_last_scan", lambda: [])
    monkeypatch.setattr(engine, "compare_device_sets", lambda current, previous: {"added": [], "removed": [], "common": []})
    monkeypatch.setattr(engine, "persist_live_observations", lambda _: None)
    monkeypatch.setattr(engine, "save_all_reports", lambda _: {"html": "x"})
    monkeypatch.setattr(engine, "save_last_scan", lambda _: None)

    monkeypatch.setattr(engine, "load_registry", lambda: (_ for _ in ()).throw(RuntimeError("io")))

    result = engine.run_engine_cycle()

    assert result["devices"] == devices
    assert isinstance(result["comparison"], dict)
