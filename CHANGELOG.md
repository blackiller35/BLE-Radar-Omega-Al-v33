# CHANGELOG

## v1.0.1
- module `ble_radar/artifact_index.py` ajouté
- script `scripts/v101_artifact_check.sh` ajouté
- index local des artefacts générés ajouté
- README / PROJECT_STATUS / CHANGELOG mis à jour
- base de tests portée à 161 tests

## v1.0.0
- module `ble_radar/release_manifest.py` ajouté
- script `scripts/v100_release_check.sh` ajouté
- stable release finale formalisée
- README / PROJECT_STATUS / CHANGELOG consolidés
- base de tests portée à 155 tests

## v0.4.9
- module `ble_radar/export_context.py` ajouté
- export global latest session / recent sessions / session diff ajouté
- sortie JSON + Markdown du contexte global ajoutée
- README / PROJECT_STATUS / CHANGELOG mis à jour
- base de tests portée à 149 tests
\n

## v0.4.8
- incident packs enrichis avec le session catalog
- manifest JSON enrichi avec `session_overview` et `recent_sessions`
- résumé Markdown enrichi avec la dernière session et les sessions récentes
- README / PROJECT_STATUS / CHANGELOG mis à jour
- base de tests portée à 144 tests
\n

## v0.4.7
- panneaux `Latest session overview` et `Sessions récentes` ajoutés au dashboard HTML
- intégration de `build_session_catalog()` dans `dashboard.py`
- intégration de `latest_session_overview()` dans `dashboard.py`
- README / PROJECT_STATUS / CHANGELOG mis à jour
- base de tests portée à 141 tests
\n

## v0.4.6
- incident packs enrichis avec le dernier session diff
- manifest JSON enrichi avec `session_diff`
- résumé Markdown enrichi avec le diff courant vs précédent
- README / PROJECT_STATUS / CHANGELOG mis à jour
- base de tests portée à 135 tests
\n

## v0.4.5
- panneau `Session diff récent` ajouté au dashboard HTML
- intégration de `latest_session_diff()` dans `dashboard.py`
- lecture directe du diff courant vs précédent ajoutée
- README / PROJECT_STATUS / CHANGELOG mis à jour
- base de tests portée à 132 tests

## v0.4.4
- module `ble_radar/session_diff_report.py` ajouté
- export local JSON/Markdown du session diff ajouté
- catalogue local des rapports de diff ajouté
- README / PROJECT_STATUS / CHANGELOG mis à jour
- base de tests portée à 126 tests

## v0.4.3
- module `ble_radar/session_diff.py` ajouté
- comparaison structurée entre manifests récents ajoutée
- vue delta latest vs previous ajoutée
- README / PROJECT_STATUS / CHANGELOG mis à jour
- base de tests portée à 120 tests

## v0.4.2
- module `ble_radar/session_catalog.py` ajouté
- lecture structurée des scan manifests ajoutée
- vue latest session ajoutée
- README / PROJECT_STATUS / CHANGELOG mis à jour
- base de tests portée à 114 tests

## v0.4.1
- module `ble_radar/scan_manifest.py` ajouté
- génération de scan manifests structurés ajoutée
- catalogue local des manifests ajouté
- README / PROJECT_STATUS / CHANGELOG mis à jour
- base de tests portée à 108 tests

## v0.4.0
- module `ble_radar/operator_baseline.py` ajouté
- script `scripts/v040_operator_readiness.sh` ajouté
- baseline opérateur finale formalisée
- README / PROJECT_STATUS / CHANGELOG consolidés
- base de tests portée à 102 tests

## v0.3.7
- script `scripts/v037_release_guard.sh` ajouté
- garde-fou final pour les releases ajouté
- README enrichi avec le release guard final
- PROJECT_STATUS enrichi avec la baseline opérateur finale
- base de tests portée à 96 tests

## v0.3.0
- `PROJECT_STATUS.md` ajouté
- script `scripts/v030_milestone_check.sh` ajouté
- README enrichi avec la milestone v0.3.0
- consolidation finale de la série v0.2.x
- base de tests portée à 60 tests

## v0.2.0
- changelog ajouté
- helper `scripts/release_summary.sh` ajouté
- README enrichi avec le workflow de release
- base de tests maintenue
- milestone mineure stable consolidée

## v0.1.6
- helper `scripts/bootstrap_local_config.sh` ajouté

## v0.1.5
- helper `scripts/release_check.sh` ajouté

## v0.1.4
- tests automation runtime ajoutés

## v0.1.3
- `ble_radar/config.json` ignoré par Git
- README clarifié sur la config locale

## v0.1.2
- README amélioré
- documentation config locale ajoutée

## v0.1.1
- tests runtime config ajoutés
- tests app runtime scan settings ajoutés

## v0.1.0
- baseline stable initiale
