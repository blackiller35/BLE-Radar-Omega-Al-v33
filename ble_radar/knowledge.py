from datetime import datetime
import unicodedata

from ble_radar.config import STATE_DIR
from ble_radar.state import load_json, save_json

KNOWLEDGE_FILE = STATE_DIR / "device_knowledge.json"

if not KNOWLEDGE_FILE.exists():
    save_json(KNOWLEDGE_FILE, {})


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def norm_addr(addr: str) -> str:
    return str(addr or "").upper().strip()


def norm_text(text: str) -> str:
    text = str(text or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def load_knowledge():
    data = load_json(KNOWLEDGE_FILE, {})
    return data if isinstance(data, dict) else {}


def save_knowledge(data):
    save_json(KNOWLEDGE_FILE, data)


def _trust_from_record(record: dict) -> str:
    label = str(record.get("manual_label", "")).strip().lower()
    if label in {"friendly", "known", "suspicious", "critical"}:
        return label

    if record.get("watch_hits", 0) >= 1:
        return "critical"
    if record.get("critical_hits", 0) >= 1:
        return "critical"
    if record.get("alerts", 0) >= 3:
        return "suspicious"
    if record.get("max_score", 0) >= 75:
        return "suspicious"
    if record.get("sightings", 0) >= 4:
        return "known"
    return "unknown"


def get_record(address: str):
    data = load_knowledge()
    return data.get(norm_addr(address))


def upsert_observation(device: dict):
    data = load_knowledge()
    addr = norm_addr(device.get("address"))
    if not addr or addr == "-":
        return None

    rec = data.get(addr, {
        "address": addr,
        "first_seen": _now(),
        "last_seen": _now(),
        "sightings": 0,
        "names": [],
        "vendors": [],
        "profiles": [],
        "watch_hits": 0,
        "alerts": 0,
        "critical_hits": 0,
        "max_score": 0,
        "last_score": 0,
        "manual_label": "",
        "note": "",
    })

    rec["last_seen"] = _now()
    rec["sightings"] = int(rec.get("sightings", 0)) + 1

    name = str(device.get("name", "Inconnu"))
    vendor = str(device.get("vendor", "Unknown"))
    profile = str(device.get("profile", "general_ble"))
    score = int(device.get("final_score", device.get("score", 0)))
    alert = str(device.get("alert_level", "faible"))

    if name and name not in rec.get("names", []):
        rec.setdefault("names", []).append(name)
    if vendor and vendor not in rec.get("vendors", []):
        rec.setdefault("vendors", []).append(vendor)
    if profile and profile not in rec.get("profiles", []):
        rec.setdefault("profiles", []).append(profile)

    if device.get("watch_hit"):
        rec["watch_hits"] = int(rec.get("watch_hits", 0)) + 1

    if alert in ("moyen", "élevé", "critique"):
        rec["alerts"] = int(rec.get("alerts", 0)) + 1
    if alert == "critique":
        rec["critical_hits"] = int(rec.get("critical_hits", 0)) + 1

    rec["max_score"] = max(int(rec.get("max_score", 0)), score)
    rec["last_score"] = score
    rec["last_alert_level"] = alert
    rec["last_vendor"] = vendor
    rec["last_profile"] = profile
    rec["last_name"] = name
    rec["trust_label"] = _trust_from_record(rec)

    data[addr] = rec
    save_knowledge(data)
    return rec


def sync_current_devices(devices: list[dict]):
    out = []
    for d in devices:
        rec = upsert_observation(d)
        if rec:
            out.append(rec)
    return out


def set_manual_label(address: str, label: str, note: str = ""):
    data = load_knowledge()
    addr = norm_addr(address)
    if not addr:
        return None

    rec = data.get(addr, {
        "address": addr,
        "first_seen": _now(),
        "last_seen": _now(),
        "sightings": 0,
        "names": [],
        "vendors": [],
        "profiles": [],
        "watch_hits": 0,
        "alerts": 0,
        "critical_hits": 0,
        "max_score": 0,
        "last_score": 0,
        "manual_label": "",
        "note": "",
    })

    rec["manual_label"] = str(label or "").strip().lower()
    if note:
        rec["note"] = str(note)
    rec["trust_label"] = _trust_from_record(rec)
    data[addr] = rec
    save_knowledge(data)
    return rec


def search_known_devices(query: str, limit: int = 20):
    data = load_knowledge()
    q = norm_text(query)
    rows = []

    for addr, rec in data.items():
        hay = " ".join([
            addr,
            " ".join(rec.get("names", [])),
            " ".join(rec.get("vendors", [])),
            " ".join(rec.get("profiles", [])),
            rec.get("manual_label", ""),
            rec.get("note", ""),
            rec.get("trust_label", ""),
        ])
        if not q or q in norm_text(hay):
            rows.append(rec)

    rows.sort(
        key=lambda x: (
            {"critical": 3, "suspicious": 2, "known": 1, "friendly": 0, "unknown": -1}.get(x.get("trust_label", "unknown"), -1),
            x.get("sightings", 0),
            x.get("max_score", 0),
        ),
        reverse=True,
    )
    return rows[:limit]


def top_known_devices(limit: int = 20):
    return search_known_devices("", limit)
