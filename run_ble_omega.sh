#!/usr/bin/env bash
set -e

PROJECT_DIR="$HOME/Bureau/BLE-Radar-Omega-AI-v33"
cd "$PROJECT_DIR"

if [ -d ".venv" ]; then
  . .venv/bin/activate
fi

python3 -m py_compile ble_radar/*.py >/dev/null
python3 main.py
