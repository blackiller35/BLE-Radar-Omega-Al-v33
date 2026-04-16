from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT_DIR / "reports"
HISTORY_DIR = ROOT_DIR / "history"
STATE_DIR = ROOT_DIR / "state"

WHITELIST_FILE = STATE_DIR / "whitelist.json"
WATCHLIST_FILE = STATE_DIR / "watchlist.json"
LIVE_HISTORY_FILE = STATE_DIR / "live_devices.json"
LAST_SCAN_FILE = STATE_DIR / "last_scan.json"
SCAN_HISTORY_FILE = HISTORY_DIR / "scan_history.json"
TRENDS_FILE = HISTORY_DIR / "trends.json"

LEGACY_WHITELIST_FILE = HISTORY_DIR / "whitelist.json"
LEGACY_WATCHLIST_FILE = HISTORY_DIR / "watchlist.json"
LEGACY_LIVE_HISTORY_FILE = HISTORY_DIR / "live_devices.json"
LEGACY_LAST_SCAN_FILE = HISTORY_DIR / "last_scan.json"

QUICK_SCAN_SECONDS = 3
FULL_SCAN_SECONDS = 5
LIVE_SCAN_SECONDS = 3

ALERT_MEDIUM = 35
ALERT_HIGH = 60
ALERT_CRITICAL = 82

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)
