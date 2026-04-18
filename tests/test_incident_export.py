"""Tests for ble_radar/history/incident_export.py — device-centric incident pack export."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

SAMPLE_DEVICE = {
    "address": "AA:BB:CC:DD:EE:FF",
    "name": "TestPhone",
    "vendor": "Apple",
    "profile": "mobile",
    "rssi": -65,
    "alert_level": "élevé",
    "final_score": 72,
    "flags": ["possible_suivi"],
}

SAMPLE_REGISTRY = {
    "AA:BB:CC:DD:EE:FF": {
        "address": "AA:BB:CC:DD:EE:FF",
        "first_seen": "2026-04-01 08:00:00",
        "last_seen": "2026-04-18 09:00:00",
        "seen_count": 10,
        "session_count": 4,
    }
}

SAMPLE_CASES = {
    "AA:BB:CC:DD:EE:FF": {
        "address": "AA:BB:CC:DD:EE:FF",
        "reason": "tracker candidate",
        "status": "watch",
        "created_at": "2026-04-10 10:00:00",
        "updated_at": "2026-04-18 09:00:00",
    }
}

SAMPLE_MOVEMENT = {
    "new": [],
    "disappeared": [],
    "recurring": [SAMPLE_DEVICE],
    "score_changes": [
        {
            "address": "AA:BB:CC:DD:EE:FF",
            "name": "TestPhone",
            "prev_score": 55,
            "curr_score": 60,
            "delta": 5,
        }
    ],
    "counts": {"new": 0, "disappeared": 0, "recurring": 1, "total_current": 1},
}


def _build(tmp_path, **kwargs):
    """Wrap build_device_pack, redirecting DEVICE_PACKS_DIR to tmp_path."""
    from ble_radar.history import incident_export as mod
    original = mod.DEVICE_PACKS_DIR
    mod.DEVICE_PACKS_DIR = tmp_path
    try:
        result = mod.build_device_pack(**kwargs)
    finally:
        mod.DEVICE_PACKS_DIR = original
    return result


# ---------------------------------------------------------------------------
# Return structure
# ---------------------------------------------------------------------------

def test_returns_expected_keys(tmp_path):
    result = _build(tmp_path, address="AA:BB:CC:DD:EE:FF", stamp="2026-04-18_12-00-00")
    assert set(result.keys()) == {"pack_dir", "json_path", "md_path", "pack"}


def test_pack_dir_is_created(tmp_path):
    result = _build(tmp_path, address="AA:BB:CC:DD:EE:FF", stamp="2026-04-18_12-00-00")
    assert result["pack_dir"].is_dir()


def test_json_file_is_created(tmp_path):
    result = _build(tmp_path, address="AA:BB:CC:DD:EE:FF", stamp="2026-04-18_12-00-00")
    assert result["json_path"].exists()


def test_md_file_is_created(tmp_path):
    result = _build(tmp_path, address="AA:BB:CC:DD:EE:FF", stamp="2026-04-18_12-00-00")
    assert result["md_path"].exists()


# ---------------------------------------------------------------------------
# JSON content
# ---------------------------------------------------------------------------

def test_pack_json_top_level_keys(tmp_path):
    result = _build(tmp_path, address="AA:BB:CC:DD:EE:FF", stamp="2026-04-18_12-00-00")
    data = json.loads(result["json_path"].read_text())
    for key in ("address", "pack_stamp", "identity", "registry", "device_score", "case", "movement"):
        assert key in data, f"missing key: {key}"


def test_pack_json_address_normalised(tmp_path):
    result = _build(tmp_path, address="aa:bb:cc:dd:ee:ff", stamp="ts")
    data = json.loads(result["json_path"].read_text())
    assert data["address"] == "AA:BB:CC:DD:EE:FF"


def test_pack_json_identity_from_device(tmp_path):
    result = _build(
        tmp_path,
        address="AA:BB:CC:DD:EE:FF",
        current_devices=[SAMPLE_DEVICE],
        stamp="ts",
    )
    data = json.loads(result["json_path"].read_text())
    assert data["identity"]["name"] == "TestPhone"
    assert data["identity"]["vendor"] == "Apple"
    assert data["identity"]["alert_level"] == "élevé"


def test_pack_json_registry_fields(tmp_path):
    result = _build(
        tmp_path,
        address="AA:BB:CC:DD:EE:FF",
        registry=SAMPLE_REGISTRY,
        stamp="ts",
    )
    data = json.loads(result["json_path"].read_text())
    assert data["registry"]["seen_count"] == 10
    assert data["registry"]["session_count"] == 4
    assert data["registry"]["first_seen"] == "2026-04-01 08:00:00"


def test_pack_json_device_score_is_int(tmp_path):
    result = _build(
        tmp_path,
        address="AA:BB:CC:DD:EE:FF",
        registry=SAMPLE_REGISTRY,
        stamp="ts",
    )
    data = json.loads(result["json_path"].read_text())
    assert isinstance(data["device_score"], int)
    assert 0 <= data["device_score"] <= 100


def test_pack_json_case_populated(tmp_path):
    result = _build(
        tmp_path,
        address="AA:BB:CC:DD:EE:FF",
        watch_cases=SAMPLE_CASES,
        stamp="ts",
    )
    data = json.loads(result["json_path"].read_text())
    assert data["case"] is not None
    assert data["case"]["reason"] == "tracker candidate"
    assert data["case"]["status"] == "watch"


def test_pack_json_case_null_when_not_watched(tmp_path):
    result = _build(tmp_path, address="AA:BB:CC:DD:EE:FF", watch_cases={}, stamp="ts")
    data = json.loads(result["json_path"].read_text())
    assert data["case"] is None


def test_pack_json_movement_recurring(tmp_path):
    result = _build(
        tmp_path,
        address="AA:BB:CC:DD:EE:FF",
        current_devices=[SAMPLE_DEVICE],
        movement=SAMPLE_MOVEMENT,
        stamp="ts",
    )
    data = json.loads(result["json_path"].read_text())
    assert data["movement"]["status"] == "recurring"
    assert data["movement"]["score_delta"] == 5


def test_pack_json_movement_new(tmp_path):
    movement = {
        "new": [SAMPLE_DEVICE],
        "disappeared": [],
        "recurring": [],
        "score_changes": [],
        "counts": {},
    }
    result = _build(
        tmp_path,
        address="AA:BB:CC:DD:EE:FF",
        movement=movement,
        stamp="ts",
    )
    data = json.loads(result["json_path"].read_text())
    assert data["movement"]["status"] == "new"


def test_pack_json_movement_unknown_when_none(tmp_path):
    result = _build(tmp_path, address="AA:BB:CC:DD:EE:FF", movement=None, stamp="ts")
    data = json.loads(result["json_path"].read_text())
    assert data["movement"]["status"] == "unknown"


# ---------------------------------------------------------------------------
# Markdown content
# ---------------------------------------------------------------------------

def test_md_contains_address(tmp_path):
    result = _build(tmp_path, address="AA:BB:CC:DD:EE:FF", stamp="ts")
    md = result["md_path"].read_text()
    assert "AA:BB:CC:DD:EE:FF" in md


def test_md_contains_identity_section(tmp_path):
    result = _build(
        tmp_path,
        address="AA:BB:CC:DD:EE:FF",
        current_devices=[SAMPLE_DEVICE],
        stamp="ts",
    )
    md = result["md_path"].read_text()
    assert "## Identity" in md
    assert "TestPhone" in md


def test_md_contains_registry_section(tmp_path):
    result = _build(
        tmp_path,
        address="AA:BB:CC:DD:EE:FF",
        registry=SAMPLE_REGISTRY,
        stamp="ts",
    )
    md = result["md_path"].read_text()
    assert "## Registry" in md
    assert "2026-04-01" in md


def test_md_contains_score_section(tmp_path):
    result = _build(tmp_path, address="AA:BB:CC:DD:EE:FF", stamp="ts")
    md = result["md_path"].read_text()
    assert "## Persistence Score" in md


def test_md_contains_case_section(tmp_path):
    result = _build(
        tmp_path,
        address="AA:BB:CC:DD:EE:FF",
        watch_cases=SAMPLE_CASES,
        stamp="ts",
    )
    md = result["md_path"].read_text()
    assert "## Watch / Case" in md
    assert "tracker candidate" in md


def test_md_no_case_message(tmp_path):
    result = _build(tmp_path, address="AA:BB:CC:DD:EE:FF", watch_cases={}, stamp="ts")
    md = result["md_path"].read_text()
    assert "No active watch/case record" in md


def test_md_contains_movement_section(tmp_path):
    result = _build(
        tmp_path,
        address="AA:BB:CC:DD:EE:FF",
        movement=SAMPLE_MOVEMENT,
        stamp="ts",
    )
    md = result["md_path"].read_text()
    assert "## Session Movement" in md
    assert "recurring" in md


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_address_raises(tmp_path):
    from ble_radar.history.incident_export import build_device_pack
    with pytest.raises(ValueError):
        build_device_pack("")


def test_all_optional_args_none(tmp_path):
    """Must not crash when all optional context is absent."""
    result = _build(
        tmp_path,
        address="FF:EE:DD:CC:BB:AA",
        current_devices=None,
        registry=None,
        watch_cases=None,
        movement=None,
        stamp="ts",
    )
    assert result["pack"] is not None
    data = json.loads(result["json_path"].read_text())
    assert data["identity"]["name"] == "Inconnu"
    assert data["registry"]["seen_count"] == 0
    assert data["case"] is None


def test_pack_dir_slug_strips_colons(tmp_path):
    result = _build(tmp_path, address="AA:BB:CC:DD:EE:FF", stamp="2026-04-18_12-00-00")
    assert result["pack_dir"].name == "AABBCCDDEEFF_2026-04-18_12-00-00"
