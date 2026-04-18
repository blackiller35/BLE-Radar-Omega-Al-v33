from ble_radar.watchlist.watchlist import match_watchlist


def test_watchlist_match_name():
    result = match_watchlist(
        {"name": "Tile Tracker", "vendor": "Tile", "address": "AA"},
        [{"name": "tile", "reason": "tracking"}],
    )
    assert result["matched"] is True
