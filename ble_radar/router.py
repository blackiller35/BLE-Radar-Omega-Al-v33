from pathlib import Path
import subprocess

from ble_radar.ui import *
from ble_radar.intel import get_vendor_summary
from ble_radar.inspector import inspect_to_lines


def open_html_report(path):
    try:
        subprocess.Popen(
            ["xdg-open", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def render_devices(devices, title="Résultats"):
    clear()
    banner()
    print(color(f"\n{title}", CYAN, bold=True))
    print(hr(180))
    print(
        f"{color('Nom', BLUE, bold=True):18} "
        f"{color('Adresse', BLUE, bold=True):20} "
        f"{color('Vendor', BLUE, bold=True):12} "
        f"{color('Profil', BLUE, bold=True):16} "
        f"{color('RSSI', BLUE, bold=True):>6} "
        f"{color('Risk', BLUE, bold=True):>6} "
        f"{color('Follow', BLUE, bold=True):>8} "
        f"{color('Conf', BLUE, bold=True):>6} "
        f"{color('Final', BLUE, bold=True):>6} "
        f"{color('Alerte', BLUE, bold=True):10} "
        f"{color('Seen', BLUE, bold=True):>5} "
        f"{color('Flags', BLUE, bold=True):20} "
        f"{color('Raison', BLUE, bold=True)}"
    )
    print(hr(180))

    for d in devices:
        final = d.get("final_score", d.get("score", 0))
        tone = RED if final >= 60 else YELLOW if final >= 35 else GREEN
        flags_txt = ",".join(d.get("flags", [])) if d.get("flags") else "-"

        print(
            f"{color(compact(d.get('name', 'Inconnu'), 18), tone):18} "
            f"{color(d.get('address', '-'), tone):20} "
            f"{color(compact(d.get('vendor', 'Unknown'), 12), tone):12} "
            f"{color(compact(d.get('profile', 'general_ble'), 16), tone):16} "
            f"{color(str(d.get('rssi', '-')), tone):>6} "
            f"{color(str(d.get('risk_score', d.get('score', 0))), tone, bold=True):>6} "
            f"{color(str(d.get('follow_score', 0)), tone, bold=True):>8} "
            f"{color(str(d.get('confidence_score', 0)), tone, bold=True):>6} "
            f"{color(str(final), tone, bold=True):>6} "
            f"{color(d.get('alert_level', 'faible'), tone):10} "
            f"{color(str(d.get('seen_count', 0)), tone):>5} "
            f"{color(compact(flags_txt, 20), tone):20} "
            f"{color(compact(d.get('reason_short', 'normal'), 24), tone)}"
        )

    print()
    print(color(f"Total appareils: {len(devices)}", GREEN, bold=True))


def show_engine_summary(summary: dict):
    print()
    print(color("Résumé moteur", CYAN, bold=True))
    print(hr())
    print(f"Total     : {summary.get('total', 0)}")
    print(f"Critiques : {summary.get('critical', 0)}")
    print(f"Élevés    : {summary.get('high', 0)}")
    print(f"Moyens    : {summary.get('medium', 0)}")
    print(f"Trackers  : {summary.get('trackers', 0)}")
    print(f"Nouveaux  : {summary.get('added', 0)}")
    print(f"Disparus  : {summary.get('removed', 0)}")
    print(f"Communs   : {summary.get('common', 0)}")


def show_report_paths(paths):
    print()
    print(color("Rapports générés", CYAN, bold=True))
    print(hr())
    print(color("JSON    :", BLUE, bold=True), paths["json"])
    print(color("CSV     :", BLUE, bold=True), paths["csv"])
    print(color("TXT     :", BLUE, bold=True), paths["txt"])
    print(color("HTML    :", BLUE, bold=True), paths["html"])
    if paths.get("operator_panel_html"):
        print(color("OPANEL  :", BLUE, bold=True), paths["operator_panel_html"])
    print(color("HISTORY :", BLUE, bold=True), paths["history"])
    print(color("SUMMARY :", BLUE, bold=True), paths["summary"])


def show_vendor_summary(devices):
    print()
    print(color("Résumé vendors", CYAN, bold=True))
    print(hr())
    for vendor, count in get_vendor_summary(devices)[:10]:
        print(f"{vendor} : {count}")


def show_comparison_summary(comp):
    print()
    print(color("Comparaison", CYAN, bold=True))
    print(hr())

    if not comp:
        print(color("Aucune comparaison disponible.", YELLOW, bold=True))
        return

    if "previous_stamp" in comp:
        print(f"Précédent : {comp.get('previous_stamp', '-')}")
        print(f"Actuel    : {comp.get('current_stamp', '-')}")
        print()

    print(f"Nouveaux : {len(comp.get('added', []))}")
    print(f"Disparus : {len(comp.get('removed', []))}")
    print(f"Communs  : {len(comp.get('common', []))}")


def show_named_list(title, entries):
    clear()
    banner()
    print(color(f"\n{title}", CYAN, bold=True))
    print(hr())
    if not entries:
        print(color("Liste vide.", YELLOW, bold=True))
    else:
        for i, item in enumerate(entries, start=1):
            print(f"{i}) {item.get('name','')} | {item.get('address','')}")
    pause()


def show_history_view(hist):
    clear()
    banner()
    print(color("\nHistorique local", CYAN, bold=True))
    print(hr())

    if not hist:
        print(color("Historique vide.", YELLOW, bold=True))
        pause()
        return

    items = sorted(
        hist.items(),
        key=lambda x: (x[1].get("seen_count", 0), x[1].get("near_count", 0)),
        reverse=True,
    )

    for addr, info in items[:30]:
        follow = " | suivi?" if info.get("possible_suivi") else ""
        print(
            f"{info.get('name','Inconnu')} | {addr} | "
            f"vus:{info.get('seen_count',0)} | near:{info.get('near_count',0)} | "
            f"rssi:{info.get('last_rssi','-')} | "
            f"alert:{info.get('last_alert_level','faible')} | "
            f"profile:{info.get('last_profile','unknown')}{follow}"
        )
    pause()


def show_inspection_view(device):
    clear()
    banner()
    print(color("\nInspection détaillée", CYAN, bold=True))
    print(hr())
    for line in inspect_to_lines(device):
        print(line)
    pause()


def show_history_search_results(query, results):
    clear()
    banner()
    print(color(f"\nRésultats historique: {query}", CYAN, bold=True))
    print(hr())

    if not results:
        print(color("Aucun résultat.", YELLOW, bold=True))
        pause()
        return

    for row in results:
        d = row["device"]
        print(
            f"[{row.get('stamp','-')}] "
            f"{d.get('name','Inconnu')} | {d.get('address','-')} | "
            f"{d.get('vendor','Unknown')} | {d.get('profile','-')} | "
            f"score={d.get('final_score', d.get('score', 0))} | "
            f"alert={d.get('alert_level','faible')} | "
            f"match={row.get('score',0)}"
        )
    pause()


def show_query_suggestions_list(suggestions):
    clear()
    banner()
    print(color("\nSuggestions de requêtes", CYAN, bold=True))
    print(hr())

    if not suggestions:
        print(color("Aucune suggestion.", YELLOW, bold=True))
    else:
        for q in suggestions:
            print(f"- {q}")
    pause()


def select_device_interactive(devices, title="Choisir un appareil", limit=20):
    clear()
    banner()
    print(color(f"\n{title}", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun appareil.", YELLOW, bold=True))
        pause()
        return None

    top = devices[:limit]
    for i, d in enumerate(top, start=1):
        print(
            f"{i}) {d.get('name','Inconnu')} | {d.get('address','-')} | "
            f"{d.get('alert_level','faible')} | {d.get('final_score', d.get('score', 0))}"
        )
    print("0) Retour")

    raw = input("Choix > ").strip()
    try:
        idx = int(raw)
    except Exception:
        return None

    if idx == 0 or not (1 <= idx <= len(top)):
        return None

    return top[idx - 1]


def investigation_menu(actions: dict):
    while True:
        clear()
        banner()
        print(color("\nCentre d'investigation", CYAN, bold=True))
        print(hr())
        print("1) Recherche dans le dernier scan")
        print("2) Recherche dans l'historique")
        print("3) Expliquer un appareil du dernier scan")
        print("4) Comparer les 2 derniers scans")
        print("5) Suggestions de requêtes")
        print("6) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            actions["search_last"]()
        elif choice == "2":
            actions["search_history"]()
        elif choice == "3":
            actions["inspect_last"]()
        elif choice == "4":
            actions["compare_last_two"]()
        elif choice == "5":
            actions["suggest_queries"]()
        elif choice == "6":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()
