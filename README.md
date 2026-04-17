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
- `v0.1.4` : tests automation runtime ajoutés
- `v0.1.5` : helper de vérification avant release
- `v0.1.6` : helper de bootstrap pour la config locale
- `v0.2.0` : changelog + résumé de release + milestone consolidée


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

## Bootstrap config locale

Pour créer rapidement une config locale à partir de l'exemple :

    ./scripts/bootstrap_local_config.sh

Ce script :
- copie `ble_radar/config.example.json`
- crée `ble_radar/config.json` si absent
- n'écrase pas un fichier local existant

## Workflow release

Avant une release :

    ./scripts/release_check.sh

Pour générer un résumé rapide du dépôt :

    ./scripts/release_summary.sh

Pour lire l'historique des versions :

    cat CHANGELOG.md

## Maintenance locale

Validation complète :

    ./scripts/run_full_validation.sh

Nettoyage des artefacts runtime en aperçu :

    ./scripts/clean_runtime_artifacts.sh --dry-run

Nettoyage réel :

    ./scripts/clean_runtime_artifacts.sh --yes

## Quickstart développeur

Setup rapide :

    ./scripts/quickstart.sh

Commandes utiles :

    make help
    make run
    make test
    make menu-test
    make validate
    make clean-runtime-dry

## Milestone v0.3.0

Le projet atteint une base consolidée avec :

- configuration runtime stabilisée
- profils opérateur validés
- exports JSON/CSV validés
- dashboard HTML amélioré
- logique AEGIS / automation testée
- outils de maintenance disponibles
- quickstart développeur et Makefile disponibles

Commandes clés :

    make help
    make validate
    ./scripts/v030_milestone_check.sh
