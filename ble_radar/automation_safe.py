from __future__ import annotations

from ble_radar import automation


def _rule_name(rule: dict, index: int) -> str:
    return str(rule.get("name") or rule.get("title") or rule.get("label") or f"rule_{index}")


def _rule_action(rule: dict) -> str:
    return str(rule.get("action") or rule.get("effect") or "notify")


def collect_triggered_rules(context: dict, config: dict | None = None) -> list[dict]:
    cfg = config or automation.load_automation_config()
    if not cfg.get("enabled", True):
        return []

    triggered = []
    for index, rule in enumerate(cfg.get("rules", [])):
        if not rule.get("enabled", True):
            continue

        matched = False
        try:
            matched = bool(automation.rule_matches(rule, context))
        except Exception:
            matched = False

        if not matched:
            continue

        triggered.append(
            {
                "index": index,
                "name": _rule_name(rule, index),
                "condition": rule.get("condition", ""),
                "threshold": rule.get("threshold"),
                "action": _rule_action(rule),
            }
        )

    return triggered


def build_trace_lines(context: dict, triggered_rules: list[dict], enabled: bool = True) -> list[str]:
    lines = [
        "Automation safe mode",
        f"Engine: {'enabled' if enabled else 'disabled'}",
        "Context: "
        f"critical={context.get('critical', 0)} | "
        f"high={context.get('high', 0)} | "
        f"watch_hits={context.get('watch_hits', 0)} | "
        f"trackers={context.get('trackers', 0)} | "
        f"health_score={context.get('health_score', 0)}",
    ]

    if not enabled:
        lines.append("No rules evaluated: automation disabled.")
        return lines

    if not triggered_rules:
        lines.append("No rules triggered.")
        return lines

    lines.append("Triggered rules:")
    for item in triggered_rules:
        lines.append(
            f"- #{item['index']} {item['name']} | "
            f"condition={item['condition']} | "
            f"threshold={item['threshold']} | "
            f"action={item['action']}"
        )

    return lines


def build_dry_run_report(devices: list[dict], config: dict | None = None) -> dict:
    cfg = config or automation.load_automation_config()
    enabled = bool(cfg.get("enabled", True))
    context = automation.build_context(devices)

    triggered_rules = collect_triggered_rules(context, cfg) if enabled else []
    suggested_actions = [
        f"[DRY-RUN] Would execute action={item['action']} for rule={item['name']}"
        for item in triggered_rules
    ]
    trace_lines = build_trace_lines(context, triggered_rules, enabled=enabled)

    return {
        "mode": "dry-run",
        "enabled": enabled,
        "context": context,
        "triggered_rules": triggered_rules,
        "suggested_actions": suggested_actions,
        "trace_lines": trace_lines,
    }
