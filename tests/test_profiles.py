from ble_radar import profiles


REQUIRED_KEYS = {"key", "label", "scan_seconds", "live_seconds", "alert_floor"}


def test_list_profiles_has_required_fields():
    items = profiles.list_profiles()
    assert isinstance(items, list)
    assert len(items) >= 1

    for item in items:
        assert REQUIRED_KEYS.issubset(item.keys())
        assert isinstance(item["key"], str) and item["key"]
        assert isinstance(item["label"], str) and item["label"]
        assert isinstance(item["scan_seconds"], int)
        assert isinstance(item["live_seconds"], int)
        assert isinstance(item["alert_floor"], str) and item["alert_floor"]


def test_get_active_profile_is_in_profile_list():
    items = profiles.list_profiles()
    keys = {item["key"] for item in items}
    active = profiles.get_active_profile()

    assert active["key"] in keys
    assert REQUIRED_KEYS.issubset(active.keys())


def test_set_profile_key_switches_to_existing_profile():
    items = profiles.list_profiles()
    original_key = profiles.get_active_profile()["key"]
    target_key = items[-1]["key"]

    profiles.set_profile_key(target_key)
    try:
        active = profiles.get_active_profile()
        assert active["key"] == target_key
    finally:
        profiles.set_profile_key(original_key)


def test_set_profile_key_invalid_keeps_current_profile():
    original_key = profiles.get_active_profile()["key"]

    profiles.set_profile_key("__profil_inexistant__")
    active = profiles.get_active_profile()

    assert active["key"] == original_key
