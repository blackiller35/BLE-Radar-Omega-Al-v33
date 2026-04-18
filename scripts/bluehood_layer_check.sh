#!/usr/bin/env bash
set -e
echo "[1/4] import check"
python3 - <<'PY'
from ble_radar.bluehood_layer import enrich_devices_for_session

devices = [
    {"address": "AA:BB", "name": "Tile Tracker", "vendor": "Tile", "rssi": -58},
    {"address": "CC:DD", "name": "Beacon", "vendor": "Acme", "rssi": -77},
]
result = enrich_devices_for_session(devices, {}, "sess-demo", "2026-04-17T21:30:00")
print("devices_enriched =", len(result["devices_enriched"]))
print("watch_hits =", len(result["watch_hits"]))
print("top_correlated =", len(result["top_correlated"]))
PY

echo "[2/4] pytest"
pytest -q tests/test_bluehood_layer_*.py

echo "[3/4] git status"
git status --short

echo "[4/4] done"
echo "Bluehood-inspired layer ready."
