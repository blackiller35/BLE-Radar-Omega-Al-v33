#!/usr/bin/env bash
set -euo pipefail

SRC="ble_radar/config.example.json"
DST="ble_radar/config.json"

if [[ ! -f "$SRC" ]]; then
  echo "[ERREUR] $SRC introuvable"
  exit 1
fi

if [[ -f "$DST" ]]; then
  echo "[INFO] $DST existe déjà, rien à faire"
  exit 0
fi

cp "$SRC" "$DST"
echo "[OK] Config locale créée : $DST"
echo "[INFO] Tu peux maintenant l'éditer avec tes réglages locaux."
