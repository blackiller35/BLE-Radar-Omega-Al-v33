#!/usr/bin/env bash
set -u
cd "$(dirname "$0")" || exit 1

if [ -d ".venv" ]; then
  . .venv/bin/activate
fi

mkdir -p logs
TS="$(date +%F_%H-%M-%S)"

run_case() {
  local name="$1"
  local logfile="logs/${name}_${TS}.log"
  shift
  python3 -m ble_radar.app <<EOF >"$logfile" 2>&1
$*
EOF
  echo "[OK] $name -> $logfile"
}

run_case snapshot_test '28
2

4
40'

run_case sentinel_test '32
1

6
40'

run_case oracle_test '36
4
40'

run_case aegis_test '35
1

5
40'

run_case commander_test '39
7
40'

echo
echo "Derniers logs :"
ls -1t logs/*_"$TS".log
