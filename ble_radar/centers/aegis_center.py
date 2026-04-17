from ble_radar.aegis import (
    load_aegis_config,
    toggle_aegis_engine,
    shift_threshold,
    evaluate_aegis,
    get_playbook,
    playbook_lines,
    aegis_summary_lines,
)
from ble_radar.ui import *
from ble_radar.state import load_last_scan, load_scan_history
def show_aegis_quick_summary(devices):
    result = evaluate_aegis(devices, load_scan_history())
    print()
    print(color("AEGIS quick summary", CYAN, bold=True))
    print(hr())
    for line in aegis_summary_lines(result)[:8]:
        print(line)


def aegis_dashboard():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nAEGIS — Dashboard", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    result = evaluate_aegis(devices, load_scan_history())
    for line in aegis_summary_lines(result):
        print(line)
    pause()


def aegis_incidents_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nAEGIS — Incidents composés", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    result = evaluate_aegis(devices, load_scan_history())
    incidents = result.get("incidents", [])
    if not incidents:
        print(color("Aucun incident composé.", GREEN, bold=True))
        pause()
        return

    for inc in incidents:
        print(f"- [{inc['severity']}] {inc['title']} | score={inc['score']} | {inc['why']}")
    pause()


def aegis_playbooks_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nAEGIS — Playbooks", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    result = evaluate_aegis(devices, load_scan_history())
    incidents = result.get("incidents", [])
    if not incidents:
        print(color("Aucun playbook actif.", GREEN, bold=True))
        pause()
        return

    for i, inc in enumerate(incidents, start=1):
        print(f"{i}) {inc['title']} | playbook={inc['playbook']}")
    print("0) Retour")

    raw = input("Choix > ").strip()
    if raw == "0":
        return
    if not raw.isdigit():
        return

    idx = int(raw) - 1
    if not (0 <= idx < len(incidents)):
        return

    playbook = get_playbook(incidents[idx]["playbook"])
    clear()
    banner()
    print(color("\nAEGIS — Playbook détaillé", CYAN, bold=True))
    print(hr())
    for line in playbook_lines(playbook):
        print(line)
    pause()


def aegis_thresholds_view():
    while True:
        cfg = load_aegis_config()
        th = cfg.get("thresholds", {})

        clear()
        banner()
        print(color("\nAEGIS — Seuils", CYAN, bold=True))
        print(hr())
        print(f"Moteur: {'ON' if cfg.get('enabled', True) else 'OFF'}")
        print("1) priority_high =", th.get("priority_high", 70))
        print("2) priority_critical =", th.get("priority_critical", 85))
        print("3) watch_hits =", th.get("watch_hits", 1))
        print("4) critical_alerts =", th.get("critical_alerts", 1))
        print("5) high_alerts =", th.get("high_alerts", 2))
        print("6) campaign_count =", th.get("campaign_count", 1))
        print("7) tracker_cluster =", th.get("tracker_cluster", 2))
        print("8) escalations =", th.get("escalations", 2))
        print("9) Toggle moteur")
        print("10) Retour")

        choice = input("Choix > ").strip()
        mapping = {
            "1": "priority_high",
            "2": "priority_critical",
            "3": "watch_hits",
            "4": "critical_alerts",
            "5": "high_alerts",
            "6": "campaign_count",
            "7": "tracker_cluster",
            "8": "escalations",
        }

        if choice in mapping:
            delta_raw = input("Delta (+1, -1, +5, -5) > ").strip()
            try:
                delta = int(delta_raw)
            except Exception:
                continue
            shift_threshold(mapping[choice], delta)
        elif choice == "9":
            toggle_aegis_engine()
        elif choice == "10":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def aegis_center():
    while True:
        clear()
        banner()
        print(color("\nAEGIS Center", CYAN, bold=True))
        print(hr())
        print("1) Dashboard")
        print("2) Incidents composés")
        print("3) Playbooks actifs")
        print("4) Seuils / moteur")
        print("5) Retour")

        choice = input("Choix > ").strip()
        if choice == "1":
            aegis_dashboard()
        elif choice == "2":
            aegis_incidents_view()
        elif choice == "3":
            aegis_playbooks_view()
        elif choice == "4":
            aegis_thresholds_view()
        elif choice == "5":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()
