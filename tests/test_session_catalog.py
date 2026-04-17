import json

from ble_radar import session_catalog


def _write_manifest(path, stamp, count, critical, high, medium, low, watch_hits, trackers, vendor, vendor_count, device_name, device_score):
    payload = {
        "stamp": stamp,
        "device_count": count,
        "alerts": {
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
        },
        "watch_hits": watch_hits,
        "tracker_candidates": trackers,
        "top_vendors": [[vendor, vendor_count]],
        "top_devices": [
            {
                "name": device_name,
                "final_score": device_score,
                "alert_level": "critique" if critical else "moyen",
            }
        ],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def test_session_row_from_manifest_extracts_expected_fields():
    row = session_catalog.session_row_from_manifest(
        {
            "stamp": "2026-04-17_18-50-00",
            "device_count": 3,
            "alerts": {"critical": 1, "high": 1, "medium": 1, "low": 0},
            "watch_hits": 1,
            "tracker_candidates": 2,
            "top_vendors": [["TestVendor", 2]],
            "top_devices": [{"name": "Beacon-One", "final_score": 72, "alert_level": "critique"}],
        }
    )

    assert row["stamp"] == "2026-04-17_18-50-00"
    assert row["device_count"] == 3
    assert row["critical"] == 1
    assert row["watch_hits"] == 1
    assert row["top_vendor"] == "TestVendor"
    assert row["top_device_name"] == "Beacon-One"
    assert row["top_device_score"] == 72


def test_build_session_catalog_reads_latest_first(tmp_path):
    _write_manifest(
        tmp_path / "scan_manifest_2026-04-17_18-50-01.json",
        "2026-04-17_18-50-01", 2, 0, 1, 1, 0, 0, 1, "TrackCorp", 1, "Tracker-Two", 44
    )
    _write_manifest(
        tmp_path / "scan_manifest_2026-04-17_18-50-02.json",
        "2026-04-17_18-50-02", 4, 1, 1, 1, 1, 1, 2, "TestVendor", 2, "Beacon-One", 72
    )

    rows = session_catalog.build_session_catalog(root=tmp_path)

    assert len(rows) == 2
    assert rows[0]["stamp"] == "2026-04-17_18-50-02"
    assert rows[1]["stamp"] == "2026-04-17_18-50-01"


def test_build_session_catalog_honors_limit(tmp_path):
    _write_manifest(
        tmp_path / "scan_manifest_2026-04-17_18-50-01.json",
        "2026-04-17_18-50-01", 2, 0, 1, 1, 0, 0, 1, "TrackCorp", 1, "Tracker-Two", 44
    )
    _write_manifest(
        tmp_path / "scan_manifest_2026-04-17_18-50-02.json",
        "2026-04-17_18-50-02", 4, 1, 1, 1, 1, 1, 2, "TestVendor", 2, "Beacon-One", 72
    )

    rows = session_catalog.build_session_catalog(root=tmp_path, limit=1)

    assert len(rows) == 1
    assert rows[0]["stamp"] == "2026-04-17_18-50-02"


def test_latest_session_overview_returns_default_when_empty(tmp_path):
    row = session_catalog.latest_session_overview(root=tmp_path)

    assert row["stamp"] == "unknown"
    assert row["device_count"] == 0
    assert row["top_vendor"] == "Unknown"


def test_latest_session_overview_returns_latest_row(tmp_path):
    _write_manifest(
        tmp_path / "scan_manifest_2026-04-17_18-50-03.json",
        "2026-04-17_18-50-03", 5, 2, 1, 1, 1, 1, 2, "TestVendor", 3, "Beacon-One", 82
    )

    row = session_catalog.latest_session_overview(root=tmp_path)

    assert row["stamp"] == "2026-04-17_18-50-03"
    assert row["critical"] == 2
    assert row["top_device_name"] == "Beacon-One"


def test_summary_lines_formats_rows():
    lines = session_catalog.summary_lines(
        [
            {
                "stamp": "2026-04-17_18-50-04",
                "device_count": 3,
                "critical": 1,
                "high": 1,
                "medium": 1,
                "low": 0,
                "watch_hits": 1,
                "tracker_candidates": 2,
                "top_vendor": "TestVendor",
                "top_vendor_count": 2,
                "top_device_name": "Beacon-One",
                "top_device_score": 72,
                "top_device_alert": "critique",
            }
        ]
    )

    joined = "\n".join(lines)
    assert "Session Catalog" in joined
    assert "Sessions: 1" in joined
    assert "top_vendor=TestVendor" in joined
    assert "top_device=Beacon-One (72)" in joined
