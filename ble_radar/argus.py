from ble_radar.state import load_scan_history
from ble_radar.knowledge import get_record
from ble_radar.behavior import device_behavior_anomaly
from ble_radar.nexus import search_device_summaries, timeline_for_address


def _trust_weight(label: str) -> int:
    return {
        "friendly": -20,
        "known": -8,
        "unknown": 0,
        "suspicious": 18,
        "critical": 30,
    }.get(str(label or "unknown").strip().lower(), 0)


def _alert_weight(alert: str) -> int:
    return {
        "faible": 0,
        "moyen": 8,
        "élevé": 18,
        "critique": 30,
    }.get(str(alert or "faible"), 0)


def score_priority(device: dict, history=None):
    if history is None:
        history = load_scan_history()

    addr = str(device.get("address", "-")).upper()
    knowledge = get_record(addr) or {}
    trust_label = knowledge.get("trust_label", "unknown")

    anomaly = device_behavior_anomaly(device, history)
    summaries = search_device_summaries(addr, history, 1)
    persistence = summaries[0] if summaries else {
        "persistence_score": 0,
        "occurrences": 0,
        "patterns": [],
        "unique_days": 0,
        "first_seen": "-",
        "last_seen": "-",
    }

    final_score = int(device.get("final_score", device.get("score", 0)))
    score = 0
    reasons = []

    score += final_score
    if final_score >= 60:
        reasons.append("score final élevé")

    aw = _alert_weight(device.get("alert_level", "faible"))
    score += aw
    if aw:
        reasons.append(f"alerte {device.get('alert_level','faible')}")

    tw = _trust_weight(trust_label)
    score += tw
    if trust_label in ("suspicious", "critical"):
        reasons.append(f"confiance historique: {trust_label}")
    elif trust_label in ("friendly", "known"):
        reasons.append(f"confiance historique: {trust_label}")

    persistence_score = int(persistence.get("persistence_score", 0))
    if persistence_score:
        score += int(persistence_score * 0.35)
        reasons.append("persistance historique")

    anomaly_score = int(anomaly.get("anomaly_score", 0))
    if anomaly_score:
        score += int(anomaly_score * 0.9)
        reasons.append("anomalie comportementale")

    if device.get("watch_hit"):
        score += 35
        reasons.append("watch hit")
    if device.get("possible_suivi"):
        score += 22
        reasons.append("signal de suivi")
    if device.get("persistent_nearby"):
        score += 15
        reasons.append("proximité persistante")
    if device.get("random_mac"):
        score += 8
        reasons.append("mac random")
    if device.get("profile") == "tracker_probable":
        score += 18
        reasons.append("tracker probable")

    score = max(0, min(100, int(score)))

    return {
        "device": device,
        "knowledge": knowledge,
        "behavior": anomaly,
        "persistence": persistence,
        "trust_label": trust_label,
        "priority_score": score,
        "reasons": reasons[:8],
    }


def rank_priority(devices: list[dict], history=None, limit: int = 15):
    if history is None:
        history = load_scan_history()

    rows = [score_priority(d, history) for d in devices]
    rows.sort(
        key=lambda x: (
            x["priority_score"],
            x["device"].get("final_score", x["device"].get("score", 0)),
            x["persistence"].get("occurrences", 0),
        ),
        reverse=True,
    )
    return rows[:limit]


def build_case_file(device: dict, history=None):
    if history is None:
        history = load_scan_history()

    row = score_priority(device, history)
    tl = timeline_for_address(str(device.get("address", "-")).upper(), history, 50)

    return {
        "priority": row,
        "timeline": tl,
    }


def case_file_lines(case: dict):
    row = case["priority"]
    d = row["device"]
    k = row["knowledge"]
    b = row["behavior"]
    p = row["persistence"]

    lines = [
        f"Nom: {d.get('name','Inconnu')}",
        f"Adresse: {d.get('address','-')}",
        f"Vendor: {d.get('vendor','Unknown')}",
        f"Profil: {d.get('profile','general_ble')}",
        f"Priority score: {row.get('priority_score', 0)}/100",
        f"Trust label: {row.get('trust_label', 'unknown')}",
        f"Score final courant: {d.get('final_score', d.get('score', 0))}",
        f"Alerte courante: {d.get('alert_level','faible')}",
        "",
        f"Sightings: {k.get('sightings', 0)}",
        f"First seen: {k.get('first_seen', '-')}",
        f"Last seen: {k.get('last_seen', '-')}",
        f"Manual label: {k.get('manual_label', '') or '-'}",
        f"Note: {k.get('note', '') or '-'}",
        "",
        f"Persistance: {p.get('persistence_score', 0)}/100",
        f"Occurrences: {p.get('occurrences', 0)}",
        f"Jours uniques: {p.get('unique_days', 0)}",
        f"Patterns: {', '.join(p.get('patterns', [])) if p.get('patterns') else '-'}",
        "",
        f"Anomaly score: {b.get('anomaly_score', 0)}",
        f"Anomalies: {', '.join(b.get('anomalies', [])) if b.get('anomalies') else '-'}",
        "",
        f"Raisons ARGUS: {', '.join(row.get('reasons', [])) if row.get('reasons') else '-'}",
        "",
        "Timeline récente:",
    ]

    for t in case.get("timeline", [])[:12]:
        lines.append(
            f"- [{t.get('stamp','-')}] {t.get('name','Inconnu')} | "
            f"score={t.get('final_score',0)} | alert={t.get('alert_level','faible')} | "
            f"rssi={t.get('rssi',-100)}"
        )

    return lines


def argus_recommended_actions(rows: list[dict]):
    if not rows:
        return ["Aucune cible prioritaire."]

    top = rows[0]
    actions = []

    if top["trust_label"] in ("critical", "suspicious"):
        actions.append("Inspecter immédiatement la cible prioritaire.")
    if top["device"].get("watch_hit"):
        actions.append("Vérifier la watchlist et exporter un incident enrichi.")
    if top["device"].get("profile") == "tracker_probable" or top["device"].get("possible_suivi"):
        actions.append("Ouvrir la chasse trackers.")
    if top["behavior"].get("anomaly_score", 0) >= 20:
        actions.append("Comparer le comportement historique dans NEXUS.")
    if top["persistence"].get("persistence_score", 0) >= 50:
        actions.append("Vérifier la persistance historique et les motifs récurrents.")

    if not actions:
        actions.append("Surveiller l'évolution au prochain scan.")

    return actions[:6]
