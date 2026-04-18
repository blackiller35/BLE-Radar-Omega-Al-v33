from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ble_radar.device_contract import explain_device, normalize_device
from ble_radar.investigation import load_case, summarize_case
from ble_radar.session_diff import latest_session_diff, summary_lines as diff_summary_lines
from ble_radar.session_catalog import latest_session_overview, build_session_catalog


INCIDENT_PACKS_DIR = Path("reports/incident_packs")


def _ensure_incident_packs_dir() -> Path:
    INCIDENT_PACKS_DIR.mkdir(parents=True, exist_ok=True)
    return INCIDENT_PACKS_DIR


def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _device_matches(case_device: dict | None, candidate: dict) -> bool:
    if not case_device:
        return False

    c = normalize_device(candidate)
    ref = normalize_device(case_device)

    if ref.get("address") not in (None, "", "-") and c.get("address") == ref.get("address"):
        return True

    if ref.get("name") not in (None, "", "Inconnu") and c.get("name") == ref.get("name"):
        return True

    return False


def build_incident_pack(case_id: str, latest_devices: list[dict] | None = None, extra_meta: dict | None = None) -> dict:
    case = load_case(case_id)
    stamp = _now_stamp()
    pack_dir = _ensure_incident_packs_dir() / f"{case_id}_{stamp}"
    pack_dir.mkdir(parents=True, exist_ok=True)

    case_device = case.get("device")
    normalized_case_device = normalize_device(case_device) if case_device else None

    session_diff = latest_session_diff()
    session_overview = latest_session_overview()
    recent_sessions = build_session_catalog(limit=3)

    matches = []
    for item in latest_devices or []:
        if _device_matches(case_device, item):
            device = normalize_device(item)
            matches.append(
                {
                    "device": device,
                    "explanation": explain_device(device),
                }
            )

    manifest = {
        "case_id": case.get("id"),
        "title": case.get("title"),
        "status": case.get("status"),
        "created_at": case.get("created_at"),
        "updated_at": case.get("updated_at"),
        "pack_stamp": stamp,
        "notes_count": len(case.get("notes", [])),
        "case_device": normalized_case_device,
        "case_device_explanation": explain_device(normalized_case_device) if normalized_case_device else None,
        "latest_devices_count": len(latest_devices or []),
        "matched_devices_count": len(matches),
        "matched_devices": matches,
        "session_diff": session_diff,
        "session_overview": session_overview,
        "recent_sessions": recent_sessions,
        "extra_meta": extra_meta or {},
    }

    manifest_path = pack_dir / "incident_pack.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = summarize_case(case)
    lines.append("")
    lines.append("Incident pack")
    lines.append(f"Pack stamp: {stamp}")
    lines.append(f"Matched devices: {len(matches)}")

    if normalized_case_device:
        lines.append("")
        lines.append("Case device explanation:")
        lines.append(manifest["case_device_explanation"]["summary"])

    lines.append("")
    lines.append("Latest session overview:")
    lines.append(f"Stamp: {session_overview.get('stamp', 'unknown')}")
    lines.append(f"Devices: {session_overview.get('device_count', 0)}")
    lines.append(f"Critical: {session_overview.get('critical', 0)}")
    lines.append(f"Watch hits: {session_overview.get('watch_hits', 0)}")
    lines.append(f"Trackers: {session_overview.get('tracker_candidates', 0)}")
    lines.append(f"Top vendor: {session_overview.get('top_vendor', 'Unknown')}")
    lines.append(
        f"Top device: {session_overview.get('top_device_name', 'Inconnu')} "
        f"({session_overview.get('top_device_score', 0)})"
    )

    if recent_sessions:
        lines.append("")
        lines.append("Recent sessions:")
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
        lines.append("")
        lines.append("Recent sessions: none")

    if session_diff.get("has_diff", False):
        lines.append("")
        lines.append("Session diff:")
        lines.extend(diff_summary_lines(session_diff)[1:])
    else:
        lines.append("")
        lines.append("Session diff: none")

    if matches:
        lines.append("")
        lines.append("Matched devices:")
        for match in matches:
            d = match["device"]
            lines.append(
                f"- {d.get('name', 'Inconnu')} | {d.get('address', '-')} | "
                f"vendor={d.get('vendor', 'Unknown')} | {match['explanation']['summary']}"
            )
    else:
        lines.append("")
        lines.append("Matched devices: none")

    summary_path = pack_dir / "incident_summary.md"
    summary_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "pack_dir": pack_dir,
        "manifest_path": manifest_path,
        "summary_path": summary_path,
        "manifest": manifest,
    }


def list_incident_packs() -> list[Path]:
    root = _ensure_incident_packs_dir()
    items = [p for p in root.iterdir() if p.is_dir()]
    items.sort(key=lambda p: p.name, reverse=True)
    return items
