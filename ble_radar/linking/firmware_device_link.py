from __future__ import annotations


def _norm(value) -> str:
    return str(value or "").strip().lower()


def firmware_matches_device(device: dict, report: dict) -> bool:
    """Best-effort local correlation between a BLE device and firmware intel."""
    name = _norm(device.get("name"))
    vendor = _norm(device.get("vendor"))
    address = _norm(device.get("address") or device.get("mac"))
    fw_name = _norm(report.get("name"))
    fw_path = _norm(report.get("path"))
    strings = [_norm(s) for s in report.get("interesting_strings", [])]

    candidates = [name, vendor, address.replace(":", ""), address]
    haystack = " ".join([fw_name, fw_path, *strings])

    return any(c and len(c) >= 4 and c in haystack for c in candidates)


def link_firmware_to_devices(devices: list[dict], reports: list[dict]) -> list[dict]:
    """Attach firmware risk context to matching BLE devices."""
    linked = []

    for device in devices:
        enriched = dict(device)
        matches = []

        for report in reports:
            if firmware_matches_device(device, report):
                risk = report.get("risk", {})
                matches.append({
                    "firmware": report.get("name", "unknown firmware"),
                    "score": int(risk.get("score", 0) or 0),
                    "level": risk.get("level", "INFO"),
                    "markers": [
                        hit.get("marker")
                        for hit in risk.get("hits", [])[:8]
                        if hit.get("marker")
                    ],
                })

        if matches:
            max_score = max(m["score"] for m in matches)
            enriched["firmware_links"] = matches
            enriched["firmware_risk_score"] = max_score
            tags = set(enriched.get("tags", []))
            tags.add("FIRMWARE_LINKED")
            if max_score >= 60:
                tags.add("FIRMWARE_HIGH_RISK")
            elif max_score >= 25:
                tags.add("FIRMWARE_MEDIUM_RISK")
            enriched["tags"] = sorted(tags)

        linked.append(enriched)

    return linked
