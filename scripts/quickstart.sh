#!/usr/bin/env bash
set -euo pipefail

if [[ ! -d ".venv" ]]; then
  echo "[1/4] Création du virtualenv"
  python3 -m venv .venv
else
  echo "[1/4] Virtualenv déjà présent"
fi

echo "[2/4] Activation"
# shellcheck disable=SC1091
source .venv/bin/activate

echo "[3/4] Installation des dépendances"
pip install -r requirements.txt

echo
echo "[4/4] Prêt"
echo "Commandes utiles :"
echo "  python -m ble_radar.app"
echo "  python -m pytest -q"
echo "  ./auto_menu_test.sh"
echo "  ./scripts/run_full_validation.sh"
echo "  make help"
