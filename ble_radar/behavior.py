from statistics import mean

from ble_radar.state import load_scan_history
from ble_radar.nexus import timeline_for_address


def _sev(alert: str) -> int:
    return {"faible": 0, "moyen": 1, "élevé": 2, "critique": 3}.get(str(alert or "faible"), 0)


def behavior_profile(address: str, history=None):
    if history is None:
        history = load_scan_history()

    tl = timeline_for_address(address, history, 200)
    if not tl:
        return {
            "occurrences": 0,
            "avg_rssi": -100,
            "avg_score": 0,
            "max_score": 0,
            "days_seen": 0,
            "max_alert": "faible",
            "known_vendor": "Unknown",
            "known_profile": "general_ble",
        }

    scores = [int(x.get("final_score", 0)) for x in tl]
    rssis = [int(x.get("rssi", -100)) for x in tl if isinstance(x.get("rssi", -100), (int, float))]
    days = len({(x["dt"].date().isoformat() if x.get("dt") else str(x.get("stamp", "-"))[:10]) for x in tl})
    max_alert = max((x.get("alert_level", "faible") for x in tl), key=_sev)

    vendor_counts = {}
    profile_counts = {}
    for x in tl:
        v = x.get("vendor", "Unknown")
        p = x.get("profile", "general_ble")
        vendor_counts[v] = vendor_counts.get(v, 0) + 1
        profile_counts[p] = profile_counts.get(p, 0) + 1

    known_vendor = max(vendor_counts, key=vendor_counts.get) if vendor_counts else "Unknown"
    known_profile = max(profile_counts, key=profile_counts.get) if profile_counts else "general_ble"

    return {
        "occurrences": len(tl),
        "avg_rssi": round(mean(rssis), 2) if rssis else -100,
        "avg_score": round(mean(scores), 2) if scores else 0,
        "max_score": max(scores) if scores else 0,
        "days_seen": days,
        "max_alert": max_alert,
        "known_vendor": known_vendor,
        "known_profile": known_profile,
    }


def device_behavior_anomaly(device: dict, history=None):
    profile = behavior_profile(device.get("address", ""), history)

    current_score = int(device.get("final_score", device.get("score", 0)))
    current_rssi = int(device.get("rssi", -100))
    current_alert = str(device.get("alert_level", "faible"))
    current_vendor = str(device.get("vendor", "Unknown"))
    current_profile = str(device.get("profile", "general_ble"))

    anomalies = []
    anomaly_score = 0

    if profile["occurrences"] <= 1:
        anomalies.append("présence historiquement rare")
        anomaly_score += 12

    if current_score >= profile["avg_score"] + 15:
        anomalies.append("score supérieur à l'habitude")
        anomaly_score += 18

    if current_rssi >= profile["avg_rssi"] + 12:
        anomalies.append("présence plus proche que d'habitude")
        anomaly_score += 16

    if _sev(current_alert) > _sev(profile["max_alert"]):
        anomalies.append("niveau d'alerte plus élevé que l'historique")
        anomaly_score += 20

    if profile["known_vendor"] != "Unknown" and current_vendor != profile["known_vendor"]:
        anomalies.append("vendor différent de l'historique")
        anomaly_score += 8

    if profile["known_profile"] != "general_ble" and current_profile != profile["known_profile"]:
        anomalies.append("profil différent de l'historique")
        anomaly_score += 8

    if device.get("watch_hit"):
        anomalies.append("watch hit actif")
        anomaly_score += 25

    if device.get("possible_suivi"):
        anomalies.append("signal de suivi probable")
        anomaly_score += 20

    if device.get("persistent_nearby"):
        anomalies.append("proximité persistante")
        anomaly_score += 12

    return {
        "device": device,
        "behavior": profile,
        "anomaly_score": anomaly_score,
        "anomalies": anomalies,
    }


def rank_behavior_anomalies(devices: list[dict], history=None, limit: int = 15):
    rows = [device_behavior_anomaly(d, history) for d in devices]
    rows.sort(
        key=lambda x: (
            x["anomaly_score"],
            x["device"].get("final_score", x["device"].get("score", 0)),
        ),
        reverse=True,
    )
    return rows[:limit]
