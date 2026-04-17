import json

from ble_radar import session_diff


def _write_manifest(path, stamp, count, critical, high, medium, low, watch_hits, trackers, vendor, device):
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
        "top_vendors": [[vendor, 1]],
        "top_devices": [{"name": device, "final_score": 50, "alert_level": "moyen"}],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def test_compare_session_rows_returns_expected_deltas():
    previous = {
        "stamp": "2026-04-17_19-00-00",
        "device_count": 3,
        "critical": 0,
        "high": 1,
        "medium": 1,
        "low": 1,
        "watch_hits": 0,
        "tracker_candidates": 1,
        "top_vendor": "VendorA",
        "top_device_name": "Device-A",
    }
    current = {
        "stamp": "2026-04-17_19-05-00",
        "device_count": 5,
        "critical": 1,
        "high": 1,
        "medium": 2,
        "low": 1,
        "watch_hits": 1,
        "tracker_candidates": 2,
        "top_vendor": "VendorB",
        "top_device_name": "Device-B",
    }

    diff = session_diff.compare_session_rows(previous, current)

    assert diff["device_count_delta"] == 2
    assert diff["critical_delta"] == 1
    assert diff["medium_delta"] == 1
    assert diff["watch_hits_delta"] == 1
    assert diff["previous_top_vendor"] == "VendorA"
    assert diff["current_top_vendor"] == "VendorB"


def test_compare_manifest_dicts_uses_manifest_content():
    previous_manifest = {
        "stamp": "2026-04-17_19-10-00",
        "device_count": 2,
        "alerts": {"critical": 0, "high": 0, "medium": 1, "low": 1},
        "watch_hits": 0,
        "tracker_candidates": 1,
        "top_vendors": [["VendorA", 1]],
        "top_devices": [{"name": "Device-A", "final_score": 20, "alert_level": "faible"}],
    }
    current_manifest = {
        "stamp": "2026-04-17_19-11-00",
        "device_count": 4,
        "alerts": {"critical": 1, "high": 1, "medium": 1, "low": 1},
        "watch_hits": 1,
        "tracker_candidates": 2,
        "top_vendors": [["VendorB", 2]],
        "top_devices": [{"name": "Device-B", "final_score": 70, "alert_level": "critique"}],
    }

    diff = session_diff.compare_manifest_dicts(previous_manifest, current_manifest)

    assert diff["device_count_delta"] == 2
    assert diff["critical_delta"] == 1
    assert diff["current_top_device"] == "Device-B"


def test_latest_session_diff_returns_default_when_not_enough_files(tmp_path):
    diff = session_diff.latest_session_diff(root=tmp_path)

    assert diff["has_diff"] is False
    assert diff["previous_stamp"] == "unknown"
    assert diff["current_stamp"] == "unknown"


def test_latest_session_diff_reads_two_latest_manifests(tmp_path):
    _write_manifest(
        tmp_path / "scan_manifest_2026-04-17_19-20-01.json",
        "2026-04-17_19-20-01", 2, 0, 0, 1, 1, 0, 1, "VendorA", "Device-A"
    )
    _write_manifest(
        tmp_path / "scan_manifest_2026-04-17_19-20-02.json",
        "2026-04-17_19-20-02", 5, 1, 1, 2, 1, 1, 2, "VendorB", "Device-B"
    )

    diff = session_diff.latest_session_diff(root=tmp_path)

    assert diff["has_diff"] is True
    assert diff["previous_stamp"] == "2026-04-17_19-20-01"
    assert diff["current_stamp"] == "2026-04-17_19-20-02"
    assert diff["device_count_delta"] == 3


def test_summary_lines_formats_diff():
    diff = {
        "has_diff": True,
        "previous_stamp": "2026-04-17_19-30-00",
        "current_stamp": "2026-04-17_19-31-00",
        "device_count_delta": 2,
        "critical_delta": 1,
        "high_delta": 0,
        "medium_delta": 1,
        "low_delta": 0,
        "watch_hits_delta": 1,
        "tracker_candidates_delta": 1,
        "previous_top_vendor": "VendorA",
        "current_top_vendor": "VendorB",
        "previous_top_device": "Device-A",
        "current_top_device": "Device-B",
    }

    lines = session_diff.summary_lines(diff)
    joined = "\n".join(lines)

    assert "Session Diff" in joined
    assert "Device delta: 2" in joined
    assert "Top vendor: VendorA -> VendorB" in joined
    assert "Top device: Device-A -> Device-B" in joined


def test_summary_lines_handles_no_diff_case():
    lines = session_diff.summary_lines({"has_diff": False})
    assert "No comparable sessions available." in "\n".join(lines)
