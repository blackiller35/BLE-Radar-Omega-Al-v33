from datetime import datetime
from pathlib import Path
import json

from ble_radar.config import STATE_DIR, HISTORY_DIR
from ble_radar.state import load_json, save_json
from ble_radar.ops import radio_health
from ble_radar.audit import build_audit_package, save_audit_package
from ble_radar.snapshots import create_snapshot
from ble_radar.eventlog import log_event

AUTOMATION_FILE = STATE_DIR / "automation_rules.json"
INCIDENTS_DIR = HISTORY_DIR / "incidents"
INCIDENTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_AUTOMATION = {
    "enabled": True,
    "rules": [
        {
            "id": "watch_hit_audit",
            "label": "Audit auto si watchlist hit",
            "enabled": True,
            "condition": "watch_hits_ge",
            "threshold": 1,
            "action": "export_audit",
        },
        {
            "id": "critical_snapshot",
            "label": "Snapshot auto si alerte critique",
            "enabled": True,
            "condition": "critical_ge",
            "threshold": 1,
            "action": "create_snapshot",
        },
        {
            "id": "tracker_incident",
            "label": "Incident auto si trackers >= 2",
            "enabled": True,
            "condition": "trackers_ge",
            "threshold": 2,
            "action": "log_incident",
        },
        {
            "id": "radio_incident",
            "label": "Incident auto si santé radio <= 45",
            "enabled": True,
            "condition": "health_le",
            "threshold": 45,
            "action": "log_incident",
        },
    ],
}

if not AUTOMATION_FILE.exists():
    save_json(AUTOMATION_FILE, DEFAULT_AUTOMATION)


def load_automation_config():
    data = load_json(AUTOMATION_FILE, DEFAULT_AUTOMATION)
    if not isinstance(data, dict):
        data = DEFAULT_AUTOMATION
    if "enabled" not in data:
        data["enabled"] = True
    if "rules" not in data or not isinstance(data["rules"], list):
        data["rules"] = DEFAULT_AUTOMATION["rules"]
    return data


def save_automation_config(data):
    save_json(AUTOMATION_FILE, data)


def toggle_automation_engine():
    data = load_automation_config()
    data["enabled"] = not bool(data.get("enabled", True))
    save_automation_config(data)
    return data


def toggle_rule_by_index(index: int):
    data = load_automation_config()
    rules = data.get("rules", [])
    if 0 <= index < len(rules):
        rules[index]["enabled"] = not bool(rules[index].get("enabled", True))
    save_automation_config(data)
    return data


def build_context(devices):
    health = radio_health(devices)
    critical = sum(1 for d in devices if d.get("alert_level") == "critique")
    high = sum(1 for d in devices if d.get("alert_level") == "élevé")
    trackers = sum(
        1 for d in devices
        if d.get("profile") == "tracker_probable"
        or d.get("possible_suivi")
        or d.get("watch_hit")
    )
    watch_hits = sum(1 for d in devices if d.get("watch_hit"))

    return {
        "critical": critical,
        "high": high,
        "trackers": trackers,
        "watch_hits": watch_hits,
        "health_score": health["score"],
        "health_label": health["label"],
    }


def rule_matches(rule, ctx):
    cond = rule.get("condition")
    threshold = int(rule.get("threshold", 0))

    if cond == "watch_hits_ge":
        return ctx["watch_hits"] >= threshold
    if cond == "critical_ge":
        return ctx["critical"] >= threshold
    if cond == "trackers_ge":
        return ctx["trackers"] >= threshold
    if cond == "health_le":
        return ctx["health_score"] <= threshold
    if cond == "high_ge":
        return ctx["high"] >= threshold
    return False


def save_incident(devices, ctx, rule):
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = INCIDENTS_DIR / f"incident_{stamp}.json"
    payload = {
        "stamp": stamp,
        "rule": rule,
        "context": ctx,
        "top_devices": sorted(
            devices,
            key=lambda d: d.get("final_score", d.get("score", 0)),
            reverse=True,
        )[:15],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def execute_rule_action(rule, devices, comparison=None):
    action = rule.get("action")

    if action == "export_audit":
        package = build_audit_package(devices, comparison)
        paths = save_audit_package(package)
        log_event("automation", "info", f"audit auto exécuté: {rule.get('label','rule')}", {
            "rule_id": rule.get("id"),
            "json": str(paths["json"]),
            "txt": str(paths["txt"]),
        })
        return {
            "action": action,
            "label": rule.get("label", action),
            "result": paths,
        }

    if action == "create_snapshot":
        snap = create_snapshot()
        log_event("automation", "warning", f"snapshot auto exécuté: {rule.get('label','rule')}", {
            "rule_id": rule.get("id"),
            "path": str(snap["path"]),
        })
        return {
            "action": action,
            "label": rule.get("label", action),
            "result": snap,
        }

    if action == "log_incident":
        ctx = build_context(devices)
        incident = save_incident(devices, ctx, rule)
        log_event("automation", "warning", f"incident auto créé: {rule.get('label','rule')}", {
            "rule_id": rule.get("id"),
            "path": str(incident),
        })
        return {
            "action": action,
            "label": rule.get("label", action),
            "result": {"path": incident},
        }

    return None


def run_automation_pipeline(devices, comparison=None):
    cfg = load_automation_config()
    ctx = build_context(devices)

    if not cfg.get("enabled", True):
        log_event("automation", "info", "moteur automation désactivé", ctx)
        return {
            "enabled": False,
            "context": ctx,
            "executed": [],
        }

    executed = []
    for rule in cfg.get("rules", []):
        if not rule.get("enabled", True):
            continue
        if rule_matches(rule, ctx):
            result = execute_rule_action(rule, devices, comparison)
            if result:
                executed.append(result)

    if executed:
        log_event("automation", "info", f"{len(executed)} action(s) auto exécutée(s)", {
            "count": len(executed),
            "context": ctx,
        })

    return {
        "enabled": True,
        "context": ctx,
        "executed": executed,
    }
