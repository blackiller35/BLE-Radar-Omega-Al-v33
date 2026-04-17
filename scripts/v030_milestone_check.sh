#!/usr/bin/env bash
set -euo pipefail

echo "[1/5] Fichiers clés"
for f in \
  README.md \
  CHANGELOG.md \
  PROJECT_STATUS.md \
  Makefile \
  scripts/quickstart.sh \
  scripts/run_full_validation.sh \
  scripts/clean_runtime_artifacts.sh
do
  if [[ -f "$f" ]]; then
    echo "  [OK] $f"
  else
    echo "  [ERREUR] fichier manquant: $f"
    exit 1
  fi
done

echo
echo "[2/5] Syntaxe shell"
for f in \
  scripts/quickstart.sh \
  scripts/release_check.sh \
  scripts/release_summary.sh \
  scripts/run_full_validation.sh \
  scripts/clean_runtime_artifacts.sh \
  scripts/v030_milestone_check.sh
do
  if [[ -f "$f" ]]; then
    bash -n "$f"
    echo "  [OK] $f"
  fi
done

echo
echo "[3/5] Validation complète"
./scripts/run_full_validation.sh

echo
echo "[4/5] Aperçu nettoyage runtime"
./scripts/clean_runtime_artifacts.sh --dry-run

echo
echo "[5/5] État Git"
git status
