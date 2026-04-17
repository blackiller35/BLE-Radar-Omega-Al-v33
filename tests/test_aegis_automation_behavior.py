from copy import deepcopy

from ble_radar import aegis, automation


def test_toggle_aegis_engine_flips_enabled(monkeypatch, tmp_path):
    monkeypatch.setattr(aegis, "AEGIS_FILE", tmp_path / "aegis_rules.json")
    aegis.save_aegis_config(deepcopy(aegis.DEFAULT_AEGIS))

    data = aegis.toggle_aegis_engine()
    assert data["enabled"] is False

    data = aegis.toggle_aegis_engine()
    assert data["enabled"] is True


def test_shift_threshold_clamps_at_zero(monkeypatch, tmp_path):
    monkeypatch.setattr(aegis, "AEGIS_FILE", tmp_path / "aegis_rules.json")
    aegis.save_aegis_config(deepcopy(aegis.DEFAULT_AEGIS))

    data = aegis.shift_threshold("watch_hits", -999)
    assert data["thresholds"]["watch_hits"] == 0


def test_playbook_lines_contains_title_and_actions():
    playbook = aegis.get_playbook("watch_hit_active")
    lines = aegis.playbook_lines(playbook)

    assert lines[0] == playbook["title"]
    assert lines[1] == "Actions:"
    assert any("watchlist" in line.lower() for line in lines[2:])


def test_evaluate_aegis_returns_no_incidents_when_disabled(monkeypatch):
    monkeypatch.setattr(
        aegis,
        "load_aegis_config",
        lambda: {
            "enabled": False,
            "thresholds": deepcopy(aegis.DEFAULT_AEGIS["thresholds"]),
        },
    )
    monkeypatch.setattr(aegis, "build_sentinel_report", lambda devices, prev, hist: {"threat_state": "bruit_normal"})
    monkeypatch.setattr(aegis, "build_helios_report", lambda devices, hist: {"top_priority": 0})
    monkeypatch.setattr(aegis, "rank_priority", lambda devices, history, limit: [])

    result = aegis.evaluate_aegis([], history=[])

    assert result["enabled"] is False
    assert result["incidents"] == []


def test_evaluate_aegis_detects_watch_hit_incident(monkeypatch):
    monkeypatch.setattr(
        aegis,
        "load_aegis_config",
        lambda: {
            "enabled": True,
            "thresholds": deepcopy(aegis.DEFAULT_AEGIS["thresholds"]),
        },
    )
    monkeypatch.setattr(
        aegis,
        "build_sentinel_report",
        lambda devices, prev, hist: {
            "threat_state": "pression",
            "watch_hits": 1,
            "critical_count": 0,
            "campaigns": 0,
            "tracker_count": 0,
            "escalations": 0,
            "high_count": 0,
        },
    )
    monkeypatch.setattr(aegis, "build_helios_report", lambda devices, hist: {"top_priority": 0})
    monkeypatch.setattr(aegis, "rank_priority", lambda devices, history, limit: [])

    result = aegis.evaluate_aegis([{"name": "X"}], history=[])

    keys = [x["key"] for x in result["incidents"]]
    assert "watch_hit_active" in keys


def test_toggle_automation_engine_flips_enabled(monkeypatch, tmp_path):
    monkeypatch.setattr(automation, "AUTOMATION_FILE", tmp_path / "automation_rules.json")
    automation.save_automation_config(deepcopy(automation.DEFAULT_AUTOMATION))

    data = automation.toggle_automation_engine()
    assert data["enabled"] is False

    data = automation.toggle_automation_engine()
    assert data["enabled"] is True


def test_toggle_rule_by_index_flips_rule_enabled(monkeypatch, tmp_path):
    monkeypatch.setattr(automation, "AUTOMATION_FILE", tmp_path / "automation_rules.json")
    automation.save_automation_config(deepcopy(automation.DEFAULT_AUTOMATION))

    data = automation.toggle_rule_by_index(0)
    assert data["rules"][0]["enabled"] is False

    data = automation.toggle_rule_by_index(0)
    assert data["rules"][0]["enabled"] is True


def test_rule_matches_for_watch_hits_and_health():
    assert automation.rule_matches(
        {"condition": "watch_hits_ge", "threshold": 1},
        {"watch_hits": 2, "critical": 0, "trackers": 0, "health_score": 100, "high": 0},
    ) is True

    assert automation.rule_matches(
        {"condition": "health_le", "threshold": 45},
        {"watch_hits": 0, "critical": 0, "trackers": 0, "health_score": 30, "high": 0},
    ) is True


def test_build_context_counts_watch_hits_and_trackers(monkeypatch):
    monkeypatch.setattr(automation, "radio_health", lambda devices: {"score": 44, "label": "warning"})

    devices = [
        {"alert_level": "critique", "watch_hit": True, "profile": "tracker_probable"},
        {"alert_level": "élevé", "possible_suivi": True},
        {"alert_level": "faible"},
    ]

    ctx = automation.build_context(devices)

    assert ctx["critical"] == 1
    assert ctx["high"] == 1
    assert ctx["watch_hits"] == 1
    assert ctx["trackers"] == 2
    assert ctx["health_score"] == 44
    assert ctx["health_label"] == "warning"
