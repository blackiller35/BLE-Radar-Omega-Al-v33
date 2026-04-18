"""Focused tests for step 9 investigation workspace profile."""

import json

import pytest


SAMPLE_DEVICE = {
    "address": "AA:BB:CC:DD:EE:FF",
    "name": "FocusPhone",
    "vendor": "Apple",
    "profile": "tracker_ble",
    "alert_level": "critique",
    "watch_hit": True,
    "follow_score": 4,
}

SAMPLE_REGISTRY = {
    "AA:BB:CC:DD:EE:FF": {
        "address": "AA:BB:CC:DD:EE:FF",
        "first_seen": "2026-04-10 10:00:00",
        "last_seen": "2026-04-18 10:30:00",
        "seen_count": 12,
        "session_count": 5,
    }
}

SAMPLE_CASES = {
    "AA:BB:CC:DD:EE:FF": {
        "address": "AA:BB:CC:DD:EE:FF",
        "status": "watch",
        "reason": "manual monitor",
        "updated_at": "2026-04-18 10:40:00",
    }
}

SAMPLE_MOVEMENT = {
    "new": [],
    "disappeared": [],
    "recurring": [SAMPLE_DEVICE],
    "score_changes": [
        {
            "address": "AA:BB:CC:DD:EE:FF",
            "name": "FocusPhone",
            "prev_score": 55,
            "curr_score": 60,
            "delta": 5,
        }
    ],
    "counts": {"new": 0, "disappeared": 0, "recurring": 1, "total_current": 1},
}


def test_build_investigation_profile_empty_address_raises():
    from ble_radar.history.investigation_workspace import build_investigation_profile

    with pytest.raises(ValueError):
        build_investigation_profile("")


def test_build_investigation_profile_includes_expected_sections(monkeypatch):
    from ble_radar.history.investigation_workspace import build_investigation_profile

    monkeypatch.setattr(
        "ble_radar.history.investigation_workspace.list_incident_packs",
        lambda: [],
    )

    profile = build_investigation_profile(
        "AA:BB:CC:DD:EE:FF",
        devices=[SAMPLE_DEVICE],
        registry=SAMPLE_REGISTRY,
        watch_cases=SAMPLE_CASES,
        movement=SAMPLE_MOVEMENT,
        triage_results=[
            {
                "address": "AA:BB:CC:DD:EE:FF",
                "triage_score": 75,
                "triage_bucket": "critical",
                "short_reason": "alert:critique, watch_hit",
            }
        ],
        registry_scores={"AA:BB:CC:DD:EE:FF": 60},
    )

    assert profile["address"] == "AA:BB:CC:DD:EE:FF"
    for key in ("identity", "registry", "triage", "case", "movement", "incident_refs", "summary"):
        assert key in profile


def test_build_investigation_profile_uses_triage_row_when_available(monkeypatch):
    from ble_radar.history.investigation_workspace import build_investigation_profile

    monkeypatch.setattr(
        "ble_radar.history.investigation_workspace.list_incident_packs",
        lambda: [],
    )

    profile = build_investigation_profile(
        "AA:BB:CC:DD:EE:FF",
        devices=[SAMPLE_DEVICE],
        triage_results=[
            {
                "address": "AA:BB:CC:DD:EE:FF",
                "triage_score": 88,
                "triage_bucket": "critical",
                "short_reason": "precomputed",
            }
        ],
    )

    assert profile["triage"]["triage_score"] == 88
    assert profile["triage"]["short_reason"] == "precomputed"


def test_build_investigation_profile_falls_back_to_compute_triage(monkeypatch):
    from ble_radar.history.investigation_workspace import build_investigation_profile

    monkeypatch.setattr(
        "ble_radar.history.investigation_workspace.list_incident_packs",
        lambda: [],
    )

    profile = build_investigation_profile(
        "AA:BB:CC:DD:EE:FF",
        devices=[SAMPLE_DEVICE],
        registry=SAMPLE_REGISTRY,
        watch_cases=SAMPLE_CASES,
        movement=SAMPLE_MOVEMENT,
    )

    assert isinstance(profile["triage"]["triage_score"], int)
    assert profile["triage"]["triage_bucket"] in ("critical", "review", "watch", "normal")


def test_build_investigation_profile_movement_score_delta(monkeypatch):
    from ble_radar.history.investigation_workspace import build_investigation_profile

    monkeypatch.setattr(
        "ble_radar.history.investigation_workspace.list_incident_packs",
        lambda: [],
    )

    profile = build_investigation_profile(
        "AA:BB:CC:DD:EE:FF",
        devices=[SAMPLE_DEVICE],
        movement=SAMPLE_MOVEMENT,
    )

    assert profile["movement"]["status"] == "recurring"
    assert profile["movement"]["score_delta"] == 5


def test_build_investigation_profile_ref_lists(monkeypatch, tmp_path):
    from ble_radar.history import investigation_workspace as iw

    device_packs_root = tmp_path / "device_packs"
    device_packs_root.mkdir(parents=True, exist_ok=True)
    (device_packs_root / "AABBCCDDEEFF_2026-04-18_12-00-00").mkdir()
    (device_packs_root / "AABBCCDDEEFF_2026-04-18_11-00-00").mkdir()

    monkeypatch.setattr(iw, "REPORTS_DIR", tmp_path)

    class DummyPath:
        def __init__(self, name):
            self.name = name

    monkeypatch.setattr(iw, "list_incident_packs", lambda: [DummyPath("caseA"), DummyPath("caseB")])

    profile = iw.build_investigation_profile("AA:BB:CC:DD:EE:FF", devices=[SAMPLE_DEVICE])

    assert profile["incident_refs"]["device_packs"]
    assert profile["incident_refs"]["incident_packs"] == ["caseA", "caseB"]


def test_dashboard_renders_investigation_workspace_panel(monkeypatch):
    import ble_radar.dashboard as db

    monkeypatch.setattr(db, "load_registry", lambda: SAMPLE_REGISTRY)
    monkeypatch.setattr(db, "load_last_scan", lambda: [])
    monkeypatch.setattr(db, "load_scan_history", lambda: [])
    monkeypatch.setattr(db, "load_watch_cases", lambda: SAMPLE_CASES)
    monkeypatch.setattr(
        db,
        "build_investigation_profile",
        lambda *args, **kwargs: {
            "address": "AA:BB:CC:DD:EE:FF",
            "identity": {
                "name": "FocusPhone",
                "vendor": "Apple",
                "profile": "tracker_ble",
                "alert_level": "critique",
                "watch_hit": True,
            },
            "registry": {"seen_count": 12, "session_count": 5, "registry_score": 60},
            "triage": {"triage_bucket": "critical", "triage_score": 88, "short_reason": "x"},
            "case": {"status": "watch", "reason": "manual monitor", "updated_at": "2026-04-18"},
            "movement": {"status": "new"},
            "incident_refs": {"device_packs": ["pack1"], "incident_packs": ["legacy1"]},
            "summary": {"headline": "FocusPhone", "priority": "critical:88"},
        },
    )

    html = db.render_dashboard_html([SAMPLE_DEVICE], "2026-04-18T00:00:00")

    assert "Investigation Workspace (Focused Device)" in html
    assert "FocusPhone" in html
    assert "Device pack refs" in html
    assert "Incident pack refs" in html


def test_dashboard_investigation_workspace_panel_empty(monkeypatch):
    import ble_radar.dashboard as db

    monkeypatch.setattr(db, "load_registry", lambda: {})
    monkeypatch.setattr(db, "load_last_scan", lambda: [])
    monkeypatch.setattr(db, "load_scan_history", lambda: [])
    monkeypatch.setattr(db, "load_watch_cases", lambda: {})

    html = db.render_dashboard_html([], "2026-04-18T00:00:00")

    assert "Investigation Workspace (Focused Device)" in html
    assert "Aucun profil" in html
