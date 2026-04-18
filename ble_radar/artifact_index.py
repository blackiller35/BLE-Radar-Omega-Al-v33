from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ble_radar.export_context import list_export_contexts
from ble_radar.incident_pack import list_incident_packs
from ble_radar.scan_manifest import list_scan_manifests
from ble_radar.session_diff_report import list_session_diff_reports


ARTIFACT_INDEX_DIR = Path("reports/index")


def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _ensure_artifact_index_dir() -> Path:
    ARTIFACT_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACT_INDEX_DIR


def _latest_name(paths: list[Path]) -> str | None:
    if not paths:
        return None
    return paths[0].name


def build_artifact_index(stamp: str | None = None) -> dict:
    scan_manifests = list_scan_manifests()
    session_diff_reports = list_session_diff_reports()
    export_contexts = list_export_contexts()
    incident_packs = list_incident_packs()

    return {
        "stamp": stamp or _now_stamp(),
        "scan_manifests": {
            "count": len(scan_manifests),
            "latest": _latest_name(scan_manifests),
        },
        "session_diff_reports": {
            "count": len(session_diff_reports),
            "latest": _latest_name(session_diff_reports),
        },
        "export_contexts": {
            "count": len(export_contexts),
            "latest": _latest_name(export_contexts),
        },
        "incident_packs": {
            "count": len(incident_packs),
            "latest": _latest_name(incident_packs),
        },
    }


def artifact_index_lines(index: dict) -> list[str]:
    lines = [
        "BLE Radar Omega AI - Artifact Index",
        f"Stamp: {index.get('stamp', 'unknown')}",
        "",
        "Artifacts:",
        f"- Scan manifests: {index['scan_manifests']['count']} | latest={index['scan_manifests']['latest'] or 'none'}",
        f"- Session diff reports: {index['session_diff_reports']['count']} | latest={index['session_diff_reports']['latest'] or 'none'}",
        f"- Export contexts: {index['export_contexts']['count']} | latest={index['export_contexts']['latest'] or 'none'}",
        f"- Incident packs: {index['incident_packs']['count']} | latest={index['incident_packs']['latest'] or 'none'}",
    ]
    return lines


def save_artifact_index(stamp: str | None = None, output_root: Path | None = None) -> dict:
    index = build_artifact_index(stamp=stamp)
    root = Path(output_root) if output_root else _ensure_artifact_index_dir()
    root.mkdir(parents=True, exist_ok=True)

    idx_stamp = index["stamp"]
    json_path = root / f"artifact_index_{idx_stamp}.json"
    md_path = root / f"artifact_index_{idx_stamp}.md"

    json_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text("\n".join(artifact_index_lines(index)), encoding="utf-8")

    return {
        "json_path": json_path,
        "md_path": md_path,
        "index": index,
    }


def list_artifact_indexes(root: Path | None = None) -> list[Path]:
    target_root = Path(root) if root else _ensure_artifact_index_dir()
    if not target_root.exists():
        return []

    items = [p for p in target_root.glob("artifact_index_*") if p.is_file()]
    items.sort(key=lambda p: p.name, reverse=True)
    return items
