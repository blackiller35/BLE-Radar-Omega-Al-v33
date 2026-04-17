from pathlib import Path


def test_quickstart_script_contains_expected_commands():
    text = Path("scripts/quickstart.sh").read_text(encoding="utf-8")

    assert "python3 -m venv .venv" in text
    assert "pip install -r requirements.txt" in text
    assert "python -m ble_radar.app" in text
    assert "make help" in text


def test_makefile_contains_expected_targets():
    text = Path("Makefile").read_text(encoding="utf-8")

    for target in (
        "help:",
        "quickstart:",
        "venv:",
        "install:",
        "run:",
        "test:",
        "menu-test:",
        "validate:",
        "clean-runtime-dry:",
        "clean-runtime:",
    ):
        assert target in text


def test_readme_mentions_dev_quickstart():
    text = Path("README.md").read_text(encoding="utf-8")

    assert "## Quickstart développeur" in text
    assert "./scripts/quickstart.sh" in text
    assert "make validate" in text
