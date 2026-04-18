# PROJECT STATUS

## Milestone
v0.3.0

## Core areas
- Runtime config
- Operator profiles
- JSON/CSV/TXT/HTML exports
- HTML dashboard
- AEGIS decision layer
- Automation rules
- Maintenance and healthcheck
- Developer quickstart / Makefile

## Validation commands
- `python -m pytest -q`
- `./auto_menu_test.sh`
- `./scripts/run_full_validation.sh`
- `./scripts/v030_milestone_check.sh`

## Release line
- v0.2.0 : changelog and release summary
- v0.2.1 : profile stabilization
- v0.2.2 : export stabilization
- v0.2.3 : dashboard readability
- v0.2.4 : AEGIS and automation stabilization
- v0.2.5 : maintenance and healthcheck
- v0.2.6 : packaging and developer UX
- v0.3.0 : final consolidated baseline

## Status
Repository ready as a stable working baseline.

## Final operator baseline
- v0.3.7 : release guard final
- workflow opérateur couvert de la normalisation device au safe automation
- commande finale de vérification : `./scripts/v037_release_guard.sh`

## v0.4.0 baseline
- v0.4.0 : baseline opérateur finale
- couverture de la chaîne principale du scan à l'investigation
- commande finale de vérification : `./scripts/v040_operator_readiness.sh`

## v0.4.1 extension
- v0.4.1 : scan manifests et catalogue de sessions
- résumé structuré des scans disponible

## v0.4.2 extension
- v0.4.2 : session catalog à partir des scan manifests
- vue consolidée des sessions récentes disponible

## v0.4.3 extension
- v0.4.3 : session diff entre manifests récents
- vue delta du dernier scan vs précédent disponible

## v0.4.4 extension
- v0.4.4 : export local du session diff
- rapport JSON/Markdown du dernier diff disponible

## v0.4.5 extension
- v0.4.5 : panneau session diff dans le dashboard
- vue rapide du dernier diff directement dans l'interface HTML

## v0.4.6 extension
- v0.4.6 : incident packs enrichis avec session diff
- contexte de variation entre scans disponible dans les packs

## v0.4.7 extension
- v0.4.7 : session catalog dans le dashboard
- vue rapide des sessions récentes directement dans l'interface HTML

## v0.4.8 extension
- v0.4.8 : incident packs enrichis avec session catalog
- contexte des sessions récentes disponible dans les packs

## v0.4.9 extension
- v0.4.9 : export context bundle
- contexte global latest session / recent sessions / session diff exportable

## v1.0.0 stable release
- v1.0.0 : stable release finale
- consolidation complète de la série v0.4.x
- commande finale de vérification : `./scripts/v100_release_check.sh`

## v1.0.1 patch
- v1.0.1 : artifact index patch
- index local des artefacts générés disponible

## v1.0.2 patch
- v1.0.2 : artifact index dans le dashboard
- vue rapide des artefacts locaux directement dans l'interface HTML

## v1.0.3 patch
- v1.0.3 : artifact cross-links patch
- navigation locale entre artefacts récents disponible
