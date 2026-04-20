from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ble_radar.security import build_security_context
from ble_radar.security.policy import require_operator
from ble_radar.session_catalog import build_session_catalog, latest_session_overview
from ble_radar.session_diff import (
    latest_session_diff,
    summary_lines as diff_summary_lines,
)


EXPORT_CONTEXT_DIR = Path("reports/context")


def _ensure_export_context_dir() -> Path:
    EXPORT_CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORT_CONTEXT_DIR


def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def build_export_context(stamp: str | None = None, recent_limit: int = 5) -> dict:
    ctx_stamp = stamp or _now_stamp()
    session_overview = latest_session_overview()
    recent_sessions = build_session_catalog(limit=recent_limit)
    session_diff = latest_session_diff()

    return {
        "stamp": ctx_stamp,
        "session_overview": session_overview,
        "recent_sessions": recent_sessions,
        "session_diff": session_diff,
        "recent_limit": recent_limit,
    }


def context_markdown_lines(context: dict) -> list[str]:
    overview = context.get("session_overview", {}) or {}
    recent_sessions = context.get("recent_sessions", []) or []
    session_diff = context.get("session_diff", {}) or {}

    lines = [
        "# BLE Radar Omega AI - Export Context",
        "",
        "## Latest session overview",
        f"- Stamp: {overview.get('stamp', 'unknown')}",
        f"- Devices: {overview.get('device_count', 0)}",
        f"- Critical: {overview.get('critical', 0)}",
        f"- Watch hits: {overview.get('watch_hits', 0)}",
        f"- Trackers: {overview.get('tracker_candidates', 0)}",
        f"- Top vendor: {overview.get('top_vendor', 'Unknown')}",
        f"- Top device: {overview.get('top_device_name', 'Inconnu')} ({overview.get('top_device_score', 0)})",
        "",
        "## Recent sessions",
    ]

    if recent_sessions:
        for row in recent_sessions:
            lines.append(
                f"- {row.get('stamp', 'unknown')} | "
                f"devices={row.get('device_count', 0)} | "
                f"critical={row.get('critical', 0)} | "
                f"watch_hits={row.get('watch_hits', 0)} | "
                f"trackers={row.get('tracker_candidates', 0)} | "
                f"top_vendor={row.get('top_vendor', 'Unknown')}"
            )
    else:
        lines.append("- none")

    lines.append("")
    lines.append("## Session diff")

    if session_diff.get("has_diff", False):
        lines.extend(diff_summary_lines(session_diff)[1:])
    else:
        lines.append("- none")

    return lines


def save_export_context(
    stamp: str | None = None,
    recent_limit: int = 5,
    output_root: Path | None = None,
) -> dict:
    security_context = build_security_context()
    require_operator(security_context)

    context = build_export_context(stamp=stamp, recent_limit=recent_limit)

    root = Path(output_root) if output_root else _ensure_export_context_dir()
    root.mkdir(parents=True, exist_ok=True)

    ctx_stamp = context["stamp"]
    json_path = root / f"export_context_{ctx_stamp}.json"
    md_path = root / f"export_context_{ctx_stamp}.md"

    json_path.write_text(
        json.dumps(context, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    md_path.write_text("\n".join(context_markdown_lines(context)), encoding="utf-8")

    return {
        "json_path": json_path,
        "md_path": md_path,
        "context": context,
    }


def list_export_contexts(root: Path | None = None) -> list[Path]:
    target_root = Path(root) if root else _ensure_export_context_dir()
    if not target_root.exists():
        return []

    items = [p for p in target_root.glob("export_context_*") if p.is_file()]
    items.sort(key=lambda p: p.name, reverse=True)
    return items
