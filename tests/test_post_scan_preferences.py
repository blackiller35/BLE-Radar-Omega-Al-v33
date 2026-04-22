from ble_radar import post_scan_preferences as prefs


def test_post_scan_preference_defaults_to_ask(monkeypatch, tmp_path):
    monkeypatch.setattr(
        prefs,
        "POST_SCAN_PREFERENCE_FILE",
        tmp_path / "post_scan_preference.json",
    )
    assert prefs.load_post_scan_preference()["open_mode"] == "ask"


def test_post_scan_preference_can_save_and_load(monkeypatch, tmp_path):
    monkeypatch.setattr(
        prefs,
        "POST_SCAN_PREFERENCE_FILE",
        tmp_path / "post_scan_preference.json",
    )
    prefs.save_post_scan_preference("operator_panel")
    assert prefs.get_post_scan_open_mode() == "operator_panel"
