from ble_radar.config import STATE_DIR
from ble_radar.state import load_json, save_json

SAVED_QUERIES_FILE = STATE_DIR / "saved_queries.json"

if not SAVED_QUERIES_FILE.exists():
    save_json(SAVED_QUERIES_FILE, [])


def load_saved_queries():
    data = load_json(SAVED_QUERIES_FILE, [])
    return data if isinstance(data, list) else []


def save_saved_queries(data):
    cleaned = []
    seen = set()
    for item in data:
        q = str(item).strip()
        if not q or q in seen:
            continue
        seen.add(q)
        cleaned.append(q)
    save_json(SAVED_QUERIES_FILE, cleaned)


def add_saved_query(query: str):
    data = load_saved_queries()
    data.append(query)
    save_saved_queries(data)
    return load_saved_queries()


def remove_saved_query(index: int):
    data = load_saved_queries()
    if 0 <= index < len(data):
        data.pop(index)
    save_saved_queries(data)
    return load_saved_queries()
