from __future__ import annotations

from copy import deepcopy


DEFAULT_OPERATOR_PROFILE = "balanced"

_OPERATOR_PROFILES = {
    "balanced": {
        "label": "Balanced",
        "risk_threshold": 65,
        "anomaly_boost": 10,
        "live_alerts": True,
        "aegis_mode": "balanced",
        "dashboard_density": "normal",
        "security_feedback": "normal",
    },
    "stealth": {
        "label": "Stealth",
        "risk_threshold": 75,
        "anomaly_boost": 6,
        "live_alerts": False,
        "aegis_mode": "quiet",
        "dashboard_density": "minimal",
        "security_feedback": "low",
    },
    "aggressive": {
        "label": "Aggressive",
        "risk_threshold": 50,
        "anomaly_boost": 18,
        "live_alerts": True,
        "aegis_mode": "strict",
        "dashboard_density": "dense",
        "security_feedback": "high",
    },
    "audit": {
        "label": "Audit",
        "risk_threshold": 60,
        "anomaly_boost": 12,
        "live_alerts": True,
        "aegis_mode": "audit",
        "dashboard_density": "detailed",
        "security_feedback": "normal",
    },
}


def list_operator_profiles() -> list[str]:
    return list(_OPERATOR_PROFILES.keys())


def resolve_operator_profile(name: str | None = None) -> str:
    profile_name = (name or DEFAULT_OPERATOR_PROFILE).strip().lower()
    if profile_name in _OPERATOR_PROFILES:
        return profile_name
    return DEFAULT_OPERATOR_PROFILE


def get_operator_profile(name: str | None = None) -> dict:
    resolved = resolve_operator_profile(name)
    profile = deepcopy(_OPERATOR_PROFILES[resolved])
    profile["name"] = resolved
    return profile


def profile_summary_lines(name: str | None = None) -> list[str]:
    profile = get_operator_profile(name)
    return [
        f"Operator profile: {profile['label']}",
        f"Risk threshold: {profile['risk_threshold']}",
        f"Anomaly boost: {profile['anomaly_boost']}",
        f"Live alerts: {'ON' if profile['live_alerts'] else 'OFF'}",
        f"AEGIS mode: {profile['aegis_mode']}",
        f"Dashboard density: {profile['dashboard_density']}",
        f"Security feedback: {profile['security_feedback']}",
    ]
