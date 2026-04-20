import pytest

from ble_radar import incident_pack, investigation
from ble_radar.security import SecurityContext


def _operator_security_context():
    return SecurityContext(
        mode="operator",
        yubikey_present=True,
        key_name="primary",
        key_label="YubiKey-1",
        sensitive_enabled=True,
        secrets_unlocked=True,
    )


@pytest.fixture(autouse=True)
def _operator_mode_autouse(monkeypatch):
    monkeypatch.setattr(
        investigation, "build_security_context", _operator_security_context
    )
    monkeypatch.setattr(
        incident_pack, "build_security_context", _operator_security_context
    )


def test_incident_pack_manifest_contains_session_diff(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")
    monkeypatch.setattr(
        incident_pack, "INCIDENT_PACKS_DIR", tmp_path / "incident_packs"
    )
    monkeypatch.setattr(
        incident_pack,
        "latest_session_diff",
        lambda: {
            "has_diff": True,
            "previous_stamp": "2026-04-17_19-00-00",
            "current_stamp": "2026-04-17_19-05-00",
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
            "has_diff": True,
        },
    )
    monkeypatch.setattr(
        incident_pack,
        "diff_summary_lines",
        lambda diff: [
            "BLE Radar Omega AI - Session Diff",
            "Device delta: 2",
            "Top vendor: VendorA -> VendorB",
        ],
    )

    case = investigation.create_case("Tracker suspect")
    result = incident_pack.build_incident_pack(case["id"])

    assert result["manifest"]["session_diff"]["has_diff"] is True
    assert result["manifest"]["session_diff"]["device_count_delta"] == 2


def test_incident_summary_mentions_session_diff(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")
    monkeypatch.setattr(
        incident_pack, "INCIDENT_PACKS_DIR", tmp_path / "incident_packs"
    )
    monkeypatch.setattr(
        incident_pack,
        "latest_session_diff",
        lambda: {
            "has_diff": True,
            "previous_stamp": "2026-04-17_19-10-00",
            "current_stamp": "2026-04-17_19-11-00",
            "device_count_delta": 1,
            "critical_delta": 1,
            "high_delta": 0,
            "medium_delta": 0,
            "low_delta": 0,
            "watch_hits_delta": 0,
            "tracker_candidates_delta": 1,
            "previous_top_vendor": "VendorA",
            "current_top_vendor": "VendorB",
            "previous_top_device": "Device-A",
            "current_top_device": "Device-B",
            "has_diff": True,
        },
    )
    monkeypatch.setattr(
        incident_pack,
        "diff_summary_lines",
        lambda diff: [
            "BLE Radar Omega AI - Session Diff",
            "Device delta: 1",
            "Top vendor: VendorA -> VendorB",
        ],
    )

    case = investigation.create_case("Beacon check")
    result = incident_pack.build_incident_pack(case["id"])
    text = result["summary_path"].read_text(encoding="utf-8")

    assert "Session diff:" in text
    assert "Device delta: 1" in text
    assert "Top vendor: VendorA -> VendorB" in text


def test_incident_summary_handles_missing_session_diff(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation, "CASES_DIR", tmp_path / "cases")
    monkeypatch.setattr(
        incident_pack, "INCIDENT_PACKS_DIR", tmp_path / "incident_packs"
    )
    monkeypatch.setattr(
        incident_pack, "latest_session_diff", lambda: {"has_diff": False}
    )
    monkeypatch.setattr(
        incident_pack,
        "diff_summary_lines",
        lambda diff: [
            "BLE Radar Omega AI - Session Diff",
            "No comparable sessions available.",
        ],
    )

    case = investigation.create_case("No diff case")
    result = incident_pack.build_incident_pack(case["id"])
    text = result["summary_path"].read_text(encoding="utf-8")

    assert "Session diff: none" in text
