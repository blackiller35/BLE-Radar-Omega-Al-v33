from copy import deepcopy


BASELINE_FEATURES = [
    {
        "key": "runtime_config",
        "label": "Runtime config",
        "status": "ready",
        "description": "Configuration runtime stabilisée",
    },
    {
        "key": "device_contract",
        "label": "Device contract",
        "status": "ready",
        "description": "Contrat device et normalisation centralisée",
    },
    {
        "key": "score_explanations",
        "label": "Score explanations",
        "status": "ready",
        "description": "Scoring explicable propagé dans dashboard et exports",
    },
    {
        "key": "dashboard_pro",
        "label": "Dashboard pro",
        "status": "ready",
        "description": "Vue opérateur HTML enrichie",
    },
    {
        "key": "investigation_cases",
        "label": "Investigation cases",
        "status": "ready",
        "description": "Cas, notes et statuts d'investigation locaux",
    },
    {
        "key": "incident_packs",
        "label": "Incident packs",
        "status": "ready",
        "description": "Packs d'incident locaux avec manifest et résumé",
    },
    {
        "key": "automation_safe",
        "label": "Automation safe mode",
        "status": "ready",
        "description": "Dry-run automation avec traçabilité",
    },
    {
        "key": "release_guard",
        "label": "Release guard",
        "status": "ready",
        "description": "Garde-fou final pour validation et release",
    },
]


def feature_matrix() -> list[dict]:
    return deepcopy(BASELINE_FEATURES)


def current_milestone() -> str:
    return "v0.4.0"


def ready_feature_count() -> int:
    return sum(1 for item in BASELINE_FEATURES if item.get("status") == "ready")


def baseline_summary() -> dict:
    return {
        "milestone": current_milestone(),
        "total_features": len(BASELINE_FEATURES),
        "ready_features": ready_feature_count(),
        "is_ready": ready_feature_count() == len(BASELINE_FEATURES),
    }


def summary_lines() -> list[str]:
    summary = baseline_summary()
    lines = [
        "BLE Radar Omega AI - Operator Baseline",
        f"Milestone: {summary['milestone']}",
        f"Ready features: {summary['ready_features']}/{summary['total_features']}",
        f"Ready: {'yes' if summary['is_ready'] else 'no'}",
        "Features:",
    ]

    for item in BASELINE_FEATURES:
        lines.append(f"- {item['label']} | {item['status']} | {item['description']}")

    return lines
