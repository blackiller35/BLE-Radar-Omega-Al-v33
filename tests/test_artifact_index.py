import json
from pathlib import Path

from ble_radar import artifact_index


def test_build_artifact_index_collects_counts(monkeypatch):
    monkeypatch.setattr(artifact_index, "list_scan_manifests", lambda: [Path("a.json"), Path("b.json")])
    monkeypatch.setattr(artifact_index, "list_session_diff_reports", lambda: [Path("d1.json")])
    monkeypatch.setattr(artifact_index, "list_export_contexts", lambda: [Path("c1.json"), Path("c2.json"), Path("c3.json")])
    monkeypatch.setattr(artifact_index, "list_incident_packs", lambda: [Path("p1"), Path("p2")])

    index = artifact_index.build_artifact_index(stamp="2026-04-17_21-00-00")

    assert index["stamp"] == "2026-04-17_21-00-00"
    assert index["scan_manifests"]["count"] == 2
    assert index["scan_manifests"]["latest"] == "a.json"
    assert index["session_diff_reports"]["count"] == 1
    assert index["export_contexts"]["count"] == 3
    assert index["incident_packs"]["count"] == 2


def test_artifact_index_lines_formats_output():
    lines = artifact_index.artifact_index_lines(
        {
            "stamp": "2026-04-17_21-01-00",
            "scan_manifests": {"count": 2, "latest": "a.json"},
            "session_diff_reports": {"count": 1, "latest": "d1.json"},
            "export_contexts": {"count": 3, "latest": "c1.json"},
            "incident_packs": {"count": 2, "latest": "p1"},
        }
    )

    joined = "\n".join(lines)
    assert "Artifact Index" in joined
    assert "Scan manifests: 2 | latest=a.json" in joined
    assert "Incident packs: 2 | latest=p1" in joined


def test_save_artifact_index_writes_json_and_md(monkeypatch, tmp_path):
    monkeypatch.setattr(
        artifact_index,
        "build_artifact_index",
        lambda stamp=None: {
            "stamp": "2026-04-17_21-02-00",
            "scan_manifests": {"count": 2, "latest": "a.json"},
            "session_diff_reports": {"count": 1, "latest": "d1.json"},
            "export_contexts": {"count": 3, "latest": "c1.json"},
            "incident_packs": {"count": 2, "latest": "p1"},
        },
    )
    monkeypatch.setattr(
        artifact_index,
        "artifact_index_lines",
        lambda index: ["BLE Radar Omega AI - Artifact Index", "Stamp: 2026-04-17_21-02-00"],
    )

    result = artifact_index.save_artifact_index(output_root=tmp_path)

    assert result["json_path"].exists()
    assert result["md_path"].exists()

    payload = json.loads(result["json_path"].read_text(encoding="utf-8"))
    text = result["md_path"].read_text(encoding="utf-8")

    assert payload["stamp"] == "2026-04-17_21-02-00"
    assert "Artifact Index" in text


def test_list_artifact_indexes_returns_latest_first(tmp_path):
    a = tmp_path / "artifact_index_2026-04-17_21-00-00.json"
    b = tmp_path / "artifact_index_2026-04-17_21-01-00.md"
    a.write_text("{}", encoding="utf-8")
    b.write_text("{}", encoding="utf-8")

    items = artifact_index.list_artifact_indexes(root=tmp_path)

    assert items[0].name == "artifact_index_2026-04-17_21-01-00.md"
    assert items[1].name == "artifact_index_2026-04-17_21-00-00.json"


def test_list_artifact_indexes_returns_empty_when_missing(tmp_path):
    items = artifact_index.list_artifact_indexes(root=tmp_path / "missing")
    assert items == []


def test_readme_project_status_and_changelog_mentions_v101():
    readme = Path("README.md").read_text(encoding="utf-8")
    project = Path("PROJECT_STATUS.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "## Artifact index" in readme
    assert "v1.0.1 : artifact index patch" in project
    assert "## v1.0.1" in changelog
