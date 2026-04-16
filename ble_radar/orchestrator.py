from ble_radar.mission_control import build_mission_control
from ble_radar.missions import get_active_mission
from ble_radar.ops import radio_health


def recommended_actions(devices):
    mission = get_active_mission()
    control = build_mission_control(devices)
    health = radio_health(devices)

    critical = len(control["critical"])
    high = len(control["high"])
    trackers = len(control["trackers"])
    watch_hits = len(control["watch_hits"])
    hot = control["hot"]

    actions = []

    if watch_hits > 0:
        actions.append({
            "key": "watch_hits",
            "label": "Ouvrir les watchlist hits",
            "reason": "Au moins un appareil watchlist a été détecté.",
            "priority": 100,
        })

    if critical > 0:
        actions.append({
            "key": "critical_alerts",
            "label": "Afficher les alertes critiques",
            "reason": "Une ou plusieurs alertes critiques sont présentes.",
            "priority": 95,
        })

    if high > 0:
        actions.append({
            "key": "high_alerts",
            "label": "Afficher les alertes élevées",
            "reason": "Des alertes élevées sont présentes.",
            "priority": 85,
        })

    if trackers > 0:
        actions.append({
            "key": "tracker_lab",
            "label": "Ouvrir la chasse trackers",
            "reason": "Des trackers probables ou signaux de suivi ont été trouvés.",
            "priority": 90,
        })

    if health["score"] < 55:
        actions.append({
            "key": "deep_scan",
            "label": "Relancer un scan profond",
            "reason": "La santé radio est instable ou dense.",
            "priority": 80,
        })

    if health["unknown_vendor"] >= 3:
        actions.append({
            "key": "unknown_view",
            "label": "Voir les vendors inconnus",
            "reason": "Plusieurs appareils sans vendor connu sont présents.",
            "priority": 70,
        })

    if health["random_mac"] >= 3:
        actions.append({
            "key": "random_view",
            "label": "Voir les MAC random",
            "reason": "Plusieurs MAC aléatoires sont présentes.",
            "priority": 68,
        })

    if hot:
        actions.append({
            "key": "inspect_hot",
            "label": "Inspecter les appareils les plus chauds",
            "reason": "Le scan contient des appareils à score élevé.",
            "priority": 75,
        })

    mission_key = mission["key"]
    if mission_key == "tracker_hunt":
        actions.append({
            "key": "tracker_lab",
            "label": "Priorité mission: tracker lab",
            "reason": "La mission active est orientée chasse tracker.",
            "priority": 98,
        })
    elif mission_key == "rapid_audit":
        actions.append({
            "key": "export_audit",
            "label": "Priorité mission: exporter un audit",
            "reason": "La mission active est orientée audit rapide.",
            "priority": 92,
        })
    elif mission_key == "live_watch":
        actions.append({
            "key": "start_live",
            "label": "Priorité mission: démarrer le radar live",
            "reason": "La mission active est orientée surveillance continue.",
            "priority": 88,
        })
    elif mission_key == "history_forensics":
        actions.append({
            "key": "replay_lab",
            "label": "Priorité mission: ouvrir le replay lab",
            "reason": "La mission active est orientée comparaison historique.",
            "priority": 86,
        })

    dedup = {}
    for a in actions:
        key = a["key"]
        if key not in dedup or a["priority"] > dedup[key]["priority"]:
            dedup[key] = a

    out = sorted(dedup.values(), key=lambda x: x["priority"], reverse=True)
    return out[:8]


def operator_brief(devices):
    control = build_mission_control(devices)
    mission = control["mission"]
    health = control["health"]
    actions = recommended_actions(devices)

    lines = [
        f"Mission active: {mission['label']}",
        f"Focus: {mission['focus']}",
        f"Santé radio: {health['score']}/100 ({health['label']})",
        f"Critiques: {len(control['critical'])}",
        f"Élevés: {len(control['high'])}",
        f"Trackers: {len(control['trackers'])}",
        f"Watch hits: {len(control['watch_hits'])}",
        "",
        "Actions recommandées:",
    ]

    if actions:
        for a in actions:
            lines.append(f"- {a['label']} — {a['reason']}")
    else:
        lines.append("- Aucune action immédiate recommandée.")

    return lines


def action_menu_lines(actions):
    lines = []
    for i, a in enumerate(actions, start=1):
        lines.append(f"{i}) {a['label']}")
        lines.append(f"   {a['reason']}")
    return lines
