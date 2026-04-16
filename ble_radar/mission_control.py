from ble_radar.ops import radio_health
from ble_radar.missions import mission_recommendations, mission_summary_lines, get_active_mission
from ble_radar.selectors import sort_by_score


def build_mission_control(devices):
    devices = sort_by_score(devices)
    mission = get_active_mission()
    health = radio_health(devices)

    critical = [d for d in devices if d.get("alert_level") == "critique"]
    high = [d for d in devices if d.get("alert_level") == "élevé"]
    trackers = [
        d for d in devices
        if d.get("profile") == "tracker_probable"
        or d.get("possible_suivi")
        or d.get("watch_hit")
    ]
    watch_hits = [d for d in devices if d.get("watch_hit")]
    hot = devices[:10]

    return {
        "mission": mission,
        "health": health,
        "critical": critical,
        "high": high,
        "trackers": trackers,
        "watch_hits": watch_hits,
        "hot": hot,
        "recommendations": mission_recommendations(devices, mission),
        "summary_lines": mission_summary_lines(devices, mission),
    }


def mission_control_lines(data):
    lines = [
        f"Mission: {data['mission']['label']}",
        f"Focus: {data['mission']['focus']}",
        f"Santé radio: {data['health']['score']}/100 ({data['health']['label']})",
        f"Critiques: {len(data['critical'])}",
        f"Élevés: {len(data['high'])}",
        f"Trackers: {len(data['trackers'])}",
        f"Watch hits: {len(data['watch_hits'])}",
        "",
        "Recommandations:",
    ]
    for r in data["recommendations"]:
        lines.append(f"- {r}")

    if data["hot"]:
        lines.append("")
        lines.append("Top appareils chauds:")
        for d in data["hot"][:5]:
            lines.append(
                f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
                f"{d.get('vendor','Unknown')} | final={d.get('final_score', d.get('score', 0))} | "
                f"{d.get('alert_level','faible')}"
            )

    return lines
