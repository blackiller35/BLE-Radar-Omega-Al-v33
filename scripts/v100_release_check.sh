#!/usr/bin/env bash
set -euo pipefail

echo "[1/5] Stable release manifest"
python3 - <<'PY'
from ble_radar.release_manifest import release_lines
for line in release_lines():
    print(line)
PY

echo
echo "[2/5] Tests unitaires"
python -m pytest -q

echo
echo "[3/5] Menu pipeline"
./auto_menu_test.sh

echo
echo "[4/5] Validation complémentaire"
if [[ -x ./scripts/run_full_validation.sh ]]; then
  ./scripts/run_full_validation.sh
else
  echo "  [SKIP] scripts/run_full_validation.sh absent"
fi

echo
echo "[5/5] État Git"
git status
