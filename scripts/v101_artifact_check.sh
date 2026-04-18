#!/usr/bin/env bash
set -euo pipefail

echo "[1/2] Artifact index"
python3 - <<'PY'
from ble_radar.artifact_index import artifact_index_lines, build_artifact_index
for line in artifact_index_lines(build_artifact_index()):
    print(line)
PY

echo
echo "[2/2] État Git"
git status
