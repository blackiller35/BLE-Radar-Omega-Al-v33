from pathlib import Path

from ble_radar import app


def test_latest_report_file_picks_latest_matching(tmp_path, monkeypatch):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    older = reports_dir / "operator_panel_2026-04-22_17-00-00.html"
    newer = reports_dir / "operator_panel_2026-04-22_17-05-00.html"
    older.write_text("old", encoding="utf-8")
    newer.write_text("new", encoding="utf-8")

    monkeypatch.setattr(app, "Path", lambda value: tmp_path / value)

    result = app._latest_report_file("operator_panel_*.html")

    assert result is not None
    assert result.name == "operator_panel_2026-04-22_17-05-00.html"


def test_open_last_operator_panel_report_opens_expected_file(tmp_path, monkeypatch):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    panel = reports_dir / "operator_panel_2026-04-22_17-10-00.html"
    panel.write_text("panel", encoding="utf-8")

    opened = []

    monkeypatch.setattr(app, "Path", lambda value: tmp_path / value)
    monkeypatch.setattr(app, "open_html_report", lambda path: opened.append(Path(path).name))
    monkeypatch.setattr(app, "clear", lambda: None)
    monkeypatch.setattr(app, "banner", lambda: None)
    monkeypatch.setattr(app, "pause", lambda: None)
    monkeypatch.setattr(app, "color", lambda text, *_args, **_kwargs: text)

    app.open_last_operator_panel_report()

    assert opened == ["operator_panel_2026-04-22_17-10-00.html"]
