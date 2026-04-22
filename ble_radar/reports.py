import csv
import json
from datetime import datetime
from pathlib import Path

from ble_radar.config import REPORTS_DIR, HISTORY_DIR
from ble_radar.dashboard import render_dashboard_html
from ble_radar.device_contract import explain_device
from ble_radar.operator_panel import render_operator_panel_html
from ble_radar.state import append_scan_history, build_trends


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def save_json(devices: list[dict], stamp: str) -> Path:
    path = REPORTS_DIR / f"scan_{stamp}.json"
    path.write_text(json.dumps(devices, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def save_csv(devices: list[dict], stamp: str) -> Path:
    path = REPORTS_DIR / f"scan_{stamp}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "name", "address", "vendor", "profile", "rssi",
            "risk_score", "follow_score", "confidence_score", "final_score",
            "score_explanation", "classification", "alert_level", "reason_short",
            "seen_count", "near_count", "possible_suivi",
            "persistent_nearby", "whitelisted", "watched",
            "watch_hit", "random_mac", "apple_prefix", "is_new_device",
        ])
        for d in devices:
            writer.writerow([
                d.get("name", ""),
                d.get("address", ""),
                d.get("vendor", ""),
                d.get("profile", ""),
                d.get("rssi", ""),
                d.get("risk_score", 0),
                d.get("follow_score", 0),
                d.get("confidence_score", 0),
                d.get("final_score", 0),
                explain_device(d)["summary"],
                d.get("classification", ""),
                d.get("alert_level", ""),
                d.get("reason_short", ""),
                d.get("seen_count", 0),
                d.get("near_count", 0),
                d.get("possible_suivi", False),
                d.get("persistent_nearby", False),
                d.get("whitelisted", False),
                d.get("watched", False),
                d.get("watch_hit", False),
                d.get("random_mac", False),
                d.get("apple_prefix", False),
                d.get("is_new_device", False),
            ])
    return path


def save_txt(devices: list[dict], stamp: str) -> Path:
    path = REPORTS_DIR / f"scan_{stamp}.txt"

    critical = [d for d in devices if d.get("alert_level") == "critique"]
    high = [d for d in devices if d.get("alert_level") == "élevé"]
    medium = [d for d in devices if d.get("alert_level") == "moyen"]
    trackers = [d for d in devices if d.get("possible_suivi") or d.get("watch_hit")]

    lines = [
        f"Scan BLE - {stamp}",
        "",
        f"Total devices: {len(devices)}",
        f"Critiques: {len(critical)}",
        f"Élevés: {len(high)}",
        f"Moyens: {len(medium)}",
        f"Trackers probables: {len(trackers)}",
        "",
        "Résumé exécutif:",
    ]

    hot = sorted(devices, key=lambda x: x.get("final_score", 0), reverse=True)[:10]
    if hot:
        for d in hot:
            lines.append(
                f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
                f"{d.get('vendor','Unknown')} | profile={d.get('profile','-')} | "
                f"final={d.get('final_score',0)} | {d.get('alert_level','faible')}"
            )
    else:
        lines.append("- Aucun appareil analysé.")

    lines.append("")
    lines.append("Détails:")
    for d in devices:
        lines.append(
            f"{d.get('name','Inconnu')} | {d.get('address','-')} | {d.get('vendor','Unknown')} | "
            f"profile:{d.get('profile','-')} | RSSI:{d.get('rssi','-')} | "
            f"risk:{d.get('risk_score',0)} | follow:{d.get('follow_score',0)} | "
            f"confidence:{d.get('confidence_score',0)} | final:{d.get('final_score',0)} | "
            f"alert:{d.get('alert_level','faible')} | seen:{d.get('seen_count',0)} | "
            f"{d.get('reason_short','normal')} | explication:{explain_device(d)['summary']}"
        )

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def save_html(devices: list[dict], stamp: str) -> Path:
    path = REPORTS_DIR / f"scan_{stamp}.html"
    html = render_dashboard_html(devices, stamp)
    path.write_text(html, encoding="utf-8")
    return path


def build_operator_panel_events(devices: list[dict]) -> list[dict]:
    ranked = sorted(
        devices,
        key=lambda x: x.get("final_score", x.get("risk_score", 0)),
        reverse=True,
    )

    events: list[dict] = []

    for d in ranked[:12]:
        name = d.get("name", "Inconnu")
        address = d.get("address", "-")
        score = int(d.get("final_score", d.get("risk_score", 0)) or 0)
        alert_level = str(d.get("alert_level", "")).lower()

        severity = "low"
        if alert_level == "critique" or score >= 85:
            severity = "critical"
        elif alert_level == "élevé" or score >= 65:
            severity = "high"
        elif alert_level == "moyen" or score >= 35:
            severity = "medium"

        reasons = []
        if d.get("watch_hit"):
            reasons.append("watchlist hit")
        if d.get("possible_suivi"):
            reasons.append("possible tracking")
        if d.get("persistent_nearby"):
            reasons.append("persistent nearby")
        if d.get("reason_short"):
            reasons.append(str(d.get("reason_short")))

        message = " | ".join(reasons[:3]).strip()
        if not message:
            message = explain_device(d)["summary"]

        if severity == "low" and not (
            d.get("watch_hit")
            or d.get("possible_suivi")
            or d.get("persistent_nearby")
        ):
            continue

        events.append(
            {
                "severity": severity,
                "title": f"{name} ({address})",
                "message": message,
            }
        )

    return events[:10]


def save_operator_panel_html(devices: list[dict], stamp: str) -> Path:
    path = REPORTS_DIR / f"operator_panel_{stamp}.html"
    html = render_operator_panel_html(
        devices,
        stamp,
        events=build_operator_panel_events(devices),
    )
    path.write_text(html, encoding="utf-8")
    return path


def save_executive_summary(devices: list[dict], stamp: str) -> Path:
    path = HISTORY_DIR / f"executive_summary_{stamp}.json"
    data = {
        "stamp": stamp,
        "total": len(devices),
        "critical": [d for d in devices if d.get("alert_level") == "critique"][:10],
        "high": [d for d in devices if d.get("alert_level") == "élevé"][:10],
        "trackers": [d for d in devices if d.get("possible_suivi") or d.get("watch_hit")][:10],
        "top_hot": sorted(devices, key=lambda x: x.get("final_score", 0), reverse=True)[:10],
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def save_all_reports(devices: list[dict]) -> dict:
    stamp = now_stamp()
    json_path = save_json(devices, stamp)
    csv_path = save_csv(devices, stamp)
    txt_path = save_txt(devices, stamp)
    html_path = save_html(devices, stamp)
    operator_panel_html_path = save_operator_panel_html(devices, stamp)
    history_path = append_scan_history(devices, stamp)
    trends = build_trends()
    summary_path = save_executive_summary(devices, stamp)

    return {
        "stamp": stamp,
        "json": json_path,
        "csv": csv_path,
        "txt": txt_path,
        "html": html_path,
        "operator_panel_html": operator_panel_html_path,
        "history": history_path,
        "summary": summary_path,
        "trends": trends,
    }
