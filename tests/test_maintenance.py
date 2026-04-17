from pathlib import Path

from ble_radar import maintenance


def test_runtime_artifact_patterns_contains_expected_entries():
    patterns = maintenance.runtime_artifact_patterns()

    assert "reports/scan_*.html" in patterns
    assert "history/executive_summary_*.json" in patterns
    assert "snapshots/snapshot_*" in patterns


def test_find_runtime_artifacts_finds_generated_paths_only(tmp_path):
    (tmp_path / "reports").mkdir()
    (tmp_path / "history").mkdir()
    (tmp_path / "history" / "daily_reports").mkdir(parents=True)
    (tmp_path / "snapshots").mkdir()
    (tmp_path / "state").mkdir()

    (tmp_path / "reports" / "scan_2026-04-17_14-40-00.html").write_text("x", encoding="utf-8")
    (tmp_path / "reports" / "scan_2026-04-17_14-40-00.json").write_text("{}", encoding="utf-8")
    (tmp_path / "reports" / "release_summary_2026-04-17_14-40-00.md").write_text("# x", encoding="utf-8")
    (tmp_path / "history" / "executive_summary_2026-04-17_14-40-00.json").write_text("{}", encoding="utf-8")
    (tmp_path / "history" / "daily_reports" / "daily_report_2026-04-17.json").write_text("{}", encoding="utf-8")
    (tmp_path / "snapshots" / "snapshot_2026-04-17_14-40-00").mkdir()

    (tmp_path / "history" / "scan_history.json").write_text("[]", encoding="utf-8")
    (tmp_path / "history" / "trends.json").write_text("{}", encoding="utf-8")
    (tmp_path / "state" / "last_scan.json").write_text("[]", encoding="utf-8")

    found = {p.relative_to(tmp_path).as_posix() for p in maintenance.find_runtime_artifacts(Path(tmp_path))}

    assert "reports/scan_2026-04-17_14-40-00.html" in found
    assert "reports/scan_2026-04-17_14-40-00.json" in found
    assert "reports/release_summary_2026-04-17_14-40-00.md" in found
    assert "history/executive_summary_2026-04-17_14-40-00.json" in found
    assert "history/daily_reports/daily_report_2026-04-17.json" in found
    assert "snapshots/snapshot_2026-04-17_14-40-00" in found

    assert "history/scan_history.json" not in found
    assert "history/trends.json" not in found
    assert "state/last_scan.json" not in found


def test_find_runtime_artifacts_returns_empty_list_when_clean(tmp_path):
    assert maintenance.find_runtime_artifacts(Path(tmp_path)) == []
