#!/usr/bin/env bash
set -euo pipefail

echo "[1/2] Activity timeline"
python3 - <<'PY'
from ble_radar.activity_timeline import build_activity_timeline, timeline_lines
for line in timeline_lines(build_activity_timeline(limit=10)):
    print(line)
PY

echo
echo "[2/2] État Git"
git status
