from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from ble_radar.artifact_index import list_artifact_indexes
from ble_radar.export_context import list_export_contexts
from ble_radar.incident_pack import list_incident_packs
from ble_radar.scan_manifest import list_scan_manifests
from ble_radar.session_diff_report import list_session_diff_reports


ACTIVITY_TIMELINE_DIR = Path("reports/timeline")
STAMP_RE = re.compile(r"(20\d{2}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})")


def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _ensure_activity_timeline_dir() -> Path:
    ACTIVITY_TIMELINE_DIR.mkdir(parents=True, exist_ok=True)
    return ACTIVITY_TIMELINE_DIR


def _extract_stamp(name: str) -> str:
    match = STAMP_RE.search(name)
    return match.group(1) if match else "unknown"


def _event(kind: str, path: Path) -> dict:
    return {
        "kind": kind,
        "name": path.name,
        "path": str(path),
        "stamp": _extract_stamp(path.name),
    }


def build_activity_timeline(limit: int = 20) -> list[dict]:
    events: list[dict] = []

    for path in list_scan_manifests():
        events.append(_event("scan_manifest", path))
    for path in list_session_diff_reports():
        events.append(_event("session_diff_report", path))
    for path in list_export_contexts():
        events.append(_event("export_context", path))
    for path in list_incident_packs():
        events.append(_event("incident_pack", path))
    for path in list_artifact_indexes():
        events.append(_event("artifact_index", path))

    events.sort(
        key=lambda item: (
            item.get("stamp") != "unknown",
            item.get("stamp", ""),
            item.get("kind", ""),
            item.get("name", ""),
        ),
        reverse=True,
    )
    return events[:limit]


def timeline_lines(events: list[dict]) -> list[str]:
    lines = [
        "BLE Radar Omega AI - Activity Timeline",
        f"Events: {len(events)}",
    ]
    if not events:
        lines.append("No activity available.")
        return lines

    lines.append("")
    for item in events:
        lines.append(
            f"- {item['stamp']} | {item['kind']} | {item['name']}"
        )
    return lines


def save_activity_timeline(limit: int = 20, output_root: Path | None = None) -> dict:
    events = build_activity_timeline(limit=limit)
    stamp = _now_stamp()

    root = Path(output_root) if output_root else _ensure_activity_timeline_dir()
    root.mkdir(parents=True, exist_ok=True)

    json_path = root / f"activity_timeline_{stamp}.json"
    md_path = root / f"activity_timeline_{stamp}.md"

    payload = {
        "stamp": stamp,
        "limit": limit,
        "events": events,
    }

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text("\n".join(timeline_lines(events)), encoding="utf-8")

    return {
        "json_path": json_path,
        "md_path": md_path,
        "payload": payload,
    }


def list_activity_timelines(root: Path | None = None) -> list[Path]:
    target_root = Path(root) if root else _ensure_activity_timeline_dir()
    if not target_root.exists():
        return []

    items = [p for p in target_root.glob("activity_timeline_*") if p.is_file()]
    items.sort(key=lambda p: p.name, reverse=True)
    return items
