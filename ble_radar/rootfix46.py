from ble_radar.state import load_last_scan, load_scan_history


def safe_int_like(value, default=0):
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


def safe_text_like(value, default="-"):
    if value is None:
        return default
    if isinstance(value, dict):
        return default
    if isinstance(value, (list, tuple, set)):
        if not value:
            return default
        return ", ".join(str(x) for x in list(value)[:3])
    return str(value)


def _call_report(fn, devices, history, label, issues):
    try:
        return fn(devices, history)
    except Exception as e:
        issues.append(f"{label}: {e}")
        return {}


def safe_brief_from_core(devices=None, history=None):
    if devices is None:
        devices = load_last_scan() or []
    if history is None:
        history = load_scan_history()

    issues = []

    from ble_radar.helios import build_helios_report
    from ble_radar.oracle import build_oracle_report
    from ble_radar.nebula import build_nebula_report

    helios = _call_report(build_helios_report, devices, history, "helios", issues)
    oracle = _call_report(build_oracle_report, devices, history, "oracle", issues)
    nebula = _call_report(build_nebula_report, devices, history, "nebula", issues)

    top_priority = safe_int_like(helios.get("top_priority", 0))
    watch_hits = safe_int_like(helios.get("watch_hits", 0))
    critical_count = safe_int_like(helios.get("critical_count", 0))
    campaigns = safe_int_like(helios.get("campaigns", 0))
    oracle_immediate = safe_int_like(oracle.get("immediate_count", 0))
    oracle_probable = safe_int_like(oracle.get("probable_count", 0))

    master_state = safe_text_like(nebula.get("master_state", "stable"), "stable")
    threat_state = safe_text_like(helios.get("threat_state", "bruit_normal"), "bruit_normal")
    focus = safe_text_like(helios.get("focus", "-"), "-")
    oracle_outlook = safe_text_like(oracle.get("outlook", "stable"), "stable")

    recommendations = helios.get("recommendations", [])
    if not isinstance(recommendations, list):
        recommendations = [safe_text_like(recommendations, "-")]

    targets = helios.get("immediate_targets", [])
    if not isinstance(targets, list):
        targets = []

    if master_state == "crise":
        next_action = "ouvrir SENTINEL / AEGIS / ARGUS immédiatement"
    elif oracle_immediate >= 1:
        next_action = "ouvrir ORACLE puis ARGUS case file"
    elif watch_hits >= 1:
        next_action = "vérifier la watchlist et exporter un incident"
    elif top_priority >= 70:
        next_action = "inspecter les top cibles immédiates"
    else:
        next_action = "surveillance standard"

    return {
        "devices": len(devices),
        "master_state": master_state,
        "threat_state": threat_state,
        "focus": focus,
        "top_priority": top_priority,
        "watch_hits": watch_hits,
        "critical_count": critical_count,
        "campaigns": campaigns,
        "oracle_outlook": oracle_outlook,
        "oracle_immediate": oracle_immediate,
        "oracle_probable": oracle_probable,
        "next_action": next_action,
        "recommendations": recommendations[:6],
        "targets": targets[:5],
        "issues": issues,
    }


def build_rootfix_report(devices=None, history=None):
    brief = safe_brief_from_core(devices, history)
    status = "ROOTFIX46 OK" if not brief.get("issues") else "ROOTFIX46 WARN"

    return {
        "status": status,
        "devices": brief.get("devices", 0),
        "top_priority": brief.get("top_priority", 0),
        "threat_state": brief.get("threat_state", "bruit_normal"),
        "next_action": brief.get("next_action", "-"),
        "issues": brief.get("issues", []),
    }


def rootfix_lines(report):
    lines = [
        f"Status: {report.get('status', 'ROOTFIX46 WARN')}",
        f"Devices: {report.get('devices', 0)}",
        f"Top priority: {report.get('top_priority', 0)}",
        f"Threat state: {report.get('threat_state', 'bruit_normal')}",
        f"Next action: {report.get('next_action', '-')}",
        "",
        "Issues:",
    ]

    issues = report.get("issues", [])
    if issues:
        for item in issues:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    return lines
