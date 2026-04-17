# BLE Radar Omega AI

Projet Python de radar BLE modulaire avec centres d'analyse et de supervision :

- AEGIS
- ORACLE
- NEBULA
- CITADEL
- COMMANDER
- HELIOS
- ATLAS
- SENTINEL
- ARGUS
- OMEGA-X
- NEXUS
- TITAN

## Installation

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

## Lancement

python3 -m ble_radar.app

## Tests

python -m pytest -q
./auto_menu_test.sh

## Configuration

Le projet charge la configuration dans cet ordre :

1. valeurs par défaut internes
2. ble_radar/config.example.json
3. ble_radar/config.json si présent

### Exemple de config locale

cp ble_radar/config.example.json ble_radar/config.json

Puis modifier par exemple :

{
  "scan_timeout": 8,
  "live_scan_timeout": 4,
  "aegis": {
    "priority_high": 75,
    "priority_critical": 90
  },
  "automation": {
    "enabled": true
  }
}

## Releases

- `v0.1.0` : baseline stable initiale
- `v0.1.1` : validation runtime config + tests supplémentaires
- `v0.1.2` : README amélioré + documentation config locale
- `v0.1.3` : dépôt durci + config locale explicitement ignorée


## Statut

- runtime config branchée
- automation branchée
- aegis branché
- engine et app branchés
- CI GitHub Actions active
- 29 tests validés

## Configuration locale

Note importante : `ble_radar/config.json` est un fichier local de surcharge et ne doit pas être poussé sur GitHub.

## Vérification avant release

Avant de taguer une version, tu peux lancer :

    ./scripts/release_check.sh

Ce script exécute :
- python -m pytest -q
- ./auto_menu_test.sh
- git status
