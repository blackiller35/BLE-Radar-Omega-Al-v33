#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---dry-run}"

if [[ "$MODE" != "--dry-run" && "$MODE" != "--yes" ]]; then
  echo "Usage: ./scripts/clean_runtime_artifacts.sh [--dry-run|--yes]"
  exit 1
fi

mapfile -t ITEMS < <(python3 - <<'PY'
from pathlib import Path
from ble_radar.maintenance import find_runtime_artifacts

for p in find_runtime_artifacts(Path(".")):
    print(p.as_posix())
PY
)

if [[ "${#ITEMS[@]}" -eq 0 ]]; then
  echo "[INFO] Aucun artefact runtime trouvé."
  exit 0
fi

echo "[INFO] Artefacts détectés :"
for item in "${ITEMS[@]}"; do
  echo " - $item"
done

if [[ "$MODE" == "--dry-run" ]]; then
  echo
  echo "[INFO] Dry-run terminé. Relance avec --yes pour supprimer."
  exit 0
fi

echo
echo "[INFO] Suppression en cours..."
for item in "${ITEMS[@]}"; do
  rm -rf "$item"
  echo " [OK] supprimé: $item"
done

echo
echo "[OK] Nettoyage terminé."
