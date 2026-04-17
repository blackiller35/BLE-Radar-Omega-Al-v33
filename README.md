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

## Contrat device

Le projet dispose maintenant d'une base de contrat locale pour les appareils :

- `ble_radar/device_contract.py`
- normalisation des champs attendus
- helper d'explication de score

Exemple d'usage :

    from ble_radar.device_contract import normalize_device, explain_device

## Scoring explicable

Le dashboard HTML et les exports propagent maintenant un résumé d'explication de score.

Exemples :
- colonne `Explication` dans le dashboard
- colonne `score_explanation` dans le CSV
- résumé `explication:` dans le TXT

## Workflow d'investigation

Le projet dispose maintenant d'une base locale de cas d'investigation :

- `ble_radar/investigation.py`
- création de cas
- ajout de notes
- statut `open` / `watch` / `closed`
- résumé de cas

Exemple d'usage :

    from ble_radar.investigation import create_case, add_case_note, set_case_status, summarize_case

## Dashboard pro

Le dashboard HTML inclut maintenant :

- résumé comparatif vs scan précédent
- bloc incidents visibles
- bloc cas d'investigation récents
- filtres `watch hits` / `trackers`
- filtre vendor plus pratique

## Incident packs

Le projet peut maintenant générer un incident pack local à partir d'un cas :

- `ble_radar/incident_pack.py`
- manifest `incident_pack.json`
- résumé `incident_summary.md`
- rapprochement avec les devices du dernier scan

Exemple d'usage :

    from ble_radar.incident_pack import build_incident_pack

## Automation safe mode

Le projet dispose maintenant d'un mode dry-run pour l'automation :

- `ble_radar/automation_safe.py`
- collecte des règles déclenchées
- trace lisible du contexte
- liste des actions proposées sans exécution réelle

Exemple d'usage :

    from ble_radar.automation_safe import build_dry_run_report

## Release guard final

Le projet dispose maintenant d'un garde-fou final avant release :

- `./scripts/v037_release_guard.sh`
- vérification des briques clés
- validation du workflow Makefile
- relance de la validation complète
- aperçu du nettoyage runtime

Commande :

    ./scripts/v037_release_guard.sh

## Baseline opérateur v0.4.0

Le projet atteint maintenant une baseline opérateur finale avec :

- runtime config stabilisée
- contrat device centralisé
- scoring explicable
- dashboard pro
- workflow d'investigation
- incident packs
- automation safe mode
- release guard final

Commande de vérification :

    ./scripts/v040_operator_readiness.sh

## Scan manifests

Le projet peut maintenant générer un manifest structuré par scan :

- `ble_radar/scan_manifest.py`
- résumé des alertes
- compte des watch hits / trackers
- top vendors
- top devices
- catalogue local des manifests

Exemple d'usage :

    from ble_radar.scan_manifest import build_scan_manifest, save_scan_manifest
