from copy import deepcopy

from ble_radar.config import STATE_DIR
from ble_radar.state import load_json, save_json, load_scan_history
from ble_radar.argus import rank_priority
from ble_radar.sentinel import build_sentinel_report
from ble_radar.helios import build_helios_report

AEGIS_FILE = STATE_DIR / "aegis_rules.json"

DEFAULT_AEGIS = {
    "enabled": True,
    "thresholds": {
        "priority_high": 70,
        "priority_critical": 85,
        "watch_hits": 1,
        "critical_alerts": 1,
        "high_alerts": 2,
        "campaign_count": 1,
        "tracker_cluster": 2,
        "escalations": 2,
    },
}

PLAYBOOKS = {
    "watch_hit_active": {
        "title": "Playbook watch hit actif",
        "actions": [
            "Ouvrir immédiatement la watchlist.",
            "Inspecter la cible dans ARGUS.",
            "Exporter un incident enrichi.",
            "Sauvegarder une watch session SENTINEL.",
        ],
    },
    "critical_alert_wave": {
        "title": "Playbook vague critique",
        "actions": [
            "Afficher les alertes critiques.",
            "Vérifier les escalades dans SENTINEL.",
            "Inspecter les cibles immédiates HELIOS.",
            "Créer un audit terrain.",
        ],
    },
    "coordinated_tracker_campaign": {
        "title": "Playbook campagne tracker",
        "actions": [
            "Ouvrir Tracker Lab.",
            "Vérifier les campaigns dans SENTINEL.",
            "Comparer les motifs dans NEXUS.",
            "Étiqueter les appareils concernés dans OMEGA-X.",
        ],
    },
    "active_escalation": {
        "title": "Playbook escalade active",
        "actions": [
            "Ouvrir SENTINEL escalations.",
            "Ouvrir ARGUS case file.",
            "Comparer au scan précédent.",
            "Surveiller en radar live.",
        ],
    },
    "priority_target_critical": {
        "title": "Playbook cible prioritaire",
        "actions": [
            "Ouvrir le case file ARGUS.",
            "Vérifier la persistance NEXUS.",
            "Regarder les voisins ATLAS.",
            "Évaluer si un label manuel est nécessaire.",
        ],
    },
    "alert_pressure": {
        "title": "Playbook pression d’alertes",
        "actions": [
            "Afficher les alertes élevées +.",
            "Vérifier le dashboard HELIOS.",
            "Consulter Mission Dashboard.",
            "Faire un scan profond si la pression reste haute.",
        ],
    },
}

if not AEGIS_FILE.exists():
    save_json(AEGIS_FILE, DEFAULT_AEGIS)


def _aegis_safe_int(value, default=0):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, (list, tuple, set, dict)):
        return len(value)
    try:
        return int(value)
    except Exception:
        return default


def load_aegis_config():
    data = load_json(AEGIS_FILE, DEFAULT_AEGIS)
    if not isinstance(data, dict):
        data = deepcopy(DEFAULT_AEGIS)
    data.setdefault("enabled", True)
    data.setdefault("thresholds", deepcopy(DEFAULT_AEGIS["thresholds"]))
    return data


def save_aegis_config(data):
    save_json(AEGIS_FILE, data)


def toggle_aegis_engine():
    data = load_aegis_config()
    data["enabled"] = not bool(data.get("enabled", True))
    save_aegis_config(data)
    return data


def shift_threshold(key: str, delta: int):
    data = load_aegis_config()
    thresholds = data.setdefault("thresholds", {})
    if key in thresholds:
        thresholds[key] = max(0, int(thresholds.get(key, 0)) + int(delta))
    save_aegis_config(data)
    return data


def get_playbook(key: str):
    return PLAYBOOKS.get(key, {"title": key, "actions": []})


def playbook_lines(playbook: dict):
    lines = [playbook.get("title", "Playbook"), "Actions:"]
    for action in playbook.get("actions", []):
        lines.append(f"- {action}")
    return lines


def _add_incident(incidents, key, severity, title, why, playbook, score):
    incidents.append({
        "key": key,
        "severity": severity,
        "title": title,
        "why": why,
        "playbook": playbook,
        "score": int(score),
    })


def evaluate_aegis(devices, history=None):
    if history is None:
        history = load_scan_history()

    cfg = load_aegis_config()
    thresholds = cfg.get("thresholds", {})
    previous_devices = history[-2].get("devices", []) if len(history) >= 2 else []

    sentinel = build_sentinel_report(devices, previous_devices, history)
    helios = build_helios_report(devices, history)
    ranked = rank_priority(devices, history, 20)

    if not cfg.get("enabled", True):
        return {
            "enabled": False,
            "thresholds": thresholds,
            "threat_state": sentinel.get("threat_state", "bruit_normal"),
            "incidents": [],
        }

    incidents = []

    if _aegis_safe_int(sentinel.get("watch_hits", 0)) >= thresholds.get("watch_hits", 1):
        _add_incident(
            incidents,
            "watch_hit_active",
            "critical",
            "Watch hit actif",
            "Au moins un appareil de watchlist est présent.",
            "watch_hit_active",
            95,
        )

    if _aegis_safe_int(sentinel.get("critical_count", 0)) >= thresholds.get("critical_alerts", 1):
        _add_incident(
            incidents,
            "critical_alert_wave",
            "critical",
            "Vague d’alertes critiques",
            "Une ou plusieurs alertes critiques sont présentes.",
            "critical_alert_wave",
            90,
        )

    if (
        _aegis_safe_int(sentinel.get("campaigns", 0)) >= thresholds.get("campaign_count", 1)
        and _aegis_safe_int(sentinel.get("tracker_count", 0)) >= thresholds.get("tracker_cluster", 2)
    ):
        _add_incident(
            incidents,
            "coordinated_tracker_campaign",
            "high",
            "Campagne tracker coordonnée",
            "Plusieurs trackers/campaigns sont visibles simultanément.",
            "coordinated_tracker_campaign",
            84,
        )

    if (
        _aegis_safe_int(sentinel.get("escalations", 0)) >= thresholds.get("escalations", 2)
        and _aegis_safe_int(helios.get("top_priority", 0)) >= thresholds.get("priority_high", 70)
    ):
        _add_incident(
            incidents,
            "active_escalation",
            "high",
            "Escalade active",
            "Des appareils montrent une montée de risque entre scans.",
            "active_escalation",
            80,
        )

    if _aegis_safe_int(helios.get("top_priority", 0)) >= thresholds.get("priority_critical", 85):
        _add_incident(
            incidents,
            "priority_target_critical",
            "high",
            "Cible prioritaire critique",
            "La cible la plus chaude dépasse le seuil critique.",
            "priority_target_critical",
            helios.get("top_priority", 0),
        )

    if (
        _aegis_safe_int(sentinel.get("high_count", 0)) >= thresholds.get("high_alerts", 2)
        and sentinel.get("threat_state") in ("incident_probable", "menace_active")
    ):
        _add_incident(
            incidents,
            "alert_pressure",
            "medium",
            "Pression d’alertes",
            "Le volume d’alertes élevées reste important.",
            "alert_pressure",
            65,
        )

    incidents.sort(
        key=lambda x: (
            {"critical": 3, "high": 2, "medium": 1, "low": 0}.get(x["severity"], 0),
            x["score"],
        ),
        reverse=True,
    )

    return {
        "enabled": True,
        "thresholds": thresholds,
        "threat_state": sentinel.get("threat_state", "bruit_normal"),
        "incidents": incidents[:10],
        "top_priority": helios.get("top_priority", 0),
    }


def aegis_summary_lines(result: dict):
    lines = [
        f"AEGIS enabled: {result.get('enabled', True)}",
        f"Threat state: {result.get('threat_state', 'bruit_normal')}",
        f"Top priority: {result.get('top_priority', 0)}",
        "Incidents composés:",
    ]

    incidents = result.get("incidents", [])
    if incidents:
        for inc in incidents[:6]:
            lines.append(
                f"- [{inc['severity']}] {inc['title']} | score={inc['score']} | {inc['why']}"
            )
    else:
        lines.append("- aucun")

    return lines
