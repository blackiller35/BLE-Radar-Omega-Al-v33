from datetime import datetime
import json

from ble_radar.config import HISTORY_DIR
from ble_radar.argus import rank_priority

WATCH_DIR = HISTORY_DIR / "watch_sessions"
WATCH_DIR.mkdir(parents=True, exist_ok=True)


def _severity(alert: str) -> int:
    return {
        "faible": 0,
        "moyen": 1,
        "élevé": 2,
        "critique": 3,
    }.get(str(alert or "faible"), 0)


def _previous_priority_index(previous_devices, history=None):
    rows = rank_priority(previous_devices or [], history, 500)
    return {
        str(r["device"].get("address", "-")).upper(): r
        for r in rows
    }


def escalation_rows(devices, previous_devices=None, history=None, limit=20):
    if not previous_devices:
        return []

    previous = _previous_priority_index(previous_devices, history)
    current = rank_priority(devices, history, 500)

    rows = []
    for row in current:
        addr = str(row["device"].get("address", "-")).upper()
        prev = previous.get(addr)
        if not prev:
            continue

        curr_score = int(row.get("priority_score", 0))
        prev_score = int(prev.get("priority_score", 0))
        curr_alert = row["device"].get("alert_level", "faible")
        prev_alert = prev["device"].get("alert_level", "faible")

        reasons = []
        delta = curr_score - prev_score

        if delta >= 12:
            reasons.append(f"priority +{delta}")
        if _severity(curr_alert) > _severity(prev_alert):
            reasons.append(f"alerte {prev_alert}->{curr_alert}")
        if row["device"].get("watch_hit") and not prev["device"].get("watch_hit"):
            reasons.append("nouveau watch hit")
        if row["device"].get("possible_suivi") and not prev["device"].get("possible_suivi"):
            reasons.append("nouveau signal de suivi")
        if row["behavior"].get("anomaly_score", 0) >= prev["behavior"].get("anomaly_score", 0) + 10:
            reasons.append("anomalie comportementale en hausse")

        if reasons:
            rows.append({
                "current": row,
                "previous": prev,
                "delta": delta,
                "reasons": reasons,
            })

    rows.sort(
        key=lambda x: (
            x["current"]["priority_score"],
            x["delta"],
            x["current"]["behavior"].get("anomaly_score", 0),
        ),
        reverse=True,
    )
    return rows[:limit]


def build_campaigns(devices, history=None, limit=10):
    rows = rank_priority(devices, history, 200)
    groups = {}

    for row in rows:
        d = row["device"]
        trust = row.get("trust_label", "unknown")
        if trust not in ("suspicious", "critical") and row["priority_score"] < 55:
            continue

        vendor = d.get("vendor", "Unknown")
        profile = d.get("profile", "general_ble")
        key = f"{vendor} | {profile}"

        grp = groups.setdefault(key, {
            "key": key,
            "vendor": vendor,
            "profile": profile,
            "devices": [],
            "max_priority": 0,
            "watch_hits": 0,
            "trackers": 0,
        })

        grp["devices"].append({
            "name": d.get("name", "Inconnu"),
            "address": d.get("address", "-"),
            "priority_score": row["priority_score"],
            "trust_label": row["trust_label"],
            "alert_level": d.get("alert_level", "faible"),
        })
        grp["max_priority"] = max(grp["max_priority"], row["priority_score"])
        if d.get("watch_hit"):
            grp["watch_hits"] += 1
        if d.get("profile") == "tracker_probable" or d.get("possible_suivi"):
            grp["trackers"] += 1

    out = list(groups.values())
    out = [g for g in out if len(g["devices"]) >= 2 or g["watch_hits"] >= 1 or g["trackers"] >= 2]
    out.sort(
        key=lambda g: (
            len(g["devices"]),
            g["watch_hits"],
            g["trackers"],
            g["max_priority"],
        ),
        reverse=True,
    )
    return out[:limit]


def classify_threat(report: dict):
    critical = int(report.get("critical_count", 0))
    high = int(report.get("high_count", 0))
    watch_hits = int(report.get("watch_hits", 0))
    trackers = int(report.get("tracker_count", 0))
    escalations = len(report.get("escalations", []))
    campaigns = len(report.get("campaigns", []))
    top_priority = int(report.get("top_priority", 0))

    if watch_hits >= 1 or critical >= 1 or top_priority >= 85:
        return "menace_active"
    if escalations >= 2 or trackers >= 2 or campaigns >= 1 or high >= 2:
        return "incident_probable"
    if high >= 1 or trackers >= 1 or escalations >= 1 or top_priority >= 55:
        return "vigilance"
    return "bruit_normal"


def build_sentinel_report(devices, previous_devices=None, history=None):
    ranked = rank_priority(devices, history, 50)
    escalations = escalation_rows(devices, previous_devices, history, 20)
    campaigns = build_campaigns(devices, history, 10)

    critical_count = sum(1 for d in devices if d.get("alert_level") == "critique")
    high_count = sum(1 for d in devices if d.get("alert_level") == "élevé")
    tracker_count = sum(
        1 for d in devices
        if d.get("profile") == "tracker_probable"
        or d.get("possible_suivi")
        or d.get("watch_hit")
    )
    watch_hits = sum(1 for d in devices if d.get("watch_hit"))
    top_priority = ranked[0]["priority_score"] if ranked else 0

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "top_priority": top_priority,
        "critical_count": critical_count,
        "high_count": high_count,
        "tracker_count": tracker_count,
        "watch_hits": watch_hits,
        "escalations": escalations,
        "campaigns": campaigns,
        "ranked": ranked[:10],
    }
    report["threat_state"] = classify_threat(report)
    return report


def sentinel_lines(report: dict):
    lines = [
        f"Généré: {report.get('generated_at', '-')}",
        f"Threat state: {report.get('threat_state', 'bruit_normal')}",
        f"Top priority: {report.get('top_priority', 0)}",
        f"Critiques: {report.get('critical_count', 0)}",
        f"Élevés: {report.get('high_count', 0)}",
        f"Trackers: {report.get('tracker_count', 0)}",
        f"Watch hits: {report.get('watch_hits', 0)}",
        f"Escalades: {len(report.get('escalations', []))}",
        f"Campaigns: {len(report.get('campaigns', []))}",
        "",
        "Top cibles:",
    ]

    ranked = report.get("ranked", [])
    if ranked:
        for row in ranked[:5]:
            d = row["device"]
            lines.append(
                f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
                f"priority={row['priority_score']} | trust={row['trust_label']} | "
                f"alert={d.get('alert_level','faible')}"
            )
    else:
        lines.append("- aucune")

    lines.append("")
    lines.append("Escalades:")
    escalations = report.get("escalations", [])
    if escalations:
        for row in escalations[:5]:
            d = row["current"]["device"]
            lines.append(
                f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
                f"delta={row['delta']} | {', '.join(row['reasons'])}"
            )
    else:
        lines.append("- aucune")

    return lines


def save_watch_session(report: dict):
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    json_path = WATCH_DIR / f"watch_session_{stamp}.json"
    txt_path = WATCH_DIR / f"watch_session_{stamp}.txt"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    txt_path.write_text("\n".join(sentinel_lines(report)), encoding="utf-8")

    return {
        "json": json_path,
        "txt": txt_path,
        "report": report,
    }
