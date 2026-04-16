# README STABLE - BLE Radar Omega

Ce document résume la base stable validée du projet BLE Radar Omega.

## 1) Commande de lancement

Option recommandée (script projet) :

```bash
./run_ble_omega.sh
```

Option directe (module principal) :

```bash
python3 -m ble_radar.app
```

## 2) Commande de revalidation automatique

Pour rejouer automatiquement les centres stabilisés :

```bash
./auto_menu_test.sh
```

Le script exécute des scénarios menu sur les centres validés et écrit un log horodaté par centre dans `logs/`.

## 3) Description rapide des centres testés

- Snapshot : vérification de la création/consultation de snapshot via le menu automatique.
- Sentinel : validation des flux d'analyse tactique (escalades/campaigns/watch).
- Oracle : validation de la projection de risque et de la sortie associée.
- Aegis : validation du moteur d'incidents composés, y compris le correctif de robustesse des comparaisons de seuils.
- Commander : validation du pilotage global et des entrées de menu de supervision.

## 4) Emplacement des logs

Les logs d'exécution se trouvent dans :

- `logs/` : logs des campagnes automatiques (`snapshot_test_*.log`, `sentinel_test_*.log`, `oracle_test_*.log`, `aegis_test_*.log`, `commander_test_*.log`).
- `logs/omega_live.log` : log agrégé de la boucle de lancement continu (`run_omega_loop.sh`).
- `logs/old_failures/` : anciens logs d'échec conservés.

## 5) Archive stable créée

Les sauvegardes de stabilisation sont archivées dans `backups_old/`.

Point de référence stable lié au correctif AEGIS :

- `backups_old/aegis.py.bak-safeint-final-20260416-115932`

Autres snapshots de sécurité :

- `backups_old/app.py.bak-aegis-safeint-20260416-104910`
- `backups_old/app.py.bak-aegis-fix-20260416-113500`
- `backups_old/app.py.bak-aegis-fix-20260416-113531`

## 6) Procédure de sauvegarde/restauration

### Sauvegarde rapide (recommandée avant modification)

Depuis la racine du projet :

```bash
TS="$(date +%F_%H-%M-%S)"
mkdir -p backups_old
cp ble_radar/aegis.py "backups_old/aegis.py.bak-$TS"
cp ble_radar/app.py "backups_old/app.py.bak-$TS"
cp ble_radar/commander.py "backups_old/commander.py.bak-$TS"
cp ble_radar/ui.py "backups_old/ui.py.bak-$TS"
```

### Restauration d'un fichier

Exemple pour restaurer AEGIS depuis le snapshot stable :

```bash
cp backups_old/aegis.py.bak-safeint-final-20260416-115932 ble_radar/aegis.py
```

Puis revalidation :

```bash
./auto_menu_test.sh
```

## 7) Note sur la build stable validée

La validation stable est matérialisée par le fichier `STABLE_BUILD_OK.txt` avec la mention :

- `BLE Radar Omega - build stable validé le 2026-04-16 12:09`

Cela correspond a la passe de stabilisation où les modules Snapshot, Sentinel, Oracle, Aegis et Commander ont été revalidés automatiquement.
