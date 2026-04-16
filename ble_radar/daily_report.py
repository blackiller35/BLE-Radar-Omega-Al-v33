from datetime import datetime
import json

from ble_radar.config import HISTORY_DIR
from ble_radar.state import load_scan_history
from ble_radar.eventlog import read_events
from ble_radar.nexus import daily_change_summary, persistence_rankings

DAILY_DIR = HISTORY_DIR / "daily_reports"
DAILY_DIR.mkdir(parents=True, exist_ok=True)


def build_daily_report(history=None):
    if history is None:
        history = load_scan_history()

    summary = daily_change_summary(history)
    date_key = summary.get("date", "-")

    events = [e for e in read_events(300) if str(e.get("ts", "")).startswith(date_key)]
    persistent = [r for r in persistence_rankings(history, 50) if str(r.get("last_seen", "")).startswith(date_key)][:10]

    return {
        "date": date_key,
        "summary": summary,
        "events": events[:50],
        "persistent_today": persistent,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def daily_report_lines(report: dict):
    s = report.get("summary", {})
    lines = [
        f"Date: {report.get('date', '-')}",
        f"Généré: {report.get('generated_at', '-')}",
        f"Scans: {s.get('scans_today', 0)}",
        f"Appareils uniques: {s.get('unique_devices_today', 0)}",
        f"Nouveaux vs précédent: {s.get('new_vs_previous_scan', 0)}",
        f"Trackers: {s.get('trackers_today', 0)}",
        f"Watch hits: {s.get('watch_hits_today', 0)}",
        f"Critiques: {s.get('critical_today', 0)}",
        f"Élevés: {s.get('high_today', 0)}",
        "",
        "Appareils persistants du jour:",
    ]

    persistent = report.get("persistent_today", [])
    if persistent:
        for row in persistent:
            lines.append(
                f"- {row['name']} | {row['address']} | persist={row['persistence_score']} | "
                f"occ={row['occurrences']} | patterns={', '.join(row['patterns']) if row['patterns'] else '-'}"
            )
    else:
        lines.append("- aucun")

    lines.append("")
    lines.append("Événements du jour:")
    events = report.get("events", [])
    if events:
        for e in events[:12]:
            lines.append(f"- [{e.get('ts','-')}] {e.get('level','-').upper()} | {e.get('message','-')}")
    else:
        lines.append("- aucun")

    return lines


def save_daily_report(report=None):
    if report is None:
        report = build_daily_report()

    date_key = report.get("date", datetime.now().strftime("%Y-%m-%d"))
    json_path = DAILY_DIR / f"daily_report_{date_key}.json"
    txt_path = DAILY_DIR / f"daily_report_{date_key}.txt"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    txt_path.write_text("\n".join(daily_report_lines(report)), encoding="utf-8")

    return {
        "report": report,
        "json": json_path,
        "txt": txt_path,
    }
