from ble_radar.config import STATE_DIR
from ble_radar.state import load_json, save_json
from ble_radar.ops import radio_health

MISSION_STATE_FILE = STATE_DIR / "mission_mode.json"

MISSIONS = {
    "general": {
        "key": "general",
        "label": "General Ops",
        "description": "Mode polyvalent pour usage quotidien.",
        "focus": "équilibre global",
    },
    "tracker_hunt": {
        "key": "tracker_hunt",
        "label": "Tracker Hunt",
        "description": "Priorise le suivi, les watch hits et la proximité persistante.",
        "focus": "trackers et suivi",
    },
    "rapid_audit": {
        "key": "rapid_audit",
        "label": "Rapid Audit",
        "description": "Résumé rapide, alertes prioritaires et export terrain.",
        "focus": "audit express",
    },
    "live_watch": {
        "key": "live_watch",
        "label": "Live Watch",
        "description": "Pensé pour le radar live et les changements rapides.",
        "focus": "surveillance continue",
    },
    "history_forensics": {
        "key": "history_forensics",
        "label": "History Forensics",
        "description": "Optimisé pour comparaison, replay et historique.",
        "focus": "analyse historique",
    },
}

if not MISSION_STATE_FILE.exists():
    save_json(MISSION_STATE_FILE, {"active": "general"})


def list_missions():
    return [MISSIONS[k] for k in MISSIONS]


def get_active_mission_key():
    data = load_json(MISSION_STATE_FILE, {"active": "general"})
    key = str(data.get("active", "general"))
    if key not in MISSIONS:
        key = "general"
    return key


def get_active_mission():
    return MISSIONS[get_active_mission_key()]


def set_active_mission(key: str):
    key = str(key).strip()
    if key not in MISSIONS:
        key = "general"
    save_json(MISSION_STATE_FILE, {"active": key})
    return get_active_mission()


def mission_recommendations(devices, mission=None):
    if mission is None:
        mission = get_active_mission()

    health = radio_health(devices)
    alerts = [d for d in devices if d.get("alert_level") in ("critique", "élevé")]
    trackers = [
        d for d in devices
        if d.get("profile") == "tracker_probable"
        or d.get("possible_suivi")
        or d.get("watch_hit")
    ]
    watch_hits = [d for d in devices if d.get("watch_hit")]
    new_devices = [d for d in devices if d.get("is_new_device")]
    nearby = [d for d in devices if d.get("persistent_nearby")]

    recs = []

    if health["score"] < 50:
        recs.append("Environnement radio instable: lance un scan profond.")
    if alerts:
        recs.append("Des alertes élevées/critique sont présentes: ouvre les alertes prioritaires.")
    if trackers:
        recs.append("Des trackers probables sont détectés: ouvre la chasse trackers.")
    if watch_hits:
        recs.append("Un appareil watchlist est présent: inspecte-le immédiatement.")
    if len(new_devices) >= 3:
        recs.append("Beaucoup de nouveaux appareils: ouvre les vues tactiques 'nouveaux appareils'.")
    if len(nearby) >= 2:
        recs.append("Plusieurs appareils proches persistants: vérifie la proximité persistante.")

    key = mission["key"]

    if key == "tracker_hunt":
        recs.insert(0, "Mission tracker hunt: priorise trackers, watch hits et suivi.")
    elif key == "rapid_audit":
        recs.insert(0, "Mission rapid audit: exporte un audit après le scan.")
    elif key == "live_watch":
        recs.insert(0, "Mission live watch: utilise le radar live adaptatif.")
    elif key == "history_forensics":
        recs.insert(0, "Mission history forensics: compare les scans et ouvre le replay lab.")
    else:
        recs.insert(0, "Mission general ops: garde une vue équilibrée.")

    if not recs:
        recs.append("Aucune action urgente recommandée.")

    return recs[:8]


def mission_summary_lines(devices, mission=None):
    if mission is None:
        mission = get_active_mission()

    health = radio_health(devices)
    recs = mission_recommendations(devices, mission)

    lines = [
        f"Mission active: {mission['label']}",
        f"Focus: {mission['focus']}",
        f"Santé radio: {health['score']}/100 ({health['label']})",
        "Recommandations:",
    ]
    for r in recs:
        lines.append(f"- {r}")
    return lines
