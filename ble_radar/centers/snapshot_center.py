from ble_radar.atlas import atlas_snapshot
from ble_radar.snapshots import list_snapshots
from ble_radar.fortress import snapshot_menu
from ble_radar.ui import banner, clear, color, hr, pause, CYAN, RED, YELLOW


def create_snapshot(devices=None, namespace=None):
    if devices is None:
        scope = namespace if isinstance(namespace, dict) else {}
        for _name in ("devices", "last_devices", "current_devices", "scan_results", "results"):
            _val = scope.get(_name)
            if isinstance(_val, (list, tuple)):
                devices = list(_val)
                break
        else:
            devices = []
    return atlas_snapshot(devices)


def batch39_snapshots_restore_pro(create_snapshot_fn=None):
    snapshot_builder = create_snapshot_fn if callable(create_snapshot_fn) else create_snapshot

    while True:
        clear()
        banner()
        print(color("\n28) Snapshots / Restore Pro", CYAN, bold=True))
        print(hr())

        try:
            snaps = list_snapshots()
            print(f"Snapshots disponibles : {len(snaps)}")
        except Exception:
            print("Snapshots disponibles : ?")

        print()
        print("1) Ouvrir Snapshots / restauration")
        print("2) Créer un snapshot")
        print("3) Voir les snapshots récents")
        print("4) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            snapshot_menu()
        elif choice == "2":
            result = snapshot_builder()
            clear()
            banner()
            print(color("\nSnapshot créé", CYAN, bold=True))
            print(hr())
            print(result)
            pause()
        elif choice == "3":
            clear()
            banner()
            print(color("\nSnapshots récents", CYAN, bold=True))
            print(hr())
            snaps = list_snapshots()
            if not snaps:
                print(color("Aucun snapshot.", YELLOW, bold=True))
            else:
                for s in snaps[:20]:
                    print(f"- {s}")
            pause()
        elif choice == "4":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()
