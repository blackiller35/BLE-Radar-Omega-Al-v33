from pathlib import Path
import importlib
import json

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "main.py",
    "ble_radar/__init__.py",
    "ble_radar/app.py",
    "ble_radar/config.py",
    "ble_radar/state.py",
    "ble_radar/intel.py",
    "ble_radar/engine.py",
    "ble_radar/router.py",
    "ble_radar/query.py",
    "ble_radar/inspector.py",
    "ble_radar/views.py",
    "ble_radar/ops.py",
    "ble_radar/reports.py",
    "ble_radar/missions.py",
    "ble_radar/mission_control.py",
    "ble_radar/orchestrator.py",
    "ble_radar/scenarios.py",
    "ble_radar/nexus.py",
    "ble_radar/daily_report.py",
    "ble_radar/argus.py",
    "ble_radar/sentinel.py",
    "ble_radar/atlas.py",
    "ble_radar/helios.py",
    "ble_radar/behavior.py",
    "ble_radar/knowledge.py",
    "ble_radar/automation.py",
    "ble_radar/eventlog.py",
    "ble_radar/fortress.py",
    "ble_radar/snapshots.py",
    "ble_radar/aegis.py",
    "ble_radar/oracle.py",
    "ble_radar/nebula.py",
    "ble_radar/citadel.py",
    "ble_radar/commander.py",
]

REQUIRED_IMPORTS = [
    "ble_radar.app",
    "ble_radar.config",
    "ble_radar.state",
    "ble_radar.intel",
    "ble_radar.engine",
    "ble_radar.router",
    "ble_radar.query",
    "ble_radar.inspector",
    "ble_radar.views",
    "ble_radar.ops",
    "ble_radar.reports",
    "ble_radar.missions",
    "ble_radar.mission_control",
    "ble_radar.orchestrator",
    "ble_radar.scenarios",
    "ble_radar.doctor",
    "ble_radar.snapshots",
    "ble_radar.fortress",
    "ble_radar.eventlog",
    "ble_radar.automation",
    "ble_radar.nexus",
    "ble_radar.knowledge",
    "ble_radar.behavior",
    "ble_radar.daily_report",
    "ble_radar.argus",
    "ble_radar.sentinel",
    "ble_radar.atlas",
    "ble_radar.helios",
    "ble_radar.aegis",
    "ble_radar.oracle",
    "ble_radar.nebula",
    "ble_radar.citadel",
    "ble_radar.commander",
]

JSON_FILES = [
    "state/whitelist.json",
    "state/watchlist.json",
    "state/live_devices.json",
    "state/last_scan.json",
    "history/scan_history.json",
    "history/trends.json",
    "state/saved_queries.json",
    "state/profile_mode.json",
    "state/mission_mode.json",
]


def check_files():
    out = []
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        out.append({
            "file": rel,
            "exists": path.exists(),
        })
    return out


def check_imports():
    out = []
    for mod in REQUIRED_IMPORTS:
        try:
            importlib.import_module(mod)
            out.append({"module": mod, "ok": True, "error": ""})
        except Exception as e:
            out.append({"module": mod, "ok": False, "error": str(e)})
    return out


def check_json_files():
    out = []
    for rel in JSON_FILES:
        path = ROOT / rel
        if not path.exists():
            out.append({"file": rel, "ok": False, "error": "missing"})
            continue

        try:
            json.loads(path.read_text(encoding="utf-8"))
            out.append({"file": rel, "ok": True, "error": ""})
        except Exception as e:
            out.append({"file": rel, "ok": False, "error": str(e)})
    return out


def build_doctor_report():
    files = check_files()
    imports = check_imports()
    jsons = check_json_files()

    return {
        "files_ok": sum(1 for x in files if x["exists"]),
        "files_total": len(files),
        "imports_ok": sum(1 for x in imports if x["ok"]),
        "imports_total": len(imports),
        "json_ok": sum(1 for x in jsons if x["ok"]),
        "json_total": len(jsons),
        "files": files,
        "imports": imports,
        "json": jsons,
    }


def doctor_lines(report):
    lines = [
        f"Fichiers: {report['files_ok']}/{report['files_total']}",
        f"Imports: {report['imports_ok']}/{report['imports_total']}",
        f"JSON: {report['json_ok']}/{report['json_total']}",
        "",
        "Détails fichiers:",
    ]
    for x in report["files"]:
        lines.append(f"- {x['file']}: {'OK' if x['exists'] else 'MANQUANT'}")

    lines.append("")
    lines.append("Détails imports:")
    for x in report["imports"]:
        if x["ok"]:
            lines.append(f"- {x['module']}: OK")
        else:
            lines.append(f"- {x['module']}: ERREUR -> {x['error']}")

    lines.append("")
    lines.append("Détails JSON:")
    for x in report["json"]:
        if x["ok"]:
            lines.append(f"- {x['file']}: OK")
        else:
            lines.append(f"- {x['file']}: ERREUR -> {x['error']}")

    return lines
