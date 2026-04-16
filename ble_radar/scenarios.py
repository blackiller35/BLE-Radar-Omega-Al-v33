SCENARIOS = {
    "tracker_hunt": {
        "key": "tracker_hunt",
        "label": "Je cherche un tracker",
        "steps": [
            "Lancer un scan profond",
            "Ouvrir la chasse trackers",
            "Voir les watchlist hits",
            "Inspecter les appareils chauds",
        ],
    },
    "rapid_audit": {
        "key": "rapid_audit",
        "label": "Je veux un audit rapide",
        "steps": [
            "Lancer un scan normal",
            "Afficher les alertes prioritaires",
            "Exporter un audit terrain",
        ],
    },
    "live_watch": {
        "key": "live_watch",
        "label": "Je surveille en live",
        "steps": [
            "Lancer un scan rapide",
            "Vérifier la santé radio",
            "Démarrer le radar live",
        ],
    },
    "history_forensics": {
        "key": "history_forensics",
        "label": "Je compare l'historique",
        "steps": [
            "Ouvrir le replay lab",
            "Comparer les 2 derniers scans",
            "Rechercher dans l'historique",
        ],
    },
}


def list_scenarios():
    return [SCENARIOS[k] for k in SCENARIOS]


def get_scenario(key: str):
    return SCENARIOS.get(str(key or "").strip())
