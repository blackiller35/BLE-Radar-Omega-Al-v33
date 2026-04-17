from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from ble_radar.device_contract import normalize_device


CASES_DIR = Path("history/cases")
VALID_CASE_STATUS = {"open", "watch", "closed"}


def _ensure_cases_dir() -> Path:
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    return CASES_DIR


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slugify(value: str) -> str:
    value = (value or "case").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "case"


def _case_path(case_id: str) -> Path:
    return _ensure_cases_dir() / f"{case_id}.json"


def create_case(title: str, device: dict | None = None, context: dict | None = None) -> dict:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    case_id = f"case_{stamp}_{_slugify(title)}"
    now = _now_iso()

    data = {
        "id": case_id,
        "title": title.strip() if title else "Untitled Case",
        "status": "open",
        "created_at": now,
        "updated_at": now,
        "device": normalize_device(device) if device else None,
        "context": context or {},
        "notes": [],
    }

    _case_path(case_id).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def load_case(case_id: str) -> dict:
    path = _case_path(case_id)
    return json.loads(path.read_text(encoding="utf-8"))


def save_case(data: dict) -> dict:
    data = dict(data)
    data["updated_at"] = _now_iso()
    _case_path(data["id"]).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def list_cases() -> list[dict]:
    _ensure_cases_dir()
    items = []
    for path in CASES_DIR.glob("case_*.json"):
        try:
            items.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue

    items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return items


def add_case_note(case_id: str, note: str) -> dict:
    data = load_case(case_id)
    data.setdefault("notes", []).append(
        {
            "created_at": _now_iso(),
            "text": note.strip(),
        }
    )
    return save_case(data)


def set_case_status(case_id: str, status: str) -> dict:
    status = (status or "").strip().lower()
    if status not in VALID_CASE_STATUS:
        raise ValueError(f"invalid case status: {status}")

    data = load_case(case_id)
    data["status"] = status
    return save_case(data)


def summarize_case(case: dict) -> list[str]:
    device = case.get("device") or {}
    notes = case.get("notes") or []

    lines = [
        f"Case: {case.get('title', '-')}",
        f"ID: {case.get('id', '-')}",
        f"Status: {case.get('status', '-')}",
        f"Created: {case.get('created_at', '-')}",
        f"Updated: {case.get('updated_at', '-')}",
    ]

    if device:
        lines.append(
            f"Device: {device.get('name', 'Inconnu')} | {device.get('address', '-')} | "
            f"vendor={device.get('vendor', 'Unknown')} | profile={device.get('profile', 'general_ble')}"
        )

    lines.append(f"Notes: {len(notes)}")
    if notes:
        lines.append(f"Last note: {notes[-1].get('text', '')}")

    return lines
