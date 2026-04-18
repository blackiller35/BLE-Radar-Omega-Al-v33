import json
from pathlib import Path

from ble_radar import artifact_index


def test_build_artifact_index_contains_cross_links(monkeypatch):
    monkeypatch.setattr(artifact_index, "list_scan_manifests", lambda: [Path("scan_manifest_a.json")])
    monkeypatch.setattr(artifact_index, "list_session_diff_reports", lambda: [Path("session_diff_a.md")])
    monkeypatch.setattr(artifact_index, "list_export_contexts", lambda: [Path("export_context_a.json")])
    monkeypatch.setattr(artifact_index, "list_incident_packs", lambda: [Path("incident_pack_a")])

    index = artifact_index.build_artifact_index(stamp="2026-04-17_21-10-00")

    assert index["cross_links"]["overview_chain"] == [
        "scan_manifest_a.json",
        "session_diff_a.md",
        "export_context_a.json",
    ]
    assert index["cross_links"]["incident_chain"] == [
        "incident_pack_a",
        "export_context_a.json",
    ]
    assert index["cross_links"]["is_complete"] is True


def test_build_artifact_cross_links_handles_partial_context():
    index = {
        "scan_manifests": {"count": 1, "latest": "scan_manifest_a.json"},
        "session_diff_reports": {"count": 0, "latest": None},
        "export_contexts": {"count": 1, "latest": "export_context_a.json"},
        "incident_packs": {"count": 0, "latest": None},
    }

    links = artifact_index.build_artifact_cross_links(index)

    assert links["overview_chain"] == ["scan_manifest_a.json", "export_context_a.json"]
    assert links["incident_chain"] == ["export_context_a.json"]
    assert links["is_complete"] is False


def test_artifact_index_lines_formats_cross_links():
    lines = artifact_index.artifact_index_lines(
        {
            "stamp": "2026-04-17_21-11-00",
            "scan_manifests": {"count": 1, "latest": "scan_manifest_a.json"},
            "session_diff_reports": {"count": 1, "latest": "session_diff_a.md"},
            "export_contexts": {"count": 1, "latest": "export_context_a.json"},
            "incident_packs": {"count": 1, "latest": "incident_pack_a"},
            "cross_links": {
                "overview_chain": ["scan_manifest_a.json", "session_diff_a.md", "export_context_a.json"],
                "incident_chain": ["incident_pack_a", "export_context_a.json"],
                "workspace_chain": ["scan_manifest_a.json", "session_diff_a.md", "export_context_a.json", "incident_pack_a"],
                "is_complete": True,
            },
        }
    )

    joined = "\n".join(lines)
    assert "Cross-links:" in joined
    assert "Overview chain: scan_manifest_a.json -> session_diff_a.md -> export_context_a.json" in joined
    assert "Incident chain: incident_pack_a -> export_context_a.json" in joined
    assert "Complete: yes" in joined


def test_save_artifact_index_writes_cross_links(monkeypatch, tmp_path):
    monkeypatch.setattr(
        artifact_index,
        "build_artifact_index",
        lambda stamp=None: {
            "stamp": "2026-04-17_21-12-00",
            "scan_manifests": {"count": 1, "latest": "scan_manifest_a.json"},
            "session_diff_reports": {"count": 1, "latest": "session_diff_a.md"},
            "export_contexts": {"count": 1, "latest": "export_context_a.json"},
            "incident_packs": {"count": 1, "latest": "incident_pack_a"},
            "cross_links": {
                "overview_chain": ["scan_manifest_a.json", "session_diff_a.md", "export_context_a.json"],
                "incident_chain": ["incident_pack_a", "export_context_a.json"],
                "workspace_chain": ["scan_manifest_a.json", "session_diff_a.md", "export_context_a.json", "incident_pack_a"],
                "is_complete": True,
            },
        },
    )
    monkeypatch.setattr(
        artifact_index,
        "artifact_index_lines",
        lambda index: ["BLE Radar Omega AI - Artifact Index", "Cross-links:", "Complete: yes"],
    )

    result = artifact_index.save_artifact_index(output_root=tmp_path)

    assert result["json_path"].exists()
    assert result["md_path"].exists()

    payload = json.loads(result["json_path"].read_text(encoding="utf-8"))
    text = result["md_path"].read_text(encoding="utf-8")

    assert payload["cross_links"]["is_complete"] is True
    assert "Complete: yes" in text


def test_v103_links_check_contains_expected_steps():
    text = Path("scripts/v103_links_check.sh").read_text(encoding="utf-8")

    assert "[1/2] Artifact links" in text
    assert "[2/2] État Git" in text


def test_readme_project_status_and_changelog_mentions_v103():
    readme = Path("README.md").read_text(encoding="utf-8")
    project = Path("PROJECT_STATUS.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "## Artifact cross-links" in readme
    assert "v1.0.3 : artifact cross-links patch" in project
    assert "## v1.0.3" in changelog
