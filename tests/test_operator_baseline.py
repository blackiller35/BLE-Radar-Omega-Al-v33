from pathlib import Path

from ble_radar import operator_baseline


def test_feature_matrix_contains_expected_keys():
    items = operator_baseline.feature_matrix()

    assert len(items) >= 8
    assert any(x["key"] == "device_contract" for x in items)
    assert any(x["key"] == "dashboard_pro" for x in items)
    assert any(x["key"] == "incident_packs" for x in items)
    assert any(x["key"] == "automation_safe" for x in items)


def test_baseline_summary_reports_v040_ready_state():
    summary = operator_baseline.baseline_summary()

    assert summary["milestone"] == "v0.4.0"
    assert summary["total_features"] >= 8
    assert summary["ready_features"] == summary["total_features"]
    assert summary["is_ready"] is True


def test_summary_lines_contains_operator_baseline_header():
    lines = operator_baseline.summary_lines()
    joined = "\n".join(lines)

    assert "BLE Radar Omega AI - Operator Baseline" in joined
    assert "Milestone: v0.4.0" in joined
    assert "Ready: yes" in joined
    assert "Incident packs" in joined


def test_v040_script_contains_expected_steps():
    text = Path("scripts/v040_operator_readiness.sh").read_text(encoding="utf-8")

    assert "[1/5] Baseline opérateur" in text
    assert "[2/5] Workflow make" in text
    assert "[3/5] Validation complète" in text
    assert "[4/5] Release guard final" in text
    assert "[5/5] État Git" in text


def test_readme_mentions_v040_baseline():
    text = Path("README.md").read_text(encoding="utf-8")

    assert "## Baseline opérateur v0.4.0" in text
    assert "./scripts/v040_operator_readiness.sh" in text


def test_project_status_mentions_v040():
    text = Path("PROJECT_STATUS.md").read_text(encoding="utf-8")

    assert "v0.4.0 : baseline opérateur finale" in text
