from ble_radar import automation_safe


def test_collect_triggered_rules_returns_matching_enabled_rules(monkeypatch):
    context = {"watch_hits": 1, "critical": 0, "trackers": 0, "health_score": 80, "high": 0}
    config = {
        "enabled": True,
        "rules": [
            {"name": "Watch hit rule", "enabled": True, "condition": "watch_hits_ge", "threshold": 1, "action": "notify"},
            {"name": "Disabled rule", "enabled": False, "condition": "watch_hits_ge", "threshold": 1, "action": "log"},
            {"name": "Health rule", "enabled": True, "condition": "health_le", "threshold": 10, "action": "alert"},
        ],
    }

    monkeypatch.setattr(
        automation_safe.automation,
        "rule_matches",
        lambda rule, ctx: (
            rule.get("condition") == "watch_hits_ge" and ctx.get("watch_hits", 0) >= rule.get("threshold", 0)
        ) or (
            rule.get("condition") == "health_le" and ctx.get("health_score", 100) <= rule.get("threshold", 0)
        ),
    )

    items = automation_safe.collect_triggered_rules(context, config)

    assert len(items) == 1
    assert items[0]["name"] == "Watch hit rule"
    assert items[0]["action"] == "notify"


def test_collect_triggered_rules_returns_empty_when_engine_disabled():
    context = {"watch_hits": 2}
    config = {"enabled": False, "rules": [{"name": "X", "enabled": True, "condition": "watch_hits_ge", "threshold": 1}]}

    items = automation_safe.collect_triggered_rules(context, config)

    assert items == []


def test_build_trace_lines_handles_no_rules():
    lines = automation_safe.build_trace_lines(
        {"critical": 0, "high": 0, "watch_hits": 0, "trackers": 0, "health_score": 100},
        [],
        enabled=True,
    )

    assert lines[0] == "Automation safe mode"
    assert "No rules triggered." in lines


def test_build_trace_lines_handles_disabled_engine():
    lines = automation_safe.build_trace_lines(
        {"critical": 1, "high": 0, "watch_hits": 1, "trackers": 0, "health_score": 90},
        [],
        enabled=False,
    )

    assert "Engine: disabled" in lines
    assert "No rules evaluated: automation disabled." in lines


def test_build_dry_run_report_contains_suggestions_and_trace(monkeypatch):
    config = {
        "enabled": True,
        "rules": [
            {"name": "Watch hit rule", "enabled": True, "condition": "watch_hits_ge", "threshold": 1, "action": "notify"},
        ],
    }

    monkeypatch.setattr(
        automation_safe.automation,
        "build_context",
        lambda devices: {"critical": 0, "high": 0, "watch_hits": 1, "trackers": 0, "health_score": 88},
    )
    monkeypatch.setattr(
        automation_safe.automation,
        "rule_matches",
        lambda rule, ctx: ctx.get("watch_hits", 0) >= rule.get("threshold", 0),
    )

    report = automation_safe.build_dry_run_report([{"name": "Beacon-One"}], config=config)

    assert report["mode"] == "dry-run"
    assert report["enabled"] is True
    assert len(report["triggered_rules"]) == 1
    assert "Would execute action=notify for rule=Watch hit rule" in report["suggested_actions"][0]
    assert any("Triggered rules:" in line for line in report["trace_lines"])


def test_build_dry_run_report_reports_disabled_engine(monkeypatch):
    config = {"enabled": False, "rules": [{"name": "X", "enabled": True, "condition": "watch_hits_ge", "threshold": 1}]}

    monkeypatch.setattr(
        automation_safe.automation,
        "build_context",
        lambda devices: {"critical": 0, "high": 0, "watch_hits": 2, "trackers": 1, "health_score": 77},
    )

    report = automation_safe.build_dry_run_report([{"name": "Beacon-One"}], config=config)

    assert report["enabled"] is False
    assert report["triggered_rules"] == []
    assert report["suggested_actions"] == []
    assert any("automation disabled" in line.lower() for line in report["trace_lines"])
