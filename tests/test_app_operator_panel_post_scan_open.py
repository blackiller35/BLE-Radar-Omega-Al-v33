from pathlib import Path
import builtins

from ble_radar import app


def test_maybe_open_post_scan_report_opens_matching_operator_panel(monkeypatch):
    opened = []

    monkeypatch.setattr(app, "open_html_report", lambda path: opened.append(Path(path).name))
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "2")
    monkeypatch.setattr(builtins, "print", lambda *args, **kwargs: None)
    monkeypatch.setattr(app, "color", lambda text, *_args, **_kwargs: text)
    monkeypatch.setattr(app, "hr", lambda *_args, **_kwargs: "---")

    app.maybe_open_post_scan_report(
        {
            "html": Path("reports/scan_2026-04-22_18-20-00.html"),
            "operator_panel_html": Path("reports/operator_panel_2026-04-22_18-20-00.html"),
        }
    )

    assert opened == ["operator_panel_2026-04-22_18-20-00.html"]


def test_maybe_open_post_scan_report_can_open_both(monkeypatch):
    opened = []

    monkeypatch.setattr(app, "open_html_report", lambda path: opened.append(Path(path).name))
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "3")
    monkeypatch.setattr(builtins, "print", lambda *args, **kwargs: None)
    monkeypatch.setattr(app, "color", lambda text, *_args, **_kwargs: text)
    monkeypatch.setattr(app, "hr", lambda *_args, **_kwargs: "---")

    app.maybe_open_post_scan_report(
        {
            "html": Path("reports/scan_2026-04-22_18-20-00.html"),
            "operator_panel_html": Path("reports/operator_panel_2026-04-22_18-20-00.html"),
        }
    )

    assert opened == [
        "scan_2026-04-22_18-20-00.html",
        "operator_panel_2026-04-22_18-20-00.html",
    ]
