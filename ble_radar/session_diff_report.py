from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ble_radar.session_diff import latest_session_diff, summary_lines


SESSION_DIFF_REPORTS_DIR = Path("reports/session_diffs")


def _ensure_session_diff_reports_dir() -> Path:
    SESSION_DIFF_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_DIFF_REPORTS_DIR


def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def build_latest_session_diff_report(root_manifests: Path | None = None) -> dict:
    diff = latest_session_diff(root=root_manifests)
    lines = summary_lines(diff)

    return {
        "stamp": _now_stamp(),
        "diff": diff,
        "lines": lines,
        "has_diff": bool(diff.get("has_diff", False)),
    }


def save_latest_session_diff_report(
    root_manifests: Path | None = None,
    output_root: Path | None = None,
) -> dict:
    payload = build_latest_session_diff_report(root_manifests=root_manifests)

    target_root = Path(output_root) if output_root else _ensure_session_diff_reports_dir()
    target_root.mkdir(parents=True, exist_ok=True)

    stamp = payload["stamp"]

    json_path = target_root / f"session_diff_{stamp}.json"
    md_path = target_root / f"session_diff_{stamp}.md"

    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    md_path.write_text("\n".join(payload["lines"]), encoding="utf-8")

    return {
        "json_path": json_path,
        "md_path": md_path,
        "payload": payload,
    }


def list_session_diff_reports(root: Path | None = None) -> list[Path]:
    target_root = Path(root) if root else _ensure_session_diff_reports_dir()
    if not target_root.exists():
        return []

    items = [p for p in target_root.glob("session_diff_*") if p.is_file()]
    items.sort(key=lambda p: p.name, reverse=True)
    return items
