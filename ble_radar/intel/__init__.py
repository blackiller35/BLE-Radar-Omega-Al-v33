from .risk_tags import build_risk_tags, risk_level_from_tags
from .pcap_intel import summarize_pcap, export_summary_json

# =========================
# TEMP ENGINE BRIDGE
# =========================


def build_intel(*args, **kwargs):
    return {}


def compare_device_sets(*args, **kwargs):
    return {}


# =========================
# MISSING FUNCTIONS (CRITICAL FIX)
# =========================


def get_vendor_summary(devices):
    summary = {}
    for d in devices or []:
        vendor = d.get("vendor") or "Unknown"
        summary[str(vendor)] = summary.get(str(vendor), 0) + 1

    return sorted(summary.items(), key=lambda x: x[1], reverse=True)


def get_tracker_candidates(devices):
    candidates = []

    for d in devices or []:
        flags = d.get("flags") or []
        name = str(d.get("name", "")).lower()
        vendor = str(d.get("vendor", "")).lower()

        if (
            "tracker" in name
            or "airtag" in name
            or "tile" in name
            or "smarttag" in name
            or "beacon" in name
            or "tracker" in vendor
            or "tile" in vendor
            or "apple" in vendor
            or "neartracking" in flags
        ):
            candidates.append(d)

    return candidates
