from pathlib import Path
import ast
import importlib

ROOT = Path(__file__).resolve().parent.parent
APP_FILE = ROOT / "ble_radar" / "app.py"

CRITICAL_IMPORTS = [
    "ble_radar.app",
    "ble_radar.doctor",
    "ble_radar.fortress",
    "ble_radar.commander",
    "ble_radar.rootfix46",
    "ble_radar.citadel",
    "ble_radar.nebula",
    "ble_radar.oracle",
    "ble_radar.aegis",
    "ble_radar.helios",
    "ble_radar.atlas",
    "ble_radar.sentinel",
    "ble_radar.argus",
    "ble_radar.omegax" if False else None,
]

BATCH_HANDLER_NAMES = [
    "batch34_scan_hub",
    "batch34_alert_center",
    "batch34_tracker_hunt",
    "batch34_investigation_hub",
    "batch34_smart_views",
    "batch35_command_center_pro",
    "batch35_query_vault",
    "batch35_audit_export_pro",
    "batch35_metrics_anomalies_pro",
    "batch35_replay_lab_pro",
    "batch36_operator_profiles_pro",
    "batch36_mission_modes_pro",
    "batch36_mission_dashboard_pro",
    "batch36_guided_scenarios_pro",
    "batch36_html_dashboard_pro",
    "batch37_history_local_pro",
    "batch37_live_radar_pro",
    "batch37_whitelist_view_pro",
    "batch37_whitelist_add_pro",
    "batch37_whitelist_remove_pro",
    "batch38_watchlist_view_pro",
    "batch38_watchlist_add_pro",
    "batch38_watchlist_remove_pro",
    "batch38_top_recurrents_pro",
    "batch38_event_log_pro",
    "batch39_automation_center_pro",
    "batch39_doctor_integrity_pro",
    "batch39_snapshots_restore_pro",
    "batch39_nexus_center_pro",
    "batch39_omegax_center_pro",
    "batch40_argus_center_pro",
    "batch40_sentinel_center_pro",
    "batch40_atlas_center_pro",
    "batch40_helios_center_pro",
    "batch40_aegis_center_pro",
    "batch41_oracle_center_pro",
    "batch41_nebula_center_pro",
    "batch41_citadel_center_pro",
    "batch41_commander_center_pro",
    "batch41_exit_pro",
]

def _read_app_text():
    return APP_FILE.read_text(encoding="utf-8")

def function_def_map():
    tree = ast.parse(_read_app_text())
    defs = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            defs.setdefault(node.name, []).append(node.lineno)
    return defs

def duplicate_functions():
    defs = function_def_map()
    return {name: lines for name, lines in defs.items() if len(lines) > 1}

def import_status():
    rows = []
    ok = 0
    critical = [x for x in CRITICAL_IMPORTS if x]
    for mod in critical:
        try:
            importlib.import_module(mod)
            rows.append((mod, True, "OK"))
            ok += 1
        except Exception as e:
            rows.append((mod, False, str(e)))
    return {
        "ok": ok,
        "total": len(critical),
        "rows": rows,
    }

def handler_status():
    defs = function_def_map()
    rows = []
    ok = 0
    for name in BATCH_HANDLER_NAMES:
        present = name in defs
        rows.append((name, present, defs.get(name, [])))
        if present:
            ok += 1
    return {
        "ok": ok,
        "total": len(BATCH_HANDLER_NAMES),
        "rows": rows,
    }

def menu_patch_status():
    text = _read_app_text()
    checks = {
        "1->batch34": "batch34_scan_hub()",
        "6->batch35": "batch35_command_center_pro()",
        "11->batch36": "batch36_operator_profiles_pro()",
        "16->batch37": "batch37_history_local_pro()",
        "21->batch38": "batch38_watchlist_view_pro()",
        "26->batch39": "batch39_automation_center_pro()",
        "31->batch40": "batch40_argus_center_pro()",
        "36->batch41": "batch41_oracle_center_pro()",
        "40->exit_pro": "if batch41_exit_pro():",
    }
    ok = 0
    rows = []
    for label, snippet in checks.items():
        present = snippet in text
        rows.append((label, present, snippet))
        if present:
            ok += 1
    return {
        "ok": ok,
        "total": len(checks),
        "rows": rows,
    }

def build_stableplus_report():
    imports = import_status()
    handlers = handler_status()
    dups = duplicate_functions()
    menu = menu_patch_status()

    if imports["ok"] == imports["total"] and handlers["ok"] == handlers["total"] and menu["ok"] == menu["total"]:
        status = "STABLE+ OK"
    elif imports["ok"] >= max(1, imports["total"] - 1) and handlers["ok"] >= max(1, handlers["total"] - 2):
        status = "STABLE+ WARN"
    else:
        status = "STABLE+ FAIL"

    return {
        "status": status,
        "imports_ok": imports["ok"],
        "imports_total": imports["total"],
        "handlers_ok": handlers["ok"],
        "handlers_total": handlers["total"],
        "menu_ok": menu["ok"],
        "menu_total": menu["total"],
        "duplicate_count": len(dups),
        "duplicates": dups,
        "imports": imports["rows"],
        "handlers": handlers["rows"],
        "menu": menu["rows"],
    }

def stableplus_lines(report):
    lines = [
        f"Status: {report.get('status', 'STABLE+ WARN')}",
        f"Imports: {report.get('imports_ok', 0)}/{report.get('imports_total', 0)}",
        f"Handlers: {report.get('handlers_ok', 0)}/{report.get('handlers_total', 0)}",
        f"Menu patches: {report.get('menu_ok', 0)}/{report.get('menu_total', 0)}",
        f"Duplicate functions: {report.get('duplicate_count', 0)}",
        "",
        "Duplicates:",
    ]

    dups = report.get("duplicates", {})
    if dups:
        for name, lines_no in sorted(dups.items()):
            lines.append(f"- {name}: lignes {', '.join(str(x) for x in lines_no)}")
    else:
        lines.append("- none")

    return lines
