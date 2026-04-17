#!/usr/bin/env bash
set -euo pipefail

echo "[1/6] Fichiers clés"
for f in \
  README.md \
  CHANGELOG.md \
  PROJECT_STATUS.md \
  Makefile \
  scripts/quickstart.sh \
  scripts/run_full_validation.sh \
  scripts/clean_runtime_artifacts.sh \
  scripts/v030_milestone_check.sh \
  ble_radar/device_contract.py \
  ble_radar/investigation.py \
  ble_radar/incident_pack.py \
  ble_radar/automation_safe.py
do
  if [[ -f "$f" ]]; then
    echo "  [OK] $f"
  else
    echo "  [ERREUR] fichier manquant: $f"
    exit 1
  fi
done

echo
echo "[2/6] Syntaxe shell"
for f in \
  scripts/quickstart.sh \
  scripts/release_check.sh \
  scripts/release_summary.sh \
  scripts/run_full_validation.sh \
  scripts/clean_runtime_artifacts.sh \
  scripts/v030_milestone_check.sh \
  scripts/v037_release_guard.sh
do
  if [[ -f "$f" ]]; then
    bash -n "$f"
    echo "  [OK] $f"
  fi
done

echo
echo "[3/6] Workflow make"
make -n help quickstart run test validate clean-runtime-dry >/dev/null
echo "  [OK] Makefile dry-run"

echo
echo "[4/6] Validation complète"
./scripts/run_full_validation.sh

echo
echo "[5/6] Milestone check + runtime dry-run"
./scripts/v030_milestone_check.sh
./scripts/clean_runtime_artifacts.sh --dry-run

echo
echo "[6/6] État Git"
git status
