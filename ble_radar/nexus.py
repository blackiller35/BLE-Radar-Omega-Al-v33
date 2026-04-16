from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import json
import unicodedata

from ble_radar.config import HISTORY_DIR
from ble_radar.state import load_scan_history

INCIDENTS_DIR = HISTORY_DIR / "incidents"
INCIDENTS_DIR.mkdir(parents=True, exist_ok=True)


def _norm(text) -> str:
    text = str(text or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def _parse_stamp(stamp: str):
    if not stamp:
        return None
    for fmt in ("%Y-%m-%d_%H-%M-%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(stamp, fmt)
        except Exception:
            pass
    return None


def _severity_value(alert: str) -> int:
    return {
        "faible": 0,
        "moyen": 1,
        "élevé": 2,
        "critique": 3,
    }.get(str(alert or "faible"), 0)


def _occurrence_index(history=None):
    if history is None:
        history = load_scan_history()

    index = defaultdict(list)

    for scan in history:
        stamp = scan.get("stamp") or scan.get("timestamp") or "-"
        dt = _parse_stamp(stamp)

        for d in scan.get("devices", []):
            addr = str(d.get("address", "-")).upper()
            if not addr or addr == "-":
                continue

            index[addr].append({
                "stamp": stamp,
                "dt": dt,
                "name": d.get("name", "Inconnu"),
                "address": addr,
                "vendor": d.get("vendor", "Unknown"),
                "profile": d.get("profile", "general_ble"),
                "alert_level": d.get("alert_level", "faible"),
                "final_score": d.get("final_score", d.get("score", 0)),
                "rssi": d.get("rssi", -100),
                "watch_hit": d.get("watch_hit", False),
                "possible_suivi": d.get("possible_suivi", False),
                "persistent_nearby": d.get("persistent_nearby", False),
                "random_mac": d.get("random_mac", False),
            })

    for addr in index:
        index[addr].sort(key=lambda x: (x["dt"] or datetime.min))
    return dict(index)


def _summary_for_occurrences(addr: str, occs: list[dict]):
    names = Counter(o["name"] for o in occs if o.get("name"))
    vendors = Counter(o["vendor"] for o in occs if o.get("vendor"))
    profiles = Counter(o["profile"] for o in occs if o.get("profile"))

    first_seen = occs[0]["stamp"] if occs else "-"
    last_seen = occs[-1]["stamp"] if occs else "-"

    unique_days = len({(o["dt"].date().isoformat() if o["dt"] else o["stamp"][:10]) for o in occs})
    near_hits = sum(1 for o in occs if o.get("persistent_nearby") or o.get("rssi", -100) > -70)
    watch_hits = sum(1 for o in occs if o.get("watch_hit"))
    tracker_hits = sum(1 for o in occs if o.get("possible_suivi") or o.get("profile") == "tracker_probable")
    random_hits = sum(1 for o in occs if o.get("random_mac"))
    alerts = sum(1 for o in occs if _severity_value(o.get("alert_level")) >= 1)
    max_score = max((int(o.get("final_score", 0)) for o in occs), default=0)
    avg_score = round(sum(int(o.get("final_score", 0)) for o in occs) / len(occs), 2) if occs else 0

    persistence_score = min(
        100,
        len(occs) * 4
        + unique_days * 9
        + near_hits * 5
        + tracker_hits * 8
        + watch_hits * 12
        + alerts * 4
        + (max_score // 5),
    )

    patterns = []
    if len(occs) >= 4:
        patterns.append("récurrent")
    if unique_days >= 2:
        patterns.append("multi-jours")
    if near_hits >= 2:
        patterns.append("proximité répétée")
    if alerts >= 2:
        patterns.append("alerte répétée")
    if watch_hits >= 1:
        patterns.append("watch hit")
    if tracker_hits >= 2:
        patterns.append("tracker probable")
    if random_hits >= 2:
        patterns.append("mac random récurrente")

    return {
        "address": addr,
        "name": names.most_common(1)[0][0] if names else "Inconnu",
        "vendor": vendors.most_common(1)[0][0] if vendors else "Unknown",
        "profile": profiles.most_common(1)[0][0] if profiles else "general_ble",
        "occurrences": len(occs),
        "unique_days": unique_days,
        "near_hits": near_hits,
        "watch_hits": watch_hits,
        "tracker_hits": tracker_hits,
        "random_hits": random_hits,
        "alerts": alerts,
        "max_score": max_score,
        "avg_score": avg_score,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "persistence_score": persistence_score,
        "patterns": patterns,
    }


def search_device_summaries(query: str, history=None, limit: int = 12):
    index = _occurrence_index(history)
    query_n = _norm(query)

    rows = []
    for addr, occs in index.items():
        s = _summary_for_occurrences(addr, occs)
        hay = " ".join([
            s["address"],
            s["name"],
            s["vendor"],
            s["profile"],
            " ".join(s["patterns"]),
        ])
        if not query_n or query_n in _norm(hay):
            rows.append(s)

    rows.sort(key=lambda x: (x["persistence_score"], x["occurrences"], x["max_score"]), reverse=True)
    return rows[:limit]


def timeline_for_address(address: str, history=None, limit: int = 80):
    index = _occurrence_index(history)
    occs = index.get(str(address or "").upper(), [])
    return occs[:limit]


def timeline_lines(summary: dict, timeline: list[dict], limit: int = 40):
    lines = [
        f"Adresse: {summary.get('address', '-')}",
        f"Nom: {summary.get('name', 'Inconnu')}",
        f"Vendor: {summary.get('vendor', 'Unknown')}",
        f"Profil: {summary.get('profile', 'general_ble')}",
        f"Occurrences: {summary.get('occurrences', 0)}",
        f"Jours uniques: {summary.get('unique_days', 0)}",
        f"Persistance: {summary.get('persistence_score', 0)}/100",
        f"Patterns: {', '.join(summary.get('patterns', [])) if summary.get('patterns') else '-'}",
        f"First seen: {summary.get('first_seen', '-')}",
        f"Last seen: {summary.get('last_seen', '-')}",
        "",
        "Timeline:",
    ]
    for row in timeline[:limit]:
        lines.append(
            f"- [{row.get('stamp','-')}] {row.get('name','Inconnu')} | "
            f"rssi={row.get('rssi', -100)} | "
            f"alert={row.get('alert_level','faible')} | "
            f"score={row.get('final_score', 0)} | "
            f"profile={row.get('profile','-')}"
        )
    return lines


def persistence_rankings(history=None, limit: int = 20):
    index = _occurrence_index(history)
    rows = [_summary_for_occurrences(addr, occs) for addr, occs in index.items()]
    rows.sort(key=lambda x: (x["persistence_score"], x["occurrences"], x["max_score"]), reverse=True)
    return rows[:limit]


def recurrent_pattern_rankings(history=None, limit: int = 20):
    rows = [r for r in persistence_rankings(history, 200) if r.get("patterns")]
    rows.sort(
        key=lambda x: (len(x["patterns"]), x["persistence_score"], x["occurrences"]),
        reverse=True,
    )
    return rows[:limit]


def daily_change_summary(history=None):
    if history is None:
        history = load_scan_history()
    if not history:
        return {
            "date": "-",
            "scans_today": 0,
            "unique_devices_today": 0,
            "new_vs_previous_scan": 0,
            "recurring_today": [],
            "trackers_today": 0,
            "watch_hits_today": 0,
            "critical_today": 0,
            "high_today": 0,
        }

    latest_stamp = history[-1].get("stamp") or history[-1].get("timestamp") or "-"
    latest_date = latest_stamp[:10]

    scans_today = [s for s in history if (s.get("stamp") or s.get("timestamp") or "").startswith(latest_date)]

    all_today = []
    for scan in scans_today:
        all_today.extend(scan.get("devices", []))

    unique_addrs_today = {
        str(d.get("address", "-")).upper()
        for d in all_today
        if str(d.get("address", "-")).upper() != "-"
    }

    recurring_counter = Counter(
        str(d.get("address", "-")).upper()
        for d in all_today
        if str(d.get("address", "-")).upper() != "-"
    )

    recurring_today = [
        {"address": addr, "count": count}
        for addr, count in recurring_counter.items()
        if count >= 2
    ]
    recurring_today.sort(key=lambda x: x["count"], reverse=True)

    new_vs_previous = 0
    if len(history) >= 2:
        prev = {
            str(d.get("address", "-")).upper()
            for d in history[-2].get("devices", [])
            if str(d.get("address", "-")).upper() != "-"
        }
        curr = {
            str(d.get("address", "-")).upper()
            for d in history[-1].get("devices", [])
            if str(d.get("address", "-")).upper() != "-"
        }
        new_vs_previous = len(curr - prev)

    trackers_today = sum(
        1 for d in all_today
        if d.get("profile") == "tracker_probable"
        or d.get("possible_suivi")
        or d.get("watch_hit")
    )
    watch_hits_today = sum(1 for d in all_today if d.get("watch_hit"))
    critical_today = sum(1 for d in all_today if d.get("alert_level") == "critique")
    high_today = sum(1 for d in all_today if d.get("alert_level") == "élevé")

    return {
        "date": latest_date,
        "scans_today": len(scans_today),
        "unique_devices_today": len(unique_addrs_today),
        "new_vs_previous_scan": new_vs_previous,
        "recurring_today": recurring_today[:10],
        "trackers_today": trackers_today,
        "watch_hits_today": watch_hits_today,
        "critical_today": critical_today,
        "high_today": high_today,
    }


def daily_change_lines(summary: dict):
    lines = [
        f"Date: {summary.get('date', '-')}",
        f"Scans aujourd'hui: {summary.get('scans_today', 0)}",
        f"Appareils uniques aujourd'hui: {summary.get('unique_devices_today', 0)}",
        f"Nouveaux vs scan précédent: {summary.get('new_vs_previous_scan', 0)}",
        f"Trackers aujourd'hui: {summary.get('trackers_today', 0)}",
        f"Watch hits aujourd'hui: {summary.get('watch_hits_today', 0)}",
        f"Critiques aujourd'hui: {summary.get('critical_today', 0)}",
        f"Élevés aujourd'hui: {summary.get('high_today', 0)}",
        "",
        "Récurrents aujourd'hui:",
    ]
    recurring = summary.get("recurring_today", [])
    if recurring:
        for row in recurring:
            lines.append(f"- {row['address']} | apparitions={row['count']}")
    else:
        lines.append("- aucun")
    return lines


def build_enriched_incident(devices, history=None):
    if history is None:
        history = load_scan_history()

    persistent = {r["address"]: r for r in persistence_rankings(history, 200)}
    hot = sorted(devices, key=lambda d: d.get("final_score", d.get("score", 0)), reverse=True)[:15]

    findings = []
    for d in hot:
        addr = str(d.get("address", "-")).upper()
        p = persistent.get(addr, {})
        findings.append({
            "address": addr,
            "name": d.get("name", "Inconnu"),
            "vendor": d.get("vendor", "Unknown"),
            "profile": d.get("profile", "general_ble"),
            "alert_level": d.get("alert_level", "faible"),
            "final_score": d.get("final_score", d.get("score", 0)),
            "persistence_score": p.get("persistence_score", 0),
            "occurrences": p.get("occurrences", 0),
            "unique_days": p.get("unique_days", 0),
            "patterns": p.get("patterns", []),
        })

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "findings": findings,
    }


def incident_lines(report: dict):
    lines = [
        f"Généré: {report.get('generated_at', '-')}",
        "Findings:",
    ]
    for f in report.get("findings", [])[:12]:
        lines.append(
            f"- {f['name']} | {f['address']} | vendor={f['vendor']} | "
            f"alert={f['alert_level']} | final={f['final_score']} | "
            f"persist={f['persistence_score']} | occ={f['occurrences']} | "
            f"patterns={', '.join(f['patterns']) if f['patterns'] else '-'}"
        )
    return lines


def save_enriched_incident(devices, history=None):
    report = build_enriched_incident(devices, history)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    json_path = INCIDENTS_DIR / f"incident_enriched_{stamp}.json"
    txt_path = INCIDENTS_DIR / f"incident_enriched_{stamp}.txt"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    txt_path.write_text("\n".join(incident_lines(report)), encoding="utf-8")

    return {
        "report": report,
        "json": json_path,
        "txt": txt_path,
    }
