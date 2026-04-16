import json
from datetime import datetime
from pathlib import Path

from ble_radar.config import REPORTS_DIR, HISTORY_DIR
from ble_radar.intel import get_vendor_summary, get_tracker_candidates


def audit_stamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def build_audit_package(devices, comparison=None):
    critical = [d for d in devices if d.get("alert_level") == "critique"]
    high = [d for d in devices if d.get("alert_level") == "élevé"]
    medium = [d for d in devices if d.get("alert_level") == "moyen"]
    trackers = get_tracker_candidates(devices)
    vendors = get_vendor_summary(devices)

    return {
        "summary": {
            "total": len(devices),
            "critical": len(critical),
            "high": len(high),
            "medium": len(medium),
            "trackers": len(trackers),
            "vendors": vendors[:10],
            "comparison": {
                "added": len(comparison.get("added", [])) if comparison else 0,
                "removed": len(comparison.get("removed", [])) if comparison else 0,
                "common": len(comparison.get("common", [])) if comparison else 0,
            },
        },
        "top_hot": sorted(devices, key=lambda d: d.get("final_score", d.get("score", 0)), reverse=True)[:15],
        "top_trackers": trackers[:15],
    }


def save_audit_package(package, stamp=None):
    if stamp is None:
        stamp = audit_stamp()

    json_path = REPORTS_DIR / f"audit_{stamp}.json"
    txt_path = HISTORY_DIR / f"audit_{stamp}.txt"

    json_path.write_text(json.dumps(package, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        f"AUDIT - {stamp}",
        "",
        f"Total: {package['summary']['total']}",
        f"Critical: {package['summary']['critical']}",
        f"High: {package['summary']['high']}",
        f"Medium: {package['summary']['medium']}",
        f"Trackers: {package['summary']['trackers']}",
        "",
        "Top hot:",
    ]

    for d in package["top_hot"][:10]:
        lines.append(
            f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
            f"{d.get('vendor','Unknown')} | final={d.get('final_score',0)} | "
            f"{d.get('alert_level','faible')}"
        )

    lines.append("")
    lines.append("Top trackers:")
    for d in package["top_trackers"][:10]:
        lines.append(
            f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
            f"profile={d.get('profile','-')} | follow={d.get('follow_score',0)}"
        )

    txt_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "json": json_path,
        "txt": txt_path,
        "stamp": stamp,
    }
