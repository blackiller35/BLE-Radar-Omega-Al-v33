#!/usr/bin/env bash
set -euo pipefail

echo "[1/5] Baseline opérateur"
python3 - <<'PY'
from ble_radar.operator_baseline import summary_lines

for line in summary_lines():
    print(line)
PY

echo
echo "[2/5] Workflow make"
make -n help quickstart run test validate clean-runtime-dry >/dev/null
echo "  [OK] Makefile dry-run"

echo
echo "[3/5] Validation complète"
./scripts/run_full_validation.sh

echo
echo "[4/5] Release guard final"
./scripts/v037_release_guard.sh

echo
echo "[5/5] État Git"
git status
