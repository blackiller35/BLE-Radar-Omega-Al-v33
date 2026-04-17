from pathlib import Path


def test_v037_release_guard_contains_expected_steps():
    text = Path("scripts/v037_release_guard.sh").read_text(encoding="utf-8")

    assert "[1/6] Fichiers clés" in text
    assert "[2/6] Syntaxe shell" in text
    assert "[3/6] Workflow make" in text
    assert "[4/6] Validation complète" in text
    assert "[5/6] Milestone check + runtime dry-run" in text
    assert "[6/6] État Git" in text


def test_v037_release_guard_checks_core_modules():
    text = Path("scripts/v037_release_guard.sh").read_text(encoding="utf-8")

    assert "ble_radar/device_contract.py" in text
    assert "ble_radar/investigation.py" in text
    assert "ble_radar/incident_pack.py" in text
    assert "ble_radar/automation_safe.py" in text


def test_v037_release_guard_uses_make_and_milestone_checks():
    text = Path("scripts/v037_release_guard.sh").read_text(encoding="utf-8")

    assert "make -n help quickstart run test validate clean-runtime-dry" in text
    assert "./scripts/v030_milestone_check.sh" in text
    assert "./scripts/clean_runtime_artifacts.sh --dry-run" in text


def test_readme_mentions_release_guard():
    text = Path("README.md").read_text(encoding="utf-8")

    assert "## Release guard final" in text
    assert "./scripts/v037_release_guard.sh" in text
    assert "make validate" in text


def test_project_status_mentions_v037():
    text = Path("PROJECT_STATUS.md").read_text(encoding="utf-8")

    assert "v0.3.7 : release guard final" in text
    assert "./scripts/v037_release_guard.sh" in text


def test_changelog_mentions_v037():
    text = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "## v0.3.7" in text
    assert "release guard" in text.lower()
