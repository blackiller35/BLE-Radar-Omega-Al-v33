from __future__ import annotations

from ble_radar.alert_history import record_alert

from datetime import datetime
from pathlib import Path


ALERT_LOG_PATH = Path("history/alerts.log")


def log_only(msg: str) -> None:
    try:
        ALERT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with ALERT_LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(msg + "\n")
    except Exception:
        pass


def emit_alert(event: dict, profile: dict) -> str:
    """
    event = {
        "device": str,
        "score": int,
        "type": str,
    }
    """
    level = profile.get("aegis_mode", "balanced")
    live = profile.get("live_alerts", True)

    timestamp = datetime.now().strftime("%H:%M:%S")
    device = event.get("device", "unknown")
    score = event.get("score", 0)
    etype = event.get("type", "generic")

    msg = f"[{timestamp}] ALERT {etype.upper()} | {device} | score={score}"

    if not live:
        log_only(msg)
        return msg

    if level == "strict":
        rendered = f"[!!! OMEGA ALERT !!!] {msg}"
        print(f"\n{rendered}")
        log_only(rendered)
        record_alert(event, profile)
    return rendered

    if level == "audit":
        rendered = f"[AUDIT] {msg}"
        print(rendered)
        log_only(rendered)
        record_alert(event, profile)
    return rendered

    rendered = f"[ALERT] {msg}"
    print(rendered)
    log_only(rendered)
    record_alert(event, profile)
    return rendered
