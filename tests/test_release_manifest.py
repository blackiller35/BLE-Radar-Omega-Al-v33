from pathlib import Path

from ble_radar import release_manifest


def test_stable_release_manifest_reports_v100_ready():
    manifest = release_manifest.stable_release_manifest()

    assert manifest["version"] == "v1.0.0"
    assert manifest["stability"] == "stable"
    assert manifest["feature_count"] >= 10
    assert manifest["stable_feature_count"] == manifest["feature_count"]
    assert manifest["is_ready"] is True


def test_stable_release_manifest_contains_v040_and_v049():
    manifest = release_manifest.stable_release_manifest()
    versions = {item["version"] for item in manifest["features"]}

    assert "v0.4.0" in versions
    assert "v0.4.9" in versions


def test_release_lines_contains_header_and_ready_state():
    lines = release_manifest.release_lines()
    joined = "\n".join(lines)

    assert "BLE Radar Omega AI - Stable Release Manifest" in joined
    assert "Version: v1.0.0" in joined
    assert "Ready: yes" in joined


def test_v100_release_check_contains_expected_steps():
    text = Path("scripts/v100_release_check.sh").read_text(encoding="utf-8")

    assert "[1/5] Stable release manifest" in text
    assert "[2/5] Tests unitaires" in text
    assert "[3/5] Menu pipeline" in text
    assert "[4/5] Validation complémentaire" in text
    assert "[5/5] État Git" in text


def test_readme_mentions_v100_stable_release():
    text = Path("README.md").read_text(encoding="utf-8")

    assert "## Stable release v1.0.0" in text
    assert "./scripts/v100_release_check.sh" in text


def test_project_status_and_changelog_mention_v100():
    project = Path("PROJECT_STATUS.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "v1.0.0 : stable release finale" in project
    assert "## v1.0.0" in changelog
