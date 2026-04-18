import json
from pathlib import Path

from ble_radar import activity_timeline


def test_build_activity_timeline_collects_and_sorts(monkeypatch):
    monkeypatch.setattr(activity_timeline, "list_scan_manifests", lambda: [Path("scan_manifest_2026-04-17_21-20-00.json")])
    monkeypatch.setattr(activity_timeline, "list_session_diff_reports", lambda: [Path("session_diff_2026-04-17_21-21-00.md")])
    monkeypatch.setattr(activity_timeline, "list_export_contexts", lambda: [Path("export_context_2026-04-17_21-22-00.json")])
    monkeypatch.setattr(activity_timeline, "list_incident_packs", lambda: [Path("incident_pack_2026-04-17_21-23-00")])
    monkeypatch.setattr(activity_timeline, "list_artifact_indexes", lambda: [Path("artifact_index_2026-04-17_21-24-00.md")])

    events = activity_timeline.build_activity_timeline(limit=10)

    assert len(events) == 5
    assert events[0]["name"] == "artifact_index_2026-04-17_21-24-00.md"
    assert events[-1]["name"] == "scan_manifest_2026-04-17_21-20-00.json"


def test_build_activity_timeline_honors_limit(monkeypatch):
    monkeypatch.setattr(activity_timeline, "list_scan_manifests", lambda: [
        Path("scan_manifest_2026-04-17_21-20-00.json"),
        Path("scan_manifest_2026-04-17_21-19-00.json"),
    ])
    monkeypatch.setattr(activity_timeline, "list_session_diff_reports", lambda: [])
    monkeypatch.setattr(activity_timeline, "list_export_contexts", lambda: [])
    monkeypatch.setattr(activity_timeline, "list_incident_packs", lambda: [])
    monkeypatch.setattr(activity_timeline, "list_artifact_indexes", lambda: [])

    events = activity_timeline.build_activity_timeline(limit=1)

    assert len(events) == 1
    assert events[0]["name"] == "scan_manifest_2026-04-17_21-20-00.json"


def test_timeline_lines_formats_output():
    lines = activity_timeline.timeline_lines(
        [
            {
                "stamp": "2026-04-17_21-20-00",
                "kind": "scan_manifest",
                "name": "scan_manifest_2026-04-17_21-20-00.json",
                "path": "scan_manifest_2026-04-17_21-20-00.json",
            }
        ]
    )

    joined = "\n".join(lines)
    assert "Activity Timeline" in joined
    assert "Events: 1" in joined
    assert "scan_manifest_2026-04-17_21-20-00.json" in joined


def test_save_activity_timeline_writes_json_and_md(monkeypatch, tmp_path):
    monkeypatch.setattr(
        activity_timeline,
        "build_activity_timeline",
        lambda limit=20: [
            {
                "stamp": "2026-04-17_21-20-00",
                "kind": "scan_manifest",
                "name": "scan_manifest_2026-04-17_21-20-00.json",
                "path": "scan_manifest_2026-04-17_21-20-00.json",
            }
        ],
    )

    result = activity_timeline.save_activity_timeline(output_root=tmp_path)

    assert result["json_path"].exists()
    assert result["md_path"].exists()

    payload = json.loads(result["json_path"].read_text(encoding="utf-8"))
    text = result["md_path"].read_text(encoding="utf-8")

    assert len(payload["events"]) == 1
    assert "Activity Timeline" in text


def test_list_activity_timelines_returns_latest_first(tmp_path):
    a = tmp_path / "activity_timeline_2026-04-17_21-20-00.json"
    b = tmp_path / "activity_timeline_2026-04-17_21-21-00.md"
    a.write_text("{}", encoding="utf-8")
    b.write_text("{}", encoding="utf-8")

    items = activity_timeline.list_activity_timelines(root=tmp_path)

    assert items[0].name == "activity_timeline_2026-04-17_21-21-00.md"
    assert items[1].name == "activity_timeline_2026-04-17_21-20-00.json"


def test_readme_project_status_and_changelog_mentions_v104():
    readme = Path("README.md").read_text(encoding="utf-8")
    project = Path("PROJECT_STATUS.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "## Activity timeline" in readme
    assert "v1.0.4 : activity timeline patch" in project
    assert "## v1.0.4" in changelog
