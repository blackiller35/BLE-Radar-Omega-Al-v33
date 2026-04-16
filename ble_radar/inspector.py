from ble_radar.selectors import sort_by_score


def inspect_device(device: dict) -> dict:
    flags = device.get("flags", [])
    reason_full = device.get("reason_full", [])

    summary = {
        "identity": {
            "name": device.get("name", "Inconnu"),
            "address": device.get("address", "-"),
            "vendor": device.get("vendor", "Unknown"),
            "profile": device.get("profile", "general_ble"),
        },
        "radio": {
            "rssi": device.get("rssi", "-"),
            "near_count": device.get("near_count", 0),
            "persistent_nearby": device.get("persistent_nearby", False),
        },
        "scores": {
            "risk_score": device.get("risk_score", device.get("score", 0)),
            "follow_score": device.get("follow_score", 0),
            "confidence_score": device.get("confidence_score", 0),
            "final_score": device.get("final_score", device.get("score", 0)),
        },
        "status": {
            "alert_level": device.get("alert_level", "faible"),
            "classification": device.get("classification", "normal"),
            "possible_suivi": device.get("possible_suivi", False),
            "watch_hit": device.get("watch_hit", False),
            "whitelisted": device.get("whitelisted", False),
            "watched": device.get("watched", False),
            "is_new_device": device.get("is_new_device", False),
        },
        "flags": flags if isinstance(flags, list) else [],
        "reasons": reason_full if isinstance(reason_full, list) else [device.get("reason_short", "normal")],
    }

    return summary


def inspect_to_lines(device: dict) -> list[str]:
    data = inspect_device(device)

    lines = [
        f"Nom: {data['identity']['name']}",
        f"Adresse: {data['identity']['address']}",
        f"Vendor: {data['identity']['vendor']}",
        f"Profil: {data['identity']['profile']}",
        "",
        f"RSSI: {data['radio']['rssi']}",
        f"Near count: {data['radio']['near_count']}",
        f"Persistent nearby: {data['radio']['persistent_nearby']}",
        "",
        f"Risk score: {data['scores']['risk_score']}",
        f"Follow score: {data['scores']['follow_score']}",
        f"Confidence score: {data['scores']['confidence_score']}",
        f"Final score: {data['scores']['final_score']}",
        "",
        f"Alerte: {data['status']['alert_level']}",
        f"Classification: {data['status']['classification']}",
        f"Possible suivi: {data['status']['possible_suivi']}",
        f"Watch hit: {data['status']['watch_hit']}",
        f"Whitelisted: {data['status']['whitelisted']}",
        f"Watched: {data['status']['watched']}",
        f"New device: {data['status']['is_new_device']}",
        "",
        f"Flags: {', '.join(data['flags']) if data['flags'] else '-'}",
        "Raisons détaillées:",
    ]

    for reason in data["reasons"]:
        lines.append(f"- {reason}")

    return lines


def pick_top_devices(devices: list[dict], limit: int = 20) -> list[dict]:
    return sort_by_score(devices)[:limit]
