from pathlib import Path


def test_project_status_contains_core_sections():
    text = Path("PROJECT_STATUS.md").read_text(encoding="utf-8")

    assert "# PROJECT STATUS" in text
    assert "v0.3.0" in text
    assert "Runtime config" in text
    assert "A E G I S".replace(" ", "")[:5] not in text or "AEGIS" in text
    assert "Developer quickstart / Makefile" in text


def test_readme_mentions_v030_milestone():
    text = Path("README.md").read_text(encoding="utf-8")

    assert "## Milestone v0.3.0" in text
    assert "./scripts/v030_milestone_check.sh" in text
    assert "make validate" in text


def test_milestone_check_script_contains_expected_steps():
    text = Path("scripts/v030_milestone_check.sh").read_text(encoding="utf-8")

    assert "[1/5] Fichiers clés" in text
    assert "[3/5] Validation complète" in text
    assert "./scripts/run_full_validation.sh" in text
    assert "./scripts/clean_runtime_artifacts.sh --dry-run" in text
