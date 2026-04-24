from __future__ import annotations

import time
from ble_radar.intel.osint_sigint_tools import get_intel_tools


def _normalize_input(device):
    # Support list[str] (tests) OR dict (real pipeline)
    if isinstance(device, list):
        return {
            "name": "",
            "hits": 0,
            "risk_tags": device,
        }
    return device


def _with_tools(context: dict, tags: set[str]) -> dict:
    context["intel_tools"] = get_intel_tools(list(tags))
    context["level"] = context.get("severity", "low")
    context["recommendation"] = " ".join(context.get("recommended_actions", []))
    return context


def build_threat_context(device) -> dict:
    device = _normalize_input(device)

    tags = set(device.get("risk_tags") or [])
    name = str(device.get("name", "")).lower()
    hits = int(device.get("hits", 0) or 0)

    # HIGH - tracking
    if "TRACKING_SUSPECT" in tags or "PRIORITY_REVIEW" in tags:
        return _with_tools({
            "severity": "high",
            "summary": "Randomized tracking-like BLE behavior detected",
            "explanation": "Persistent randomized BLE activity suggests tracking behavior.",
            "reasons": ["tracking-like behavior detected"],
            "recommended_actions": ["Review device history", "Monitor physical proximity"],
        }, tags)

    # HIGH - persistent strong activity
    if hits >= 1000:
        return _with_tools({
            "severity": "high",
            "summary": "High persistent BLE activity",
            "explanation": "Device shows repeated strong presence.",
            "reasons": ["activité BLE élevée détectée"],
            "recommended_actions": ["surveiller la réapparition sur plusieurs scans", "corréler avec appareils connus"],
        }, tags)

    # MEDIUM - tracker profile
    if "tile" in name or "airtag" in name or "tracker" in name:
        return _with_tools({
            "severity": "medium",
            "summary": "Possible tracking device",
            "explanation": "Device matches known tracker patterns.",
            "reasons": ["profil compatible avec balise ou tracker BLE", "signal proche ou fort"],
            "recommended_actions": ["Verify ownership", "Check for unwanted tracking"],
        }, tags)

    # MEDIUM - persistent
    if "PERSISTENT_DEVICE" in tags or "HIGH_ACTIVITY" in tags:
        return _with_tools({
            "severity": "medium",
            "summary": "Persistent BLE activity",
            "explanation": "Device appears repeatedly.",
            "reasons": ["activité persistante détectée"],
            "recommended_actions": ["Monitor over time"],
        }, tags)

    # LOW
    return _with_tools({
        "severity": "low",
        "summary": "No immediate threat",
        "explanation": "No suspicious behavior detected.",
        "reasons": [],
        "recommended_actions": [],
    }, tags)


def build_threat_contexts(devices: list[dict]) -> list[dict]:
    return [
        {
            "address": device.get("address"),
            "name": device.get("name"),
            "risk_tags": device.get("risk_tags", []),
            "threat_context": build_threat_context(device),
        }
        for device in devices
    ]


def enrich_threat_contexts(contexts: list[dict]) -> list[dict]:
    return [
        {
            **ctx,
            "enriched": True,
            "omega_timestamp": time.time(),
        }
        for ctx in contexts
    ]
