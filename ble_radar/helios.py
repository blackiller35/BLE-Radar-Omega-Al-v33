from ble_radar.state import load_scan_history
from ble_radar.argus import rank_priority, argus_recommended_actions
from ble_radar.sentinel import build_sentinel_report
from ble_radar.atlas import atlas_snapshot
from ble_radar.nexus import daily_change_summary
from ble_radar.knowledge import top_known_devices


def _previous_devices_from_history(history):
    if history and len(history) >= 2:
        return history[-2].get("devices", [])
    return []


def _focus_from_state(threat_state: str, top_priority: int):
    if threat_state == "menace_active":
        return "agir immédiatement"
    if threat_state == "incident_probable":
        return "investigation prioritaire"
    if threat_state == "vigilance":
        return "surveillance renforcée"
    if top_priority >= 55:
        return "surveiller les cibles chaudes"
    return "surveillance normale"


def _merged_recommendations(ranked_rows, sentinel_report, daily_summary):
    recs = []

    recs.extend(argus_recommended_actions(ranked_rows))

    threat_state = sentinel_report.get("threat_state", "bruit_normal")
    if threat_state == "menace_active":
        recs.append("Passer immédiatement en mode investigation / SENTINEL.")
    elif threat_state == "incident_probable":
        recs.append("Vérifier les escalades et les campaigns dans SENTINEL.")
    elif threat_state == "vigilance":
        recs.append("Maintenir une vigilance renforcée sur les cibles prioritaires.")

    if daily_summary.get("watch_hits_today", 0) >= 1:
        recs.append("Un watch hit a été vu aujourd'hui: vérifier la watchlist et exporter un incident enrichi.")
    if daily_summary.get("trackers_today", 0) >= 2:
        recs.append("Plusieurs trackers aujourd'hui: ouvrir Tracker Lab et NEXUS.")
    if daily_summary.get("new_vs_previous_scan", 0) >= 3:
        recs.append("Beaucoup de nouveaux appareils vs précédent: vérifier les vues tactiques.")

    dedup = []
    seen = set()
    for r in recs:
        key = r.strip().lower()
        if key and key not in seen:
            seen.add(key)
            dedup.append(r)

    return dedup[:10]


def build_helios_report(devices, history=None):
    if history is None:
        history = load_scan_history()

    previous_devices = _previous_devices_from_history(history)
    ranked = rank_priority(devices, history, 20)
    sentinel = build_sentinel_report(devices, previous_devices, history)
    atlas = atlas_snapshot(devices, history)
    daily = daily_change_summary(history)
    known = top_known_devices(10)

    immediate_targets = []
    for row in ranked[:10]:
        d = row["device"]
        if (
            row["priority_score"] >= 60
            or d.get("watch_hit")
            or d.get("alert_level") in ("élevé", "critique")
        ):
            immediate_targets.append({
                "name": d.get("name", "Inconnu"),
                "address": d.get("address", "-"),
                "priority_score": row["priority_score"],
                "trust_label": row["trust_label"],
                "alert_level": d.get("alert_level", "faible"),
                "reasons": row.get("reasons", []),
            })

    threat_state = sentinel.get("threat_state", "bruit_normal")
    top_priority = sentinel.get("top_priority", 0)
    focus = _focus_from_state(threat_state, top_priority)

    report = {
        "threat_state": threat_state,
        "focus": focus,
        "top_priority": top_priority,
        "critical_count": sentinel.get("critical_count", 0),
        "high_count": sentinel.get("high_count", 0),
        "tracker_count": sentinel.get("tracker_count", 0),
        "watch_hits": sentinel.get("watch_hits", 0),
        "escalations": len(sentinel.get("escalations", [])),
        "campaigns": len(sentinel.get("campaigns", [])),
        "hot_edges": len(atlas.get("hot_edges", [])),
        "clusters": len(atlas.get("clusters", [])),
        "risk_groups": len(atlas.get("risk_groups", [])),
        "daily": daily,
        "known_top": known[:5],
        "immediate_targets": immediate_targets[:8],
    }

    report["recommendations"] = _merged_recommendations(ranked, sentinel, daily)
    return report


def helios_lines(report: dict):
    lines = [
        f"Threat state: {report.get('threat_state', 'bruit_normal')}",
        f"Focus: {report.get('focus', '-')}",
        f"Top priority: {report.get('top_priority', 0)}",
        f"Critiques: {report.get('critical_count', 0)}",
        f"Élevés: {report.get('high_count', 0)}",
        f"Trackers: {report.get('tracker_count', 0)}",
        f"Watch hits: {report.get('watch_hits', 0)}",
        f"Escalades: {report.get('escalations', 0)}",
        f"Campaigns: {report.get('campaigns', 0)}",
        f"ATLAS hot edges: {report.get('hot_edges', 0)}",
        f"ATLAS clusters: {report.get('clusters', 0)}",
        f"ATLAS risk groups: {report.get('risk_groups', 0)}",
        "",
        "Top cibles immédiates:",
    ]

    targets = report.get("immediate_targets", [])
    if targets:
        for t in targets[:5]:
            lines.append(
                f"- {t['name']} | {t['address']} | priority={t['priority_score']} | "
                f"trust={t['trust_label']} | alert={t['alert_level']}"
            )
    else:
        lines.append("- aucune")

    lines.append("")
    lines.append("Recommandations fusionnées:")
    recs = report.get("recommendations", [])
    if recs:
        for r in recs[:8]:
            lines.append(f"- {r}")
    else:
        lines.append("- aucune")

    return lines
