"""OMEGA Threat Context Engine.

Defensive BLE context helper:
- explains why a device looks interesting
- maps risk tags to operator-facing context
- recommends safe next actions
"""

from __future__ import annotations


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def build_threat_context(device: dict) -> dict:
    name = str(device.get("name") or "Unknown")
    address = str(device.get("address") or "-")
    vendor = str(device.get("vendor") or "Unknown")
    hits = int(device.get("hits") or device.get("seen_count") or 0)
    rssi = device.get("rssi")
    tags = _as_list(device.get("risk_tags") or device.get("tags") or [])

    reasons = []
    actions = []
    severity = "low"

    if "HIGH_ACTIVITY" in tags or hits >= 1000:
        reasons.append("activité BLE élevée détectée")
        actions.append("surveiller la réapparition sur plusieurs scans")
        severity = "high"

    if "PERSISTENT_DEVICE" in tags or hits >= 500:
        reasons.append("présence persistante dans la capture")
        actions.append("corréler avec l'historique et la zone observée")
        if severity != "high":
            severity = "medium"

    if "RANDOMIZED_BLE_ADDRESS" in tags:
        reasons.append("adresse BLE possiblement randomisée")
        actions.append("éviter l'identification certaine sans preuve additionnelle")
        if severity == "low":
            severity = "medium"

    lowered = f"{name} {vendor}".lower()
    if any(word in lowered for word in ("tile", "airtag", "smarttag", "tracker", "beacon")):
        reasons.append("profil compatible avec balise ou tracker BLE")
        actions.append("vérifier si l'appareil est connu ou autorisé")
        if severity == "low":
            severity = "medium"

    if rssi is not None:
        try:
            rssi_value = int(rssi)
            if rssi_value >= -55:
                reasons.append("signal proche ou fort")
                actions.append("faire un scan de confirmation à courte distance")
                if severity == "low":
                    severity = "medium"
        except (TypeError, ValueError):
            pass

    if not reasons:
        reasons.append("aucun indicateur fort détecté")
        actions.append("continuer la surveillance passive normale")

    summary = f"{name} ({address}) — {severity.upper()} — {', '.join(reasons[:2])}"

    return {
        "name": name,
        "address": address,
        "vendor": vendor,
        "severity": severity,
        "reasons": reasons,
        "recommended_actions": actions,
        "summary": summary,
    }


def build_threat_contexts(devices: list[dict]) -> list[dict]:
    return [build_threat_context(d) for d in devices or []]
