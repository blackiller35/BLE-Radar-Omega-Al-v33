#!/usr/bin/env bash
set -euo pipefail

echo "[1/3] Tests unitaires"
python -m pytest -q

echo
echo "[2/3] Test menu"
./auto_menu_test.sh

echo
echo "[3/3] État Git"
git status
