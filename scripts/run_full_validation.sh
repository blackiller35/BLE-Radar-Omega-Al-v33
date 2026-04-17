#!/usr/bin/env bash
set -euo pipefail

echo "[1/4] Vérification syntaxe shell"
for f in \
  scripts/release_check.sh \
  scripts/bootstrap_local_config.sh \
  scripts/release_summary.sh \
  scripts/run_full_validation.sh \
  scripts/clean_runtime_artifacts.sh
do
  if [[ -f "$f" ]]; then
    bash -n "$f"
    echo "  [OK] $f"
  fi
done

echo
echo "[2/4] Tests unitaires"
python -m pytest -q

echo
echo "[3/4] Test menu"
./auto_menu_test.sh

echo
echo "[4/4] État Git"
git status
