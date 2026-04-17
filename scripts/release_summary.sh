#!/usr/bin/env bash
set -euo pipefail

mkdir -p reports
STAMP=$(date +%F_%H-%M-%S)
OUT="reports/release_summary_${STAMP}.md"

BRANCH=$(git branch --show-current)
COMMIT=$(git rev-parse --short HEAD)
TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "aucun")
STATUS=$(git status --short || true)

{
  echo "# Release Summary"
  echo
  echo "- Date: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "- Branche: ${BRANCH}"
  echo "- Commit: ${COMMIT}"
  echo "- Dernier tag: ${TAG}"
  echo
  echo "## Vérifications conseillées"
  echo
  echo "    python -m pytest -q"
  echo "    ./auto_menu_test.sh"
  echo "    git status"
  echo
  echo "## État Git"
  echo
  if [[ -n "${STATUS}" ]]; then
    printf '```\n%s\n```\n' "${STATUS}"
  else
    echo "Copie de travail propre."
  fi
} > "${OUT}"

echo "[OK] Rapport créé : ${OUT}"
cat "${OUT}"
