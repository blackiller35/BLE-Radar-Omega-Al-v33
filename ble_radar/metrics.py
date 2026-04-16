from statistics import mean

from ble_radar.state import load_scan_history


def _device_metrics(devices):
    total = len(devices)
    critical = sum(1 for d in devices if d.get("alert_level") == "critique")
    high = sum(1 for d in devices if d.get("alert_level") == "élevé")
    medium = sum(1 for d in devices if d.get("alert_level") == "moyen")
    trackers = sum(1 for d in devices if d.get("profile") == "tracker_probable" or d.get("possible_suivi") or d.get("watch_hit"))
    watch_hits = sum(1 for d in devices if d.get("watch_hit"))
    new_devices = sum(1 for d in devices if d.get("is_new_device"))
    unknown_vendor = sum(1 for d in devices if d.get("vendor", "Unknown") == "Unknown")
    random_mac = sum(1 for d in devices if d.get("random_mac"))
    apple_like = sum(1 for d in devices if d.get("vendor") == "Apple" or d.get("apple_prefix"))
    finals = [d.get("final_score", d.get("score", 0)) for d in devices]
    rssis = [d.get("rssi", -100) for d in devices if isinstance(d.get("rssi", -100), (int, float))]

    return {
        "total": total,
        "critical": critical,
        "high": high,
        "medium": medium,
        "trackers": trackers,
        "watch_hits": watch_hits,
        "new_devices": new_devices,
        "unknown_vendor": unknown_vendor,
        "random_mac": random_mac,
        "apple_like": apple_like,
        "avg_final": round(mean(finals), 2) if finals else 0,
        "avg_rssi": round(mean(rssis), 2) if rssis else -100,
    }


def _history_baseline(history):
    if not history:
        return {}

    scans = history[-10:]
    totals = []
    criticals = []
    highs = []
    mediums = []
    trackers = []
    watch_hits = []
    new_devices = []
    unknown_vendor = []
    random_mac = []
    apple_like = []
    avg_final = []

    for scan in scans:
        devices = scan.get("devices", [])
        m = _device_metrics(devices)
        totals.append(m["total"])
        criticals.append(m["critical"])
        highs.append(m["high"])
        mediums.append(m["medium"])
        trackers.append(m["trackers"])
        watch_hits.append(m["watch_hits"])
        new_devices.append(m["new_devices"])
        unknown_vendor.append(m["unknown_vendor"])
        random_mac.append(m["random_mac"])
        apple_like.append(m["apple_like"])
        avg_final.append(m["avg_final"])

    return {
        "total": round(mean(totals), 2) if totals else 0,
        "critical": round(mean(criticals), 2) if criticals else 0,
        "high": round(mean(highs), 2) if highs else 0,
        "medium": round(mean(mediums), 2) if mediums else 0,
        "trackers": round(mean(trackers), 2) if trackers else 0,
        "watch_hits": round(mean(watch_hits), 2) if watch_hits else 0,
        "new_devices": round(mean(new_devices), 2) if new_devices else 0,
        "unknown_vendor": round(mean(unknown_vendor), 2) if unknown_vendor else 0,
        "random_mac": round(mean(random_mac), 2) if random_mac else 0,
        "apple_like": round(mean(apple_like), 2) if apple_like else 0,
        "avg_final": round(mean(avg_final), 2) if avg_final else 0,
    }


def detect_anomalies(current: dict, baseline: dict):
    anomalies = []

    if not baseline:
        if current.get("critical", 0) > 0:
            anomalies.append("premières alertes critiques détectées")
        return anomalies

    if current["total"] >= max(4, baseline.get("total", 0) * 1.6):
        anomalies.append("hausse anormale du nombre total d'appareils")
    if current["new_devices"] >= max(3, baseline.get("new_devices", 0) * 1.7):
        anomalies.append("hausse anormale des nouveaux appareils")
    if current["unknown_vendor"] >= max(3, baseline.get("unknown_vendor", 0) * 1.7):
        anomalies.append("hausse anormale des vendors inconnus")
    if current["random_mac"] >= max(3, baseline.get("random_mac", 0) * 1.7):
        anomalies.append("hausse anormale des MAC random")
    if current["trackers"] >= max(2, baseline.get("trackers", 0) * 1.7):
        anomalies.append("hausse anormale des trackers probables")
    if current["critical"] > baseline.get("critical", 0):
        anomalies.append("plus d'alertes critiques que la baseline")
    if current["high"] > baseline.get("high", 0) + 1:
        anomalies.append("plus d'alertes élevées que d'habitude")
    if current["avg_final"] >= baseline.get("avg_final", 0) + 8:
        anomalies.append("score moyen global plus élevé que la baseline")

    return anomalies


def compute_metrics(devices, history=None):
    if history is None:
        history = load_scan_history()

    current = _device_metrics(devices)
    baseline = _history_baseline(history[:-1] if history else [])
    anomalies = detect_anomalies(current, baseline)
    return current, baseline, anomalies


def metrics_to_lines(current: dict, baseline: dict, anomalies: list[str]):
    lines = [
        "Métriques actuelles",
        f"- total: {current.get('total', 0)}",
        f"- critical: {current.get('critical', 0)}",
        f"- high: {current.get('high', 0)}",
        f"- medium: {current.get('medium', 0)}",
        f"- trackers: {current.get('trackers', 0)}",
        f"- watch_hits: {current.get('watch_hits', 0)}",
        f"- new_devices: {current.get('new_devices', 0)}",
        f"- unknown_vendor: {current.get('unknown_vendor', 0)}",
        f"- random_mac: {current.get('random_mac', 0)}",
        f"- apple_like: {current.get('apple_like', 0)}",
        f"- avg_final: {current.get('avg_final', 0)}",
        "",
        "Baseline",
        f"- total: {baseline.get('total', 0)}",
        f"- critical: {baseline.get('critical', 0)}",
        f"- high: {baseline.get('high', 0)}",
        f"- medium: {baseline.get('medium', 0)}",
        f"- trackers: {baseline.get('trackers', 0)}",
        f"- watch_hits: {baseline.get('watch_hits', 0)}",
        f"- new_devices: {baseline.get('new_devices', 0)}",
        f"- unknown_vendor: {baseline.get('unknown_vendor', 0)}",
        f"- random_mac: {baseline.get('random_mac', 0)}",
        f"- apple_like: {baseline.get('apple_like', 0)}",
        f"- avg_final: {baseline.get('avg_final', 0)}",
        "",
        "Anomalies",
    ]

    if anomalies:
        for a in anomalies:
            lines.append(f"- {a}")
    else:
        lines.append("- aucune anomalie majeure")

    return lines
