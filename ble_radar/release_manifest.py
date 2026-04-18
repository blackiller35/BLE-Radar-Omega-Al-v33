from __future__ import annotations

from copy import deepcopy


STABLE_FEATURES = [
    {"key": "baseline", "label": "Operator baseline", "version": "v0.4.0", "status": "stable"},
    {"key": "scan_manifests", "label": "Scan manifests", "version": "v0.4.1", "status": "stable"},
    {"key": "session_catalog", "label": "Session catalog", "version": "v0.4.2", "status": "stable"},
    {"key": "session_diff", "label": "Session diff", "version": "v0.4.3", "status": "stable"},
    {"key": "session_diff_report", "label": "Session diff reports", "version": "v0.4.4", "status": "stable"},
    {"key": "dashboard_diff", "label": "Dashboard session diff", "version": "v0.4.5", "status": "stable"},
    {"key": "incident_diff", "label": "Incident packs + session diff", "version": "v0.4.6", "status": "stable"},
    {"key": "dashboard_catalog", "label": "Dashboard session catalog", "version": "v0.4.7", "status": "stable"},
    {"key": "incident_catalog", "label": "Incident packs + session catalog", "version": "v0.4.8", "status": "stable"},
    {"key": "context_bundle", "label": "Export context bundle", "version": "v0.4.9", "status": "stable"},
]


def stable_release_manifest() -> dict:
    stable_count = sum(1 for item in STABLE_FEATURES if item.get("status") == "stable")
    return {
        "version": "v1.0.0",
        "stability": "stable",
        "feature_count": len(STABLE_FEATURES),
        "stable_feature_count": stable_count,
        "is_ready": stable_count == len(STABLE_FEATURES),
        "features": deepcopy(STABLE_FEATURES),
    }


def release_lines() -> list[str]:
    manifest = stable_release_manifest()
    lines = [
        "BLE Radar Omega AI - Stable Release Manifest",
        f"Version: {manifest['version']}",
        f"Stability: {manifest['stability']}",
        f"Stable features: {manifest['stable_feature_count']}/{manifest['feature_count']}",
        f"Ready: {'yes' if manifest['is_ready'] else 'no'}",
        "Features:",
    ]
    for item in manifest["features"]:
        lines.append(f"- {item['version']} | {item['label']} | {item['status']}")
    return lines
