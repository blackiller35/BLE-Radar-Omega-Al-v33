from ble_radar.state import load_last_scan, load_scan_history
from ble_radar.oracle import build_oracle_report, oracle_lines, project_rankings
from ble_radar.ui import banner, clear, color, hr, pause, CYAN, RED, YELLOW, GREEN


def show_oracle_quick_summary(devices):
    report = build_oracle_report(devices, load_scan_history())
    print()
    print(color("ORACLE quick summary", CYAN, bold=True))
    print(hr())
    for line in oracle_lines(report)[:8]:
        print(line)


def oracle_dashboard():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nORACLE — Forecast dashboard", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    report = build_oracle_report(devices, load_scan_history())
    for line in oracle_lines(report):
        print(line)
    pause()


def oracle_targets_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nORACLE — Risques à venir", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    rows = project_rankings(devices, load_scan_history(), 20)
    if not rows:
        print(color("Aucune projection.", GREEN, bold=True))
        pause()
        return

    for row in rows:
        d = row["device"]
        print(
            f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
            f"curr={row['current_priority']} -> proj={row['projected_priority']} | "
            f"state={row['future_state']} | conf={row['confidence']} | "
            f"drivers={', '.join(row['drivers']) if row['drivers'] else '-'}"
        )
    pause()


def oracle_center():
    while True:
        clear()
        banner()
        print(color("\nORACLE Center", CYAN, bold=True))
        print(hr())
        print("1) Forecast dashboard")
        print("2) Risques à venir")
        print("3) Retour")

        choice = input("Choix > ").strip()
        if choice == "1":
            oracle_dashboard()
        elif choice == "2":
            oracle_targets_view()
        elif choice == "3":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()
