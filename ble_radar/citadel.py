from datetime import datetime
from pathlib import Path
import json
import zipfile

from ble_radar.config import HISTORY_DIR
from ble_radar.doctor import build_doctor_report
from ble_radar.fortress import integrity_status_label, quick_repair_json
from ble_radar.snapshots import list_snapshots, create_snapshot
from ble_radar.eventlog import read_events
from ble_radar.nebula import load_casebook

ROOT = Path(__file__).resolve().parent.parent
CITADEL_DIR = HISTORY_DIR / "citadel"
EXPORT_DIR = CITADEL_DIR / "exports"
INCIDENT_DIR = CITADEL_DIR / "incident_packs"
REPORT_DIR = CITADEL_DIR / "reports"

for d in (CITADEL_DIR, EXPORT_DIR, INCIDENT_DIR, REPORT_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _stamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _latest_files(path: Path, limit: int = 10):
    if not path.exists():
        return []
    files = [p for p in path.rglob("*") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


def _zip_paths(output_path: Path, paths: list[Path]):
    count = 0
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in paths:
            if not item.exists():
                continue

            if item.is_file():
                zf.write(item, arcname=str(item.relative_to(ROOT)))
                count += 1
            else:
                for sub in item.rglob("*"):
                    if sub.is_file():
                        zf.write(sub, arcname=str(sub.relative_to(ROOT)))
                        count += 1
    return count


def build_citadel_report():
    doctor = build_doctor_report()
    snapshots = list_snapshots()
    casebook = load_casebook()
    cases = casebook.get("cases", [])
    open_cases = sum(1 for c in cases if c.get("status", "open") == "open")

    events = read_events(500)
    reports_count = len(_latest_files(ROOT / "reports", 200))
    incidents_count = len(_latest_files(ROOT / "history" / "incidents", 200))
    watch_sessions_count = len(_latest_files(ROOT / "history" / "watch_sessions", 200))
    daily_reports_count = len(_latest_files(ROOT / "history" / "daily_reports", 200))
    nebula_sessions_count = len(_latest_files(ROOT / "history" / "nebula_sessions", 200))

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fortress": integrity_status_label(),
        "doctor": {
            "files_ok": doctor["files_ok"],
            "files_total": doctor["files_total"],
            "imports_ok": doctor["imports_ok"],
            "imports_total": doctor["imports_total"],
            "json_ok": doctor["json_ok"],
            "json_total": doctor["json_total"],
        },
        "snapshots": len(snapshots),
        "events_recent": len(events),
        "reports_count": reports_count,
        "incidents_count": incidents_count,
        "watch_sessions_count": watch_sessions_count,
        "daily_reports_count": daily_reports_count,
        "nebula_sessions_count": nebula_sessions_count,
        "casebook_total": len(cases),
        "casebook_open": open_cases,
    }


def citadel_lines(report: dict):
    return [
        f"Généré: {report.get('generated_at', '-')}",
        f"FORTRESS: {report.get('fortress', '-')}",
        f"Fichiers: {report.get('doctor', {}).get('files_ok', 0)}/{report.get('doctor', {}).get('files_total', 0)}",
        f"Imports: {report.get('doctor', {}).get('imports_ok', 0)}/{report.get('doctor', {}).get('imports_total', 0)}",
        f"JSON: {report.get('doctor', {}).get('json_ok', 0)}/{report.get('doctor', {}).get('json_total', 0)}",
        f"Snapshots: {report.get('snapshots', 0)}",
        f"Événements récents: {report.get('events_recent', 0)}",
        f"Rapports: {report.get('reports_count', 0)}",
        f"Incidents: {report.get('incidents_count', 0)}",
        f"Watch sessions: {report.get('watch_sessions_count', 0)}",
        f"Daily reports: {report.get('daily_reports_count', 0)}",
        f"NEBULA sessions: {report.get('nebula_sessions_count', 0)}",
        f"Cases total: {report.get('casebook_total', 0)}",
        f"Cases open: {report.get('casebook_open', 0)}",
    ]


def save_citadel_report(report=None):
    if report is None:
        report = build_citadel_report()

    stamp = _stamp()
    json_path = REPORT_DIR / f"citadel_report_{stamp}.json"
    txt_path = REPORT_DIR / f"citadel_report_{stamp}.txt"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    txt_path.write_text("\n".join(citadel_lines(report)), encoding="utf-8")

    return {
        "report": report,
        "json": json_path,
        "txt": txt_path,
    }


def export_global_bundle(include_snapshots=True):
    stamp = _stamp()
    out = EXPORT_DIR / f"ble_radar_omega_global_{stamp}.zip"

    items = [
        ROOT / "ble_radar",
        ROOT / "state",
        ROOT / "history",
        ROOT / "reports",
        ROOT / "main.py",
        ROOT / "requirements.txt",
    ]
    if include_snapshots:
        items.append(ROOT / "snapshots")

    count = _zip_paths(out, items)
    return {
        "zip": out,
        "files": count,
    }


def export_incident_pack():
    stamp = _stamp()
    out = INCIDENT_DIR / f"ble_radar_omega_incident_pack_{stamp}.zip"

    items = []
    items.extend(_latest_files(ROOT / "reports", 12))
    items.extend(_latest_files(ROOT / "history" / "incidents", 12))
    items.extend(_latest_files(ROOT / "history" / "watch_sessions", 10))
    items.extend(_latest_files(ROOT / "history" / "daily_reports", 10))
    items.extend(_latest_files(ROOT / "history" / "nebula_sessions", 10))
    items.extend(_latest_files(REPORT_DIR, 6))
    items.extend([
        ROOT / "state" / "last_scan.json",
        ROOT / "history" / "scan_history.json",
        ROOT / "state" / "device_knowledge.json",
        ROOT / "state" / "nebula_casebook.json",
    ])

    count = _zip_paths(out, items)
    return {
        "zip": out,
        "files": count,
    }


def run_maintenance_cycle():
    repaired = quick_repair_json()
    snapshot = create_snapshot()
    report = build_citadel_report()
    saved = save_citadel_report(report)

    return {
        "repaired": repaired,
        "snapshot": snapshot,
        "saved_report": saved,
        "report": report,
    }
