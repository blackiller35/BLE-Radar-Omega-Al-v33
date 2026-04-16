#!/usr/bin/env bash
set -u

cd "$(dirname "$0")" || exit 1

if [ -d ".venv" ]; then
  . .venv/bin/activate
fi

mkdir -p logs

echo "[OMEGA] démarrage $(date)" | tee -a logs/omega_live.log

while true; do
  ts="$(date +%F_%H-%M-%S)"
  echo "===== $ts =====" | tee -a logs/omega_live.log
  python3 -m ble_radar.app 2>&1 | tee -a logs/omega_live.log
  echo | tee -a logs/omega_live.log
  sleep 3
done
