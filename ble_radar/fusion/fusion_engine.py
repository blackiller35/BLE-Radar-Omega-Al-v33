from __future__ import annotations

from typing import Any


def _prefix(value: str | None, size: int = 8) -> str:
    if not value:
        return ""
    return value.upper().replace(":", "").replace("-", "")[:size]


def _signal_bucket(rssi: int | float | None) -> str:
    if rssi is None:
        return "unknown"
    if rssi >= -50:
        return "near"
    if rssi >= -70:
        return "medium"
    return "far"


def compute_fusion_risk(match_score: int, ble: dict[str, Any], wifi: dict[str, Any]) -> str:
    ble_rssi = ble.get("rssi")
    wifi_rssi = wifi.get("rssi")
    near_count = [_signal_bucket(ble_rssi), _signal_bucket(wifi_rssi)].count("near")

    if match_score >= 80 and near_count >= 1:
        return "high"
    if match_score >= 50:
        return "medium"
    return "low"


def generate_operator_summary(match_score: int, risk: str, reasons: list[str]) -> str:
    reason_text = ", ".join(reasons) if reasons else "weak correlation"
    return f"{risk.upper()} fusion correlation ({match_score}%) based on {reason_text}."


def correlate_ble_wifi(
    ble_devices: list[dict[str, Any]],
    wifi_devices: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    correlations: list[dict[str, Any]] = []

    for ble in ble_devices:
        ble_addr = str(ble.get("address") or ble.get("mac") or "")
        ble_vendor = str(ble.get("vendor") or "").lower()
        ble_name = str(ble.get("name") or "").lower()

        for wifi in wifi_devices:
            wifi_addr = str(wifi.get("bssid") or wifi.get("mac") or "")
            wifi_vendor = str(wifi.get("vendor") or "").lower()
            wifi_ssid = str(wifi.get("ssid") or wifi.get("name") or "").lower()

            score = 0
            reasons: list[str] = []

            if _prefix(ble_addr, 6) and _prefix(ble_addr, 6) == _prefix(wifi_addr, 6):
                score += 50
                reasons.append("same OUI prefix")

            if ble_vendor and wifi_vendor and ble_vendor == wifi_vendor:
                score += 25
                reasons.append("same vendor")

            if ble_name and wifi_ssid and (ble_name in wifi_ssid or wifi_ssid in ble_name):
                score += 20
                reasons.append("name similarity")

            if _signal_bucket(ble.get("rssi")) == _signal_bucket(wifi.get("rssi")) != "unknown":
                score += 10
                reasons.append("similar signal bucket")

            if score <= 0:
                continue

            score = min(score, 100)
            risk = compute_fusion_risk(score, ble, wifi)

            correlations.append(
                {
                    "ble": ble,
                    "wifi": wifi,
                    "match_score": score,
                    "risk": risk,
                    "reasons": reasons,
                    "summary": generate_operator_summary(score, risk, reasons),
                }
            )

    return sorted(correlations, key=lambda item: item["match_score"], reverse=True)


def apply_fusion_threat_boost(
    threat_context: dict[str, Any],
    correlations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Escalate operator-facing risk when BLE/WiFi fusion is high-confidence."""
    boosted = dict(threat_context)
    tags = set(boosted.get("tags") or [])

    high_matches = [
        item for item in correlations
        if item.get("risk") == "high" and int(item.get("match_score") or 0) >= 80
    ]

    if high_matches:
        boosted["risk"] = "critical"
        tags.add("FUSION_HIGH_CONFIDENCE")
        tags.add("MULTI_SIGNAL_CORRELATION")
        boosted["fusion_boost"] = {
            "enabled": True,
            "highest_match_score": max(int(item.get("match_score") or 0) for item in high_matches),
            "reason": "High-confidence BLE/WiFi correlation escalated operator risk.",
        }
    else:
        boosted["fusion_boost"] = {
            "enabled": False,
            "reason": "No high-confidence BLE/WiFi fusion correlation.",
        }

    boosted["tags"] = sorted(tags)
    return boosted
