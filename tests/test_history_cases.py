"""Tests for ble_radar/history/cases.py — watch/case tracking module."""
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers — isolate every test from the real filesystem
# ---------------------------------------------------------------------------

def _make_cases_module(initial_data=None):
    """Return a fresh import of cases with load_json/save_json patched."""
    import importlib
    import ble_radar.history.cases as mod
    importlib.reload(mod)
    return mod


def _patch_io(initial=None):
    """Context manager that patches load_json / save_json."""
    from unittest.mock import patch, call
    store = [dict(initial) if initial else {}]

    def _load(path, default):
        return dict(store[0])

    def _save(path, data):
        store[0] = dict(data)

    return (
        patch("ble_radar.history.cases.load_json", side_effect=_load),
        patch("ble_radar.history.cases.save_json", side_effect=_save),
        store,
    )


# ---------------------------------------------------------------------------
# load_cases
# ---------------------------------------------------------------------------

def test_load_cases_returns_dict_on_empty():
    p_load, p_save, _ = _patch_io()
    with p_load, p_save:
        from ble_radar.history.cases import load_cases
        result = load_cases()
    assert isinstance(result, dict)
    assert result == {}


def test_load_cases_passes_through_existing_data():
    data = {
        "AA:BB:CC:DD:EE:FF": {
            "address": "AA:BB:CC:DD:EE:FF",
            "reason": "test",
            "status": "watch",
            "created_at": "2026-01-01 00:00:00",
            "updated_at": "2026-01-01 00:00:00",
        }
    }
    p_load, p_save, _ = _patch_io(initial=data)
    with p_load, p_save:
        from ble_radar.history.cases import load_cases
        result = load_cases()
    assert "AA:BB:CC:DD:EE:FF" in result


def test_load_cases_tolerates_non_dict_json(tmp_path):
    """If the JSON file contains a list (corrupt), return empty dict."""
    with patch("ble_radar.history.cases.load_json", return_value=[]):
        with patch("ble_radar.history.cases.save_json"):
            from ble_radar.history.cases import load_cases
            result = load_cases()
    assert result == {}


# ---------------------------------------------------------------------------
# upsert_case — creation
# ---------------------------------------------------------------------------

def test_upsert_case_creates_new_entry():
    p_load, p_save, store = _patch_io()
    with p_load, p_save:
        from ble_radar.history.cases import upsert_case
        record = upsert_case("aa:bb:cc:dd:ee:ff", "tracker candidate")
    assert record["address"] == "AA:BB:CC:DD:EE:FF"
    assert record["reason"] == "tracker candidate"
    assert record["status"] == "watch"
    assert "created_at" in record
    assert "updated_at" in record


def test_upsert_case_normalises_address_uppercase():
    p_load, p_save, store = _patch_io()
    with p_load, p_save:
        from ble_radar.history.cases import upsert_case
        record = upsert_case("aa:bb:cc:dd:ee:ff", "test")
    assert record["address"] == "AA:BB:CC:DD:EE:FF"
    assert "AA:BB:CC:DD:EE:FF" in store[0]


def test_upsert_case_custom_status():
    p_load, p_save, _ = _patch_io()
    with p_load, p_save:
        from ble_radar.history.cases import upsert_case
        record = upsert_case("11:22:33:44:55:66", "manual flag", status="escalated")
    assert record["status"] == "escalated"


def test_upsert_case_empty_address_raises():
    p_load, p_save, _ = _patch_io()
    with p_load, p_save:
        from ble_radar.history.cases import upsert_case
        with pytest.raises(ValueError):
            upsert_case("", "reason")


# ---------------------------------------------------------------------------
# upsert_case — update preserves created_at
# ---------------------------------------------------------------------------

def test_upsert_case_update_preserves_created_at():
    initial = {
        "AA:BB:CC:DD:EE:FF": {
            "address": "AA:BB:CC:DD:EE:FF",
            "reason": "old reason",
            "status": "watch",
            "created_at": "2026-01-01 00:00:00",
            "updated_at": "2026-01-01 00:00:00",
        }
    }
    p_load, p_save, store = _patch_io(initial=initial)
    with p_load, p_save:
        from ble_radar.history.cases import upsert_case
        record = upsert_case("AA:BB:CC:DD:EE:FF", "new reason", status="closed")
    assert record["created_at"] == "2026-01-01 00:00:00"
    assert record["reason"] == "new reason"
    assert record["status"] == "closed"


def test_upsert_case_update_refreshes_updated_at():
    initial = {
        "AA:BB:CC:DD:EE:FF": {
            "address": "AA:BB:CC:DD:EE:FF",
            "reason": "r",
            "status": "watch",
            "created_at": "2026-01-01 00:00:00",
            "updated_at": "2026-01-01 00:00:00",
        }
    }
    p_load, p_save, _ = _patch_io(initial=initial)
    with p_load, p_save:
        from ble_radar.history.cases import upsert_case
        with patch("ble_radar.history.cases._now", return_value="2026-04-18 12:00:00"):
            record = upsert_case("AA:BB:CC:DD:EE:FF", "r2")
    assert record["updated_at"] == "2026-04-18 12:00:00"


# ---------------------------------------------------------------------------
# get_case
# ---------------------------------------------------------------------------

def test_get_case_returns_existing():
    data = {
        "AA:BB:CC:DD:EE:FF": {
            "address": "AA:BB:CC:DD:EE:FF",
            "reason": "x",
            "status": "watch",
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }
    }
    p_load, p_save, _ = _patch_io(initial=data)
    with p_load, p_save:
        from ble_radar.history.cases import get_case
        result = get_case("aa:bb:cc:dd:ee:ff")  # lower-case lookup
    assert result is not None
    assert result["address"] == "AA:BB:CC:DD:EE:FF"


def test_get_case_returns_none_for_missing():
    p_load, p_save, _ = _patch_io()
    with p_load, p_save:
        from ble_radar.history.cases import get_case
        result = get_case("00:00:00:00:00:00")
    assert result is None


# ---------------------------------------------------------------------------
# save_cases
# ---------------------------------------------------------------------------

def test_save_cases_calls_save_json():
    with patch("ble_radar.history.cases.save_json") as mock_save:
        with patch("ble_radar.history.cases.load_json", return_value={}):
            from ble_radar.history.cases import save_cases
            save_cases({"X": {"address": "X"}})
    mock_save.assert_called_once()
    _, kwargs_or_arg = mock_save.call_args[0][0], mock_save.call_args[0][1]
    assert kwargs_or_arg == {"X": {"address": "X"}}


# ---------------------------------------------------------------------------
# Dashboard integration — panel present in HTML
# ---------------------------------------------------------------------------

def test_dashboard_renders_watch_cases_panel(monkeypatch):
    """render_dashboard_html must include the Watch/Cases panel marker."""
    import ble_radar.dashboard as db

    monkeypatch.setattr(db, "load_registry", lambda: {})
    monkeypatch.setattr(db, "load_last_scan", lambda: [])
    monkeypatch.setattr(db, "load_scan_history", lambda: [])
    monkeypatch.setattr(db, "load_watch_cases", lambda: {
        "AA:BB:CC:DD:EE:FF": {
            "address": "AA:BB:CC:DD:EE:FF",
            "reason": "test",
            "status": "watch",
            "created_at": "2026-04-18 00:00:00",
            "updated_at": "2026-04-18 00:00:00",
        }
    })

    html = db.render_dashboard_html([], "2026-04-18T00:00:00")
    assert "Watch / Cases" in html
    assert "AA:BB:CC:DD:EE:FF" in html
    assert "watch" in html


def test_dashboard_watch_cases_panel_empty_message(monkeypatch):
    """When no cases exist the panel shows the empty-state message."""
    import ble_radar.dashboard as db

    monkeypatch.setattr(db, "load_registry", lambda: {})
    monkeypatch.setattr(db, "load_last_scan", lambda: [])
    monkeypatch.setattr(db, "load_scan_history", lambda: [])
    monkeypatch.setattr(db, "load_watch_cases", lambda: {})

    html = db.render_dashboard_html([], "2026-04-18T00:00:00")
    assert "Watch / Cases" in html
    assert "Aucun cas" in html


def test_render_watch_cases_panel_top10_cap():
    """Panel shows at most 10 entries plus an overflow indicator."""
    from ble_radar.dashboard import render_watch_cases_panel
    cases = {
        f"AA:BB:CC:DD:EE:{i:02X}": {
            "address": f"AA:BB:CC:DD:EE:{i:02X}",
            "reason": "r",
            "status": "watch",
            "created_at": "2026-01-01",
            "updated_at": f"2026-01-{i+1:02d} 00:00:00",
        }
        for i in range(15)
    }
    html = render_watch_cases_panel(cases)
    # 10 visible + overflow line
    assert "… 5 de plus" in html
