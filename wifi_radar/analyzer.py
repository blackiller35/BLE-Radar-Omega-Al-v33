from __future__ import annotations


def classify_wifi_network(network: dict) -> dict:
    ssid = str(network.get("ssid", "Hidden"))
    security = str(network.get("security", "OPEN")).upper()
    signal = int(network.get("signal", 0) or 0)

    score = 0
    tags = []

    if ssid.lower() == "hidden":
        score += 15
        tags.append("HIDDEN_SSID")

    if "OPEN" in security or security.strip() == "":
        score += 40
        tags.append("OPEN_NETWORK")

    if "WPA1" in security:
        score += 25
        tags.append("LEGACY_WPA")

    if "WPA2" in security:
        score += 5
        tags.append("WPA2")

    if "WPA3" in security:
        tags.append("WPA3")

    if signal >= 85:
        score += 10
        tags.append("VERY_CLOSE_SIGNAL")

    if "802.1X" in security:
        tags.append("ENTERPRISE_AUTH")

    if score >= 60:
        level = "high"
    elif score >= 30:
        level = "medium"
    else:
        level = "low"

    return {
        **network,
        "risk_score": min(score, 100),
        "risk_level": level,
        "risk_tags": tags,
    }


def analyze_wifi_networks(networks: list[dict]) -> list[dict]:
    return [classify_wifi_network(net) for net in networks]
