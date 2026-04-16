from pathlib import Path
import json

from ble_radar.doctor import build_doctor_report, doctor_lines
from ble_radar.snapshots import create_snapshot, list_snapshots, restore_snapshot
from ble_radar.ui import *


DEFAULT_JSONS = {
    "state/whitelist.json": [],
    "state/watchlist.json": [],
    "state/live_devices.json": {},
    "state/last_scan.json": [],
    "history/scan_history.json": [],
    "history/trends.json": {},
    "state/saved_queries.json": [],
    "state/profile_mode.json": {"active": "balanced"},
    "state/mission_mode.json": {"active": "general"},
}


def integrity_status_label():
    report = build_doctor_report()
    files_ok = report["files_ok"] == report["files_total"]
    imports_ok = report["imports_ok"] == report["imports_total"]
    json_ok = report["json_ok"] == report["json_total"]

    if files_ok and imports_ok and json_ok:
        return "FORTRESS OK"
    if imports_ok and (files_ok or json_ok):
        return "FORTRESS WARN"
    return "FORTRESS ALERT"


def quick_repair_json():
    root = Path(__file__).resolve().parent.parent
    repaired = []

    for rel, default in DEFAULT_JSONS.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)

        needs_repair = False
        if not path.exists():
            needs_repair = True
        else:
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                needs_repair = True

        if needs_repair:
            path.write_text(json.dumps(default, indent=2, ensure_ascii=False), encoding="utf-8")
            repaired.append(rel)

    return repaired


def show_doctor_status():
    report = build_doctor_report()
    clear()
    banner()
    print(color("\nDoctor / Integrity status", CYAN, bold=True))
    print(hr())
    print(f"Fichiers : {report['files_ok']}/{report['files_total']}")
    print(f"Imports  : {report['imports_ok']}/{report['imports_total']}")
    print(f"JSON     : {report['json_ok']}/{report['json_total']}")
    print()
    print(f"État global: {integrity_status_label()}")
    pause()


def show_full_doctor():
    report = build_doctor_report()
    clear()
    banner()
    print(color("\nDoctor complet", CYAN, bold=True))
    print(hr())
    for line in doctor_lines(report):
        print(line)
    pause()


def doctor_menu():
    while True:
        clear()
        banner()
        print(color("\nFORTRESS / Doctor", CYAN, bold=True))
        print(hr())
        print("1) Status rapide")
        print("2) Doctor complet")
        print("3) Quick repair JSON")
        print("4) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            show_doctor_status()
        elif choice == "2":
            show_full_doctor()
        elif choice == "3":
            repaired = quick_repair_json()
            clear()
            banner()
            print(color("\nQuick repair JSON", CYAN, bold=True))
            print(hr())
            if repaired:
                for rel in repaired:
                    print(f"- réparé: {rel}")
            else:
                print(color("Aucune réparation nécessaire.", GREEN, bold=True))
            pause()
        elif choice == "4":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def snapshot_menu():
    while True:
        clear()
        banner()
        print(color("\nFORTRESS / Snapshots", CYAN, bold=True))
        print(hr())
        print("1) Créer un snapshot")
        print("2) Lister les snapshots")
        print("3) Restaurer un snapshot")
        print("4) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            snap = create_snapshot()
            clear()
            banner()
            print(color("\nSnapshot créé", CYAN, bold=True))
            print(hr())
            print(f"Stamp: {snap['stamp']}")
            print(f"Path : {snap['path']}")
            print(f"Copié: {', '.join(snap['copied']) if snap['copied'] else '-'}")
            pause()

        elif choice == "2":
            snaps = list_snapshots()
            clear()
            banner()
            print(color("\nListe des snapshots", CYAN, bold=True))
            print(hr())
            if not snaps:
                print(color("Aucun snapshot.", YELLOW, bold=True))
            else:
                for i, s in enumerate(snaps, start=1):
                    print(f"{i}) {s}")
            pause()

        elif choice == "3":
            snaps = list_snapshots()
            clear()
            banner()
            print(color("\nRestaurer un snapshot", CYAN, bold=True))
            print(hr())

            if not snaps:
                print(color("Aucun snapshot.", YELLOW, bold=True))
                pause()
                continue

            for i, s in enumerate(snaps, start=1):
                print(f"{i}) {s}")
            print("0) Retour")

            raw = input("Choix > ").strip()
            if raw == "0":
                continue
            if not raw.isdigit():
                continue

            idx = int(raw) - 1
            if not (0 <= idx < len(snaps)):
                continue

            result = restore_snapshot(str(snaps[idx]))
            clear()
            banner()
            print(color("\nSnapshot restauré", CYAN, bold=True))
            print(hr())
            print(f"Source   : {result['path']}")
            print(f"Restauré : {', '.join(result['restored']) if result['restored'] else '-'}")
            pause()

        elif choice == "4":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()
