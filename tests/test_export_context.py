import json

from ble_radar import export_context


def test_build_export_context_collects_all_sections(monkeypatch):
    monkeypatch.setattr(
        export_context,
        "latest_session_overview",
        lambda: {
            "stamp": "2026-04-17_20-30-00",
            "device_count": 5,
            "critical": 1,
            "watch_hits": 1,
            "tracker_candidates": 2,
            "top_vendor": "TestVendor",
            "top_device_name": "Beacon-One",
            "top_device_score": 72,
        },
    )
    monkeypatch.setattr(
        export_context,
        "build_session_catalog",
        lambda limit=5: [
            {
                "stamp": "2026-04-17_20-30-00",
                "device_count": 5,
                "critical": 1,
                "watch_hits": 1,
                "tracker_candidates": 2,
                "top_vendor": "TestVendor",
            }
        ],
    )
    monkeypatch.setattr(
        export_context,
        "latest_session_diff",
        lambda: {
            "has_diff": True,
            "previous_stamp": "2026-04-17_20-25-00",
            "current_stamp": "2026-04-17_20-30-00",
            "device_count_delta": 2,
        },
    )

    context = export_context.build_export_context(stamp="2026-04-17_20-31-00", recent_limit=3)

    assert context["stamp"] == "2026-04-17_20-31-00"
    assert context["session_overview"]["top_vendor"] == "TestVendor"
    assert len(context["recent_sessions"]) == 1
    assert context["session_diff"]["has_diff"] is True
    assert context["recent_limit"] == 3


def test_context_markdown_lines_formats_context(monkeypatch):
    monkeypatch.setattr(
        export_context,
        "diff_summary_lines",
        lambda diff: ["BLE Radar Omega AI - Session Diff", "Device delta: 2"],
    )

    lines = export_context.context_markdown_lines(
        {
            "session_overview": {
                "stamp": "2026-04-17_20-30-00",
                "device_count": 5,
                "critical": 1,
                "watch_hits": 1,
                "tracker_candidates": 2,
                "top_vendor": "TestVendor",
                "top_device_name": "Beacon-One",
                "top_device_score": 72,
            },
            "recent_sessions": [
                {
                    "stamp": "2026-04-17_20-30-00",
                    "device_count": 5,
                    "critical": 1,
                    "watch_hits": 1,
                    "tracker_candidates": 2,
                    "top_vendor": "TestVendor",
                }
            ],
            "session_diff": {"has_diff": True},
        }
    )

    joined = "\n".join(lines)
    assert "Latest session overview" in joined
    assert "Recent sessions" in joined
    assert "Session diff" in joined
    assert "Device delta: 2" in joined


def test_save_export_context_writes_json_and_md(monkeypatch, tmp_path):
    monkeypatch.setattr(
        export_context,
        "build_export_context",
        lambda stamp=None, recent_limit=5: {
            "stamp": "2026-04-17_20-32-00",
            "session_overview": {"stamp": "2026-04-17_20-30-00"},
            "recent_sessions": [],
            "session_diff": {"has_diff": False},
            "recent_limit": 5,
        },
    )
    monkeypatch.setattr(
        export_context,
        "context_markdown_lines",
        lambda context: ["# BLE Radar Omega AI - Export Context", "", "## Session diff", "- none"],
    )

    result = export_context.save_export_context(output_root=tmp_path)

    assert result["json_path"].exists()
    assert result["md_path"].exists()

    payload = json.loads(result["json_path"].read_text(encoding="utf-8"))
    text = result["md_path"].read_text(encoding="utf-8")

    assert payload["stamp"] == "2026-04-17_20-32-00"
    assert "## Session diff" in text


def test_list_export_contexts_returns_latest_first(tmp_path):
    a = tmp_path / "export_context_2026-04-17_20-30-00.json"
    b = tmp_path / "export_context_2026-04-17_20-31-00.md"
    a.write_text("{}", encoding="utf-8")
    b.write_text("{}", encoding="utf-8")

    items = export_context.list_export_contexts(root=tmp_path)

    assert items[0].name == "export_context_2026-04-17_20-31-00.md"
    assert items[1].name == "export_context_2026-04-17_20-30-00.json"


def test_list_export_contexts_returns_empty_when_missing(tmp_path):
    items = export_context.list_export_contexts(root=tmp_path / "missing")
    assert items == []
