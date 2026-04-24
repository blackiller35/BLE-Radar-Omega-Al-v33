from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


DEFAULT_WIFI_HISTORY_PATH = Path("history/wifi_history.json")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_wifi_history(path: str | Path = DEFAULT_WIFI_HISTORY_PATH) -> dict:
    p = Path(path)
    if not p.exists():
        return {"networks": {}}

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"networks": {}}

    if not isinstance(data, dict):
        return {"networks": {}}

    data.setdefault("networks", {})
    return data


def update_wifi_history(
    networks: list[dict],
    path: str | Path = DEFAULT_WIFI_HISTORY_PATH,
) -> dict:
    p = Path(path)
    history = load_wifi_history(p)
    now = _now()

    for net in networks:
        bssid = str(net.get("bssid", "")).upper()
        if not bssid:
            continue

        existing = history["networks"].get(bssid, {})

        first_seen = existing.get("first_seen", now)
        seen_count = int(existing.get("seen_count", 0)) + 1
        previous_best_signal = int(existing.get("best_signal", -999))
        current_signal = int(net.get("signal", -999) or -999)

        history["networks"][bssid] = {
            **existing,
            **net,
            "bssid": bssid,
            "first_seen": first_seen,
            "last_seen": now,
            "seen_count": seen_count,
            "best_signal": max(previous_best_signal, current_signal),
        }

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    return history


def summarize_wifi_history(history: dict) -> dict:
    networks = history.get("networks", {})
    values = list(networks.values())

    return {
        "total_known_networks": len(values),
        "hidden_networks": sum(1 for n in values if str(n.get("ssid", "")).lower() == "hidden"),
        "medium_or_high_risk": sum(
            1 for n in values if str(n.get("risk_level", "low")).lower() in {"medium", "high"}
        ),
        "very_close": sum(
            1 for n in values if "VERY_CLOSE_SIGNAL" in n.get("risk_tags", [])
        ),
    }
