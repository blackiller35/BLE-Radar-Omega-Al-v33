from statistics import mean

from ble_radar.state import load_scan_history
from ble_radar.argus import rank_priority
from ble_radar.behavior import device_behavior_anomaly
from ble_radar.nexus import search_device_summaries, timeline_for_address
from ble_radar.sentinel import build_sentinel_report
from ble_radar.helios import build_helios_report


def _score_values(timeline):
    values = [int(x.get("final_score", 0)) for x in timeline if isinstance(x.get("final_score", 0), (int, float))]
    return values if values else [0]


def _trend_delta(values):
    if len(values) < 3:
        return 0
    recent = mean(values[-3:])
    older = mean(values[:-3]) if len(values) > 3 else values[0]
    return round(recent - older, 2)


def project_device(device: dict, history=None):
    if history is None:
        history = load_scan_history()

    ranked = rank_priority([device], history, 1)
    row = ranked[0] if ranked else {
        "device": device,
        "priority_score": int(device.get("final_score", device.get("score", 0))),
        "trust_label": "unknown",
        "reasons": [],
    }

    addr = str(device.get("address", "-")).upper()
    summaries = search_device_summaries(addr, history, 1)
    summary = summaries[0] if summaries else {
        "persistence_score": 0,
        "occurrences": 0,
        "patterns": [],
        "unique_days": 0,
    }

    timeline = timeline_for_address(addr, history, 50)
    values = _score_values(timeline)
    trend = _trend_delta(values)

    behavior = device_behavior_anomaly(device, history)
    current_priority = int(row.get("priority_score", 0))
    persistence = int(summary.get("persistence_score", 0))
    anomaly = int(behavior.get("anomaly_score", 0))

    projected = current_priority
    if trend > 0:
        projected += int(trend * 0.8)
    projected += int(persistence * 0.15)
    projected += int(anomaly * 0.35)

    if device.get("watch_hit"):
        projected += 18
    if device.get("possible_suivi"):
        projected += 14
    if device.get("persistent_nearby"):
        projected += 10
    if device.get("alert_level") == "critique":
        projected += 14
    elif device.get("alert_level") == "élevé":
        projected += 8

    projected = max(0, min(100, int(projected)))

    confidence = 35
    confidence += min(summary.get("occurrences", 0) * 6, 30)
    confidence += min(summary.get("unique_days", 0) * 5, 20)
    if len(timeline) >= 4:
        confidence += 10
    confidence = max(0, min(100, int(confidence)))

    if projected >= 85:
        future_state = "risque_immédiat"
    elif projected >= 65:
        future_state = "hausse_probable"
    elif projected >= 45:
        future_state = "à_surveille"
    else:
        future_state = "stable"

    drivers = []
    if trend > 0:
        drivers.append(f"trend +{trend}")
    if persistence >= 40:
        drivers.append("persistance forte")
    if anomaly >= 20:
        drivers.append("anomalie élevée")
    if device.get("watch_hit"):
        drivers.append("watch hit")
    if device.get("possible_suivi"):
        drivers.append("suivi probable")
    if device.get("persistent_nearby"):
        drivers.append("proximité persistante")
    if device.get("alert_level") in ("élevé", "critique"):
        drivers.append(f"alerte {device.get('alert_level')}")

    return {
        "device": device,
        "current_priority": current_priority,
        "projected_priority": projected,
        "future_state": future_state,
        "confidence": confidence,
        "trend_delta": trend,
        "persistence_score": persistence,
        "anomaly_score": anomaly,
        "trust_label": row.get("trust_label", "unknown"),
        "drivers": drivers[:8],
    }


def project_rankings(devices: list[dict], history=None, limit: int = 15):
    if history is None:
        history = load_scan_history()

    rows = [project_device(d, history) for d in devices]
    rows.sort(
        key=lambda x: (
            x["projected_priority"],
            x["confidence"],
            x["current_priority"],
        ),
        reverse=True,
    )
    return rows[:limit]


def build_oracle_report(devices: list[dict], history=None):
    if history is None:
        history = load_scan_history()

    sentinel = build_sentinel_report(
        devices,
        history[-2].get("devices", []) if len(history) >= 2 else [],
        history,
    )
    helios = build_helios_report(devices, history)
    ranked = project_rankings(devices, history, 20)

    rising = [r for r in ranked if r["trend_delta"] > 0]
    immediate = [r for r in ranked if r["future_state"] == "risque_immédiat"]
    probable = [r for r in ranked if r["future_state"] == "hausse_probable"]

    if immediate:
        global_outlook = "attention_maximale"
    elif sentinel.get("threat_state") == "menace_active":
        global_outlook = "pression_forte"
    elif probable or sentinel.get("threat_state") == "incident_probable":
        global_outlook = "montée_probable"
    elif helios.get("top_priority", 0) >= 55:
        global_outlook = "surveillance_proactive"
    else:
        global_outlook = "stable"

    return {
        "outlook": global_outlook,
        "top_priority": helios.get("top_priority", 0),
        "threat_state": sentinel.get("threat_state", "bruit_normal"),
        "immediate_count": len(immediate),
        "probable_count": len(probable),
        "rising_count": len(rising),
        "targets": ranked[:10],
    }


def oracle_lines(report: dict):
    lines = [
        f"Outlook: {report.get('outlook', 'stable')}",
        f"Threat state: {report.get('threat_state', 'bruit_normal')}",
        f"Top priority actuel: {report.get('top_priority', 0)}",
        f"Risques immédiats: {report.get('immediate_count', 0)}",
        f"Hausses probables: {report.get('probable_count', 0)}",
        f"Cibles en montée: {report.get('rising_count', 0)}",
        "",
        "Top risques à venir:",
    ]

    targets = report.get("targets", [])
    if targets:
        for t in targets[:6]:
            d = t["device"]
            lines.append(
                f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
                f"curr={t['current_priority']} -> proj={t['projected_priority']} | "
                f"state={t['future_state']} | conf={t['confidence']}"
            )
    else:
        lines.append("- aucune")

    return lines
