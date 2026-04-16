from ble_radar.state import load_scan_history
from ble_radar.selectors import sort_by_score


def list_recent_scans(limit=15):
    history = load_scan_history()
    indexed = list(enumerate(history))
    indexed.reverse()
    return indexed[:limit]


def get_scan_by_history_index(index: int):
    history = load_scan_history()
    if 0 <= index < len(history):
        return history[index]
    return None


def scan_summary_lines(scan: dict):
    return [
        f"stamp: {scan.get('stamp', scan.get('timestamp', '-'))}",
        f"count: {scan.get('count', 0)}",
        f"critical: {scan.get('critical', 0)}",
        f"high: {scan.get('high', 0)}",
        f"medium: {scan.get('medium', 0)}",
    ]


def scan_devices(scan: dict):
    return sort_by_score(scan.get("devices", []))
