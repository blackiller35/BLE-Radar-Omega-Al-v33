from pathlib import Path
import time

from ble_radar.config import FULL_SCAN_SECONDS, LIVE_SCAN_SECONDS
from ble_radar.engine import run_engine_scan, run_engine_cycle, summarize_engine_result
from ble_radar.selectors import only_alerts, only_trackers, sort_by_score
from ble_radar.views import (
    view_critical,
    view_high_plus,
    view_trackers,
    view_watch_hits,
    view_new_devices,
    view_nearby,
    view_apple_like,
    view_random_mac,
    view_unknown_vendor,
    view_top_hot,
    summarize_views,
)
from ble_radar.state import (
    load_last_scan,
    load_live_history,
    load_whitelist,
    save_whitelist,
    load_watchlist,
    save_watchlist,
    load_scan_history,
)
from ble_radar.query import query_devices, query_history, suggest_queries
from ble_radar.inspector import pick_top_devices
from ble_radar.search import compare_last_two_scans
from ble_radar.commands import parse_command, command_help_lines
from ble_radar.sessions import load_saved_queries, add_saved_query, remove_saved_query
from ble_radar.audit import build_audit_package, save_audit_package
from ble_radar.profiles import get_active_profile, list_profiles, set_profile_key
from ble_radar.metrics import compute_metrics, metrics_to_lines
from ble_radar.replay import list_recent_scans, scan_summary_lines, scan_devices
from ble_radar.ops import (
    get_scan_mode,
    radio_health,
    compare_scan_sets,
    changed_alerts,
    tracker_rank,
)
from ble_radar.missions import get_active_mission, list_missions, set_active_mission
from ble_radar.mission_control import build_mission_control, mission_control_lines
from ble_radar.router import (
    open_html_report,
    render_devices,
    show_engine_summary,
    show_report_paths,
    show_vendor_summary,
    show_comparison_summary,
    show_named_list,
    show_history_view,
    show_inspection_view,
    show_history_search_results,
    show_query_suggestions_list,
    select_device_interactive,
    investigation_menu,
)
from ble_radar.ui import *
from ble_radar.fortress import doctor_menu, snapshot_menu, integrity_status_label
from ble_radar.nexus import search_device_summaries, timeline_for_address, timeline_lines, persistence_rankings, recurrent_pattern_rankings, daily_change_summary, daily_change_lines, save_enriched_incident, incident_lines
from ble_radar.knowledge import sync_current_devices, top_known_devices, search_known_devices, set_manual_label
from ble_radar.behavior import rank_behavior_anomalies
from ble_radar.daily_report import build_daily_report, daily_report_lines, save_daily_report
from ble_radar.argus import rank_priority, build_case_file, case_file_lines, argus_recommended_actions
from ble_radar.sentinel import build_sentinel_report, sentinel_lines, save_watch_session
from ble_radar.atlas import atlas_snapshot, hot_edges, neighbors_for_address, vendor_profile_clusters, risk_groups
from ble_radar.helios import build_helios_report, helios_lines
from ble_radar.aegis import load_aegis_config, toggle_aegis_engine, shift_threshold, evaluate_aegis, get_playbook, playbook_lines, aegis_summary_lines
from ble_radar.oracle import build_oracle_report, oracle_lines, project_rankings
from ble_radar.nebula import load_casebook, list_cases, upsert_case_from_device, append_case_note, close_case, build_nebula_report, nebula_lines, build_session_summary, session_summary_lines, save_session_summary
from ble_radar.citadel import build_citadel_report, citadel_lines, save_citadel_report, export_global_bundle, export_incident_pack, run_maintenance_cycle
from ble_radar.commander import MANUAL_FILE, build_startup_status, startup_lines, build_commander_brief, commander_brief_lines, workflow_lines
from ble_radar.stableplus import build_stableplus_report, stableplus_lines
from ble_radar.eventlog import read_events
from ble_radar.automation import load_automation_config, toggle_automation_engine, toggle_rule_by_index, run_automation_pipeline
from ble_radar.centers.snapshot_center import (
    create_snapshot as _create_snapshot_impl,
    batch39_snapshots_restore_pro as _batch39_snapshots_restore_pro_impl,
)


def active_profile():
    return get_active_profile()


def active_mission():
    return get_active_mission()


def prof_scan_seconds():
    return int(active_profile().get("scan_seconds", FULL_SCAN_SECONDS))


def prof_live_seconds():
    return int(active_profile().get("live_seconds", LIVE_SCAN_SECONDS))


def prof_alert_floor():
    return str(active_profile().get("alert_floor", "moyen"))


def show_radio_health(devices):
    health = radio_health(devices)
    print()
    print(color("Santé radio", CYAN, bold=True))
    print(hr())
    print(f"Score global : {health['score']}/100")
    print(f"État         : {health['label']}")
    print(f"RSSI moyen   : {health['avg_rssi']}")
    print(f"Alerts       : {health['alerts']}")
    print(f"Trackers     : {health['trackers']}")
    print(f"Unknown vend.: {health['unknown_vendor']}")
    print(f"MAC random   : {health['random_mac']}")


def show_mission_summary(devices):
    data = build_mission_control(devices)
    print()
    print(color("Mission Control", CYAN, bold=True))
    print(hr())
    for line in mission_control_lines(data):
        print(line)




def show_automation_result(auto_result):
    print()
    print(color("Automation engine", CYAN, bold=True))
    print(hr())

    if not auto_result.get("enabled", True):
        print("Moteur automation: désactivé")
        return

    ctx = auto_result.get("context", {})
    print(f"critical    : {ctx.get('critical', 0)}")
    print(f"high        : {ctx.get('high', 0)}")
    print(f"trackers    : {ctx.get('trackers', 0)}")
    print(f"watch_hits  : {ctx.get('watch_hits', 0)}")
    print(f"health      : {ctx.get('health_score', 0)} ({ctx.get('health_label', '-')})")

    executed = auto_result.get("executed", [])
    if not executed:
        print("Aucune action auto exécutée.")
        return

    print()
    print("Actions exécutées:")
    for item in executed:
        print(f"- {item.get('label', item.get('action', '-'))}")


def show_event_log():
    events = read_events(60)
    clear()
    banner()
    print(color("\nJournal d'événements", CYAN, bold=True))
    print(hr())

    if not events:
        print(color("Aucun événement.", YELLOW, bold=True))
        pause()
        return

    for e in events:
        print(f"[{e.get('ts','-')}] {e.get('level','-').upper()} | {e.get('kind','-')} | {e.get('message','-')}")
    pause()


def automation_center():
    while True:
        cfg = load_automation_config()
        clear()
        banner()
        print(color("\nAutomation Center", CYAN, bold=True))
        print(hr())
        print(f"Moteur global: {'ON' if cfg.get('enabled', True) else 'OFF'}")
        print()

        rules = cfg.get("rules", [])
        for i, r in enumerate(rules, start=1):
            print(
                f"{i}) [{'ON' if r.get('enabled', True) else 'OFF'}] "
                f"{r.get('label','-')} | cond={r.get('condition','-')} | "
                f"seuil={r.get('threshold','-')} | action={r.get('action','-')}"
            )

        print()
        print("1) Toggle moteur global")
        print("2) Toggle une règle")
        print("3) Tester les automations sur le dernier scan")
        print("4) Voir le journal d'événements")
        print("5) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            toggle_automation_engine()
        elif choice == "2":
            raw = input("Index règle > ").strip()
            if raw.isdigit():
                toggle_rule_by_index(int(raw) - 1)
        elif choice == "3":
            devices = load_last_scan()
            clear()
            banner()
            print(color("\nTest automation sur dernier scan", CYAN, bold=True))
            print(hr())
            if not devices:
                print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
            else:
                result = run_automation_pipeline(devices)
                show_automation_result(result)
            pause()
        elif choice == "4":
            show_event_log()
        elif choice == "5":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()

def do_scan_mode(mode_key):
    mode = get_scan_mode(mode_key)
    result = run_engine_cycle(seconds=mode["seconds"])
    devices = result["devices"]

    if not devices:
        clear()
        banner()
        print(color("\nAucun appareil détecté.", YELLOW, bold=True))
        pause()
        return

    render_devices(devices, f"Scan IA — mode {mode['label']} [{active_profile()['label']}]")
    show_engine_summary(summarize_engine_result(result))
    show_radio_health(devices)
    show_mission_summary(devices)
    if result.get("paths"):
        show_report_paths(result["paths"])
        open_html_report(result["paths"]["html"])
    show_vendor_summary(devices)
    show_comparison_summary(result.get("comparison"))
    pause()


def do_scan():
    while True:
        clear()
        banner()
        print(color(f"\nScan intelligent [{active_profile()['label']} | {active_mission()['label']}]", CYAN, bold=True))
        print(hr())
        print("1) Mode rapide")
        print("2) Mode normal")
        print("3) Mode profond")
        print("4) Retour")

        choice = input("Choix > ").strip()
        if choice == "1":
            do_scan_mode("quick")
        elif choice == "2":
            do_scan_mode("normal")
        elif choice == "3":
            do_scan_mode("deep")
        elif choice == "4":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def show_alerts_by_level(level_label, level_key):
    devices = only_alerts(run_engine_scan(prof_scan_seconds()), level_key)
    if not devices:
        clear()
        banner()
        print(color(f"\nAucune alerte pour le niveau: {level_label}", GREEN, bold=True))
        pause()
        return
    render_devices(devices, f"Alertes — {level_label}")
    pause()


def show_alerts_only():
    while True:
        clear()
        banner()
        print(color("\nAlertes prioritaires", CYAN, bold=True))
        print(hr())
        print("1) Niveau moyen et plus")
        print("2) Niveau élevé et plus")
        print("3) Niveau critique seulement")
        print("4) Retour")

        choice = input("Choix > ").strip()
        if choice == "1":
            show_alerts_by_level("moyen+", "moyen")
        elif choice == "2":
            show_alerts_by_level("élevé+", "élevé")
        elif choice == "3":
            show_alerts_by_level("critique", "critique")
        elif choice == "4":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def show_trackers_ranked(title, devices):
    if not devices:
        clear()
        banner()
        print(color(f"\nAucun résultat pour: {title}", GREEN, bold=True))
        pause()
        return
    render_devices(devices, title)
    pause()


def show_trackers_only():
    devices = tracker_rank(run_engine_scan(prof_scan_seconds()))

    while True:
        clear()
        banner()
        print(color("\nTracker lab", CYAN, bold=True))
        print(hr())
        print("1) Tous les trackers probables")
        print("2) Haute confiance (follow >= 45)")
        print("3) Watchlist hits")
        print("4) Retour")

        choice = input("Choix > ").strip()
        if choice == "1":
            show_trackers_ranked("Trackers probables", devices)
        elif choice == "2":
            show_trackers_ranked(
                "Trackers haute confiance",
                [d for d in devices if d.get("follow_score", 0) >= 45 or d.get("watch_hit")]
            )
        elif choice == "3":
            show_trackers_ranked(
                "Trackers — watchlist hits",
                [d for d in devices if d.get("watch_hit")]
            )
        elif choice == "4":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def run_view(title, fn):
    devices = fn(run_engine_scan(prof_scan_seconds()))
    devices = sort_by_score(devices)

    if not devices:
        clear()
        banner()
        print(color(f"\nAucun résultat pour: {title}", YELLOW, bold=True))
        pause()
        return

    render_devices(devices, title)
    pause()


def smart_views_menu():
    while True:
        clear()
        banner()
        print(color(f"\nVues tactiques [{active_profile()['label']}]", CYAN, bold=True))
        print(hr())
        print("1) Critiques")
        print("2) Élevés +")
        print("3) Trackers probables")
        print("4) Watchlist hits")
        print("5) Nouveaux appareils")
        print("6) Proximité persistante")
        print("7) Apple-like")
        print("8) MAC random")
        print("9) Vendor inconnu")
        print("10) Top appareils chauds")
        print("11) Résumé des vues")
        print("12) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            run_view("Vue critique", view_critical)
        elif choice == "2":
            run_view("Vue élevés +", view_high_plus)
        elif choice == "3":
            run_view("Vue trackers", view_trackers)
        elif choice == "4":
            run_view("Vue watchlist hits", view_watch_hits)
        elif choice == "5":
            run_view("Vue nouveaux appareils", view_new_devices)
        elif choice == "6":
            run_view("Vue proximité persistante", view_nearby)
        elif choice == "7":
            run_view("Vue Apple-like", view_apple_like)
        elif choice == "8":
            run_view("Vue MAC random", view_random_mac)
        elif choice == "9":
            run_view("Vue vendor inconnu", view_unknown_vendor)
        elif choice == "10":
            run_view("Vue top appareils chauds", lambda d: view_top_hot(d, 15))
        elif choice == "11":
            devices = run_engine_scan(prof_scan_seconds())
            summary = summarize_views(devices)
            clear()
            banner()
            print(color("\nRésumé des vues", CYAN, bold=True))
            print(hr())
            for k, v in summary.items():
                print(f"{k}: {v}")
            pause()
        elif choice == "12":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def open_last():
    files = sorted(Path("reports").glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    clear()
    banner()
    if files:
        print(color(f"\nOuverture: {files[0]}", GREEN, bold=True))
        open_html_report(files[0])
    else:
        print(color("\nAucun rapport HTML trouvé.", YELLOW, bold=True))
    pause()


def show_history():
    show_history_view(load_live_history())


def show_whitelist():
    show_named_list("Whitelist", load_whitelist())


def show_watchlist():
    show_named_list("Watchlist", load_watchlist())


def _smart_add_to_named_list(target="white"):
    devices = load_last_scan()
    list_name = "whitelist" if target == "white" else "watchlist"

    clear()
    banner()
    print(color(f"\nAjout intelligent à la {list_name}", CYAN, bold=True))
    print(hr())
    print("1) Rechercher dans le dernier scan")
    print("2) Entrer une adresse / un nom manuellement")
    print("3) Retour")

    choice = input("Choix > ").strip()

    if choice == "3":
        return

    entry = None

    if choice == "1":
        if not devices:
            print(color("\nAucun dernier scan disponible.", YELLOW, bold=True))
            pause()
            return

        q = input("Recherche > ").strip()
        matches = query_devices(devices, q, 20) if q else sort_by_score(devices)[:20]
        selected = select_device_interactive(matches, "Choisis un appareil", 20)
        if selected:
            entry = {
                "address": str(selected.get("address", "")).upper(),
                "name": selected.get("name", "Inconnu"),
            }

    elif choice == "2":
        raw = input("Adresse ou nom > ").strip()
        if raw:
            if ":" in raw:
                entry = {"address": raw.upper(), "name": ""}
            else:
                entry = {"address": raw.upper(), "name": raw}

    if not entry:
        return

    if target == "white":
        data = load_whitelist()
        data.append(entry)
        save_whitelist(data)
    else:
        data = load_watchlist()
        data.append(entry)
        save_watchlist(data)

    print(color(f"\nAjouté à la {list_name}: {entry.get('address') or entry.get('name')}", GREEN, bold=True))
    pause()


def add_last_seen_to_named_list(target="white"):
    _smart_add_to_named_list(target)


def remove_from_named_list(target="white"):
    if target == "white":
        data = load_whitelist()
        title = "Supprimer de la whitelist"
        saver = save_whitelist
    else:
        data = load_watchlist()
        title = "Supprimer de la watchlist"
        saver = save_watchlist

    clear()
    banner()
    print(color(f"\n{title}", CYAN, bold=True))
    print(hr())

    if not data:
        print(color("Liste vide.", YELLOW, bold=True))
        pause()
        return

    for i, item in enumerate(data, start=1):
        print(f"{i}) {item.get('name','')} | {item.get('address','')}")
    print("0) Retour")

    raw = input("Choix > ").strip()
    try:
        idx = int(raw)
    except Exception:
        pause()
        return

    if idx == 0 or not (1 <= idx <= len(data)):
        return

    removed = data.pop(idx - 1)
    saver(data)
    print(color(f"\nSupprimé: {removed.get('address','') or removed.get('name','')}", GREEN, bold=True))
    pause()


def show_top_recurrents():
    hist = load_live_history()
    clear()
    banner()
    print(color("\nTop récurrents", CYAN, bold=True))
    print(hr())

    if not hist:
        print(color("Historique vide.", YELLOW, bold=True))
        pause()
        return

    items = sorted(
        hist.items(),
        key=lambda x: (
            x[1].get("possible_suivi", False),
            x[1].get("near_count", 0),
            x[1].get("seen_count", 0),
        ),
        reverse=True,
    )

    for addr, info in items[:20]:
        print(
            f"{info.get('name','Inconnu')} | {addr} | vus:{info.get('seen_count',0)} | "
            f"near:{info.get('near_count',0)} | alert:{info.get('last_alert_level','faible')} | "
            f"profile:{info.get('last_profile','unknown')} | "
            f"suivi?: {info.get('possible_suivi', False)}"
        )
    pause()


def search_last_scan_interactive(query_override=None):
    devices = load_last_scan()
    clear()
    banner()
    if not devices:
        print(color("\nAucun dernier scan disponible. Lance un scan complet IA d'abord.", YELLOW, bold=True))
        pause()
        return

    query = query_override or input(color("\nRecherche dernier scan > ", CYAN, bold=True)).strip()
    results = query_devices(devices, query, 20)

    if not results:
        print(color("\nAucun résultat.", YELLOW, bold=True))
        pause()
        return

    render_devices(results, f"Recherche dernier scan: {query}")
    pause()


def search_history_interactive(query_override=None):
    history = load_scan_history()
    clear()
    banner()

    if not history:
        print(color("\nHistorique vide.", YELLOW, bold=True))
        pause()
        return

    query = query_override or input(color("\nRecherche historique > ", CYAN, bold=True)).strip()
    results = query_history(history, query, 25)
    show_history_search_results(query, results)


def inspect_last_scan_device():
    devices = pick_top_devices(sort_by_score(load_last_scan()), 20)
    if not devices:
        clear()
        banner()
        print(color("\nAucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    selected = select_device_interactive(devices, "Choisis un appareil du dernier scan", 20)
    if not selected:
        return

    show_inspection_view(selected)


def show_last_two_scan_compare():
    comp = compare_last_two_scans()
    clear()
    banner()
    print(color("\nComparaison des 2 derniers scans", CYAN, bold=True))
    print(hr())

    if not comp:
        print(color("Pas assez d'historique pour comparer.", YELLOW, bold=True))
        pause()
        return

    show_comparison_summary(comp)

    if comp["added"]:
        print(color("\nTop nouveaux", BLUE, bold=True))
        for d in comp["added"][:8]:
            print(f"- {d.get('name','Inconnu')} | {d.get('address','-')} | {d.get('vendor','Unknown')}")

    if comp["removed"]:
        print(color("\nTop disparus", BLUE, bold=True))
        for d in comp["removed"][:8]:
            print(f"- {d.get('name','Inconnu')} | {d.get('address','-')} | {d.get('vendor','Unknown')}")

    pause()


def show_query_suggestions():
    devices = load_last_scan()
    if not devices:
        clear()
        banner()
        print(color("\nAucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    show_query_suggestions_list(suggest_queries(devices))


def open_investigation_menu():
    investigation_menu({
        "search_last": search_last_scan_interactive,
        "search_history": search_history_interactive,
        "inspect_last": inspect_last_scan_device,
        "compare_last_two": show_last_two_scan_compare,
        "suggest_queries": show_query_suggestions,
    })




def show_nexus_quick_summary(devices):
    result = save_enriched_incident(devices, load_scan_history())
    print()
    print(color("NEXUS quick summary", CYAN, bold=True))
    print(hr())
    for line in incident_lines(result["report"])[:8]:
        print(line)


def nexus_timeline_search():
    history = load_scan_history()
    clear()
    banner()
    print(color("\nNEXUS — Timeline appareil", CYAN, bold=True))
    print(hr())

    if not history:
        print(color("Historique vide.", YELLOW, bold=True))
        pause()
        return

    query = input("Recherche nom / adresse / vendor > ").strip()
    matches = search_device_summaries(query, history, 12)

    if not matches:
        print(color("Aucun résultat.", YELLOW, bold=True))
        pause()
        return

    for i, row in enumerate(matches, start=1):
        print(
            f"{i}) {row['name']} | {row['address']} | "
            f"occ={row['occurrences']} | persist={row['persistence_score']} | "
            f"last={row['last_seen']}"
        )
    print("0) Retour")

    raw = input("Choix > ").strip()
    if raw == "0":
        return
    if not raw.isdigit():
        return

    idx = int(raw) - 1
    if not (0 <= idx < len(matches)):
        return

    summary = matches[idx]
    timeline = timeline_for_address(summary["address"], history, 80)

    clear()
    banner()
    print(color("\nNEXUS — Timeline détaillée", CYAN, bold=True))
    print(hr())
    for line in timeline_lines(summary, timeline, 50):
        print(line)
    pause()


def nexus_persistence_view():
    rows = persistence_rankings(load_scan_history(), 20)
    clear()
    banner()
    print(color("\nNEXUS — Top persistance historique", CYAN, bold=True))
    print(hr())

    if not rows:
        print(color("Aucune donnée.", YELLOW, bold=True))
        pause()
        return

    for row in rows:
        print(
            f"- {row['name']} | {row['address']} | persist={row['persistence_score']} | "
            f"occ={row['occurrences']} | days={row['unique_days']} | "
            f"patterns={', '.join(row['patterns']) if row['patterns'] else '-'}"
        )
    pause()


def nexus_patterns_view():
    rows = recurrent_pattern_rankings(load_scan_history(), 20)
    clear()
    banner()
    print(color("\nNEXUS — Motifs récurrents", CYAN, bold=True))
    print(hr())

    if not rows:
        print(color("Aucun motif récurrent.", YELLOW, bold=True))
        pause()
        return

    for row in rows:
        print(
            f"- {row['name']} | {row['address']} | persist={row['persistence_score']} | "
            f"patterns={', '.join(row['patterns'])}"
        )
    pause()


def nexus_daily_changes():
    summary = daily_change_summary(load_scan_history())
    clear()
    banner()
    print(color("\nNEXUS — Ce qui a changé aujourd'hui", CYAN, bold=True))
    print(hr())
    for line in daily_change_lines(summary):
        print(line)
    pause()


def nexus_enriched_incident():
    devices = load_last_scan()
    if not devices:
        clear()
        banner()
        print(color("\nAucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    result = save_enriched_incident(devices, load_scan_history())
    clear()
    banner()
    print(color("\nNEXUS — Incident enrichi", CYAN, bold=True))
    print(hr())
    for line in incident_lines(result["report"]):
        print(line)
    print()
    print(f"JSON: {result['json']}")
    print(f"TXT : {result['txt']}")
    pause()


def nexus_center():
    while True:
        clear()
        banner()
        print(color("\nNEXUS Center", CYAN, bold=True))
        print(hr())
        print("1) Timeline d'un appareil")
        print("2) Top persistance historique")
        print("3) Motifs récurrents")
        print("4) Ce qui a changé aujourd'hui")
        print("5) Incident enrichi")
        print("6) Retour")

        choice = input("Choix > ").strip()
        if choice == "1":
            nexus_timeline_search()
        elif choice == "2":
            nexus_persistence_view()
        elif choice == "3":
            nexus_patterns_view()
        elif choice == "4":
            nexus_daily_changes()
        elif choice == "5":
            nexus_enriched_incident()
        elif choice == "6":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()




def show_omegax_quick_summary(devices):
    sync_current_devices(devices)
    anomalies = rank_behavior_anomalies(devices, load_scan_history(), 5)

    print()
    print(color("OMEGA-X quick summary", CYAN, bold=True))
    print(hr())

    known = top_known_devices(5)
    if known:
        print("Top base de connaissance:")
        for row in known[:3]:
            print(
                f"- {row.get('address','-')} | trust={row.get('trust_label','unknown')} | "
                f"sightings={row.get('sightings',0)} | max={row.get('max_score',0)}"
            )
    else:
        print("Base de connaissance vide.")

    print()
    print("Top anomalies comportement:")
    if anomalies:
        for row in anomalies[:3]:
            d = row["device"]
            print(
                f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
                f"anomaly={row['anomaly_score']} | "
                f"{', '.join(row['anomalies']) if row['anomalies'] else '-'}"
            )
    else:
        print("- aucune")


def omegax_known_devices_view():
    rows = top_known_devices(25)
    clear()
    banner()
    print(color("\nOMEGA-X — Base de connaissance", CYAN, bold=True))
    print(hr())

    if not rows:
        print(color("Aucune donnée.", YELLOW, bold=True))
        pause()
        return

    for row in rows:
        print(
            f"- {row.get('last_name','Inconnu')} | {row.get('address','-')} | "
            f"trust={row.get('trust_label','unknown')} | sightings={row.get('sightings',0)} | "
            f"max={row.get('max_score',0)} | note={row.get('note','') or '-'}"
        )
    pause()


def omegax_search_known_device():
    clear()
    banner()
    print(color("\nOMEGA-X — Recherche appareil connu", CYAN, bold=True))
    print(hr())

    query = input("Recherche > ").strip()
    rows = search_known_devices(query, 20)

    if not rows:
        print(color("Aucun résultat.", YELLOW, bold=True))
        pause()
        return

    for row in rows:
        print(
            f"- {row.get('last_name','Inconnu')} | {row.get('address','-')} | "
            f"trust={row.get('trust_label','unknown')} | sightings={row.get('sightings',0)} | "
            f"label={row.get('manual_label','') or '-'} | note={row.get('note','') or '-'}"
        )
    pause()


def omegax_label_device():
    devices = sort_by_score(load_last_scan())[:20]

    clear()
    banner()
    print(color("\nOMEGA-X — Étiqueter un appareil", CYAN, bold=True))
    print(hr())
    print("1) Choisir dans le dernier scan")
    print("2) Entrer une adresse manuellement")
    print("3) Retour")

    choice = input("Choix > ").strip()
    if choice == "3":
        return

    address = ""
    if choice == "1":
        if not devices:
            print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
            pause()
            return
        selected = select_device_interactive(devices, "Choisir un appareil", 20)
        if not selected:
            return
        address = str(selected.get("address", "")).upper()
    elif choice == "2":
        address = input("Adresse > ").strip().upper()

    if not address:
        return

    clear()
    banner()
    print(color("\nLabel manuel", CYAN, bold=True))
    print(hr())
    print("1) friendly")
    print("2) known")
    print("3) suspicious")
    print("4) critical")
    print("5) effacer le label")
    print("6) Retour")

    label_choice = input("Choix > ").strip()
    mapping = {
        "1": "friendly",
        "2": "known",
        "3": "suspicious",
        "4": "critical",
        "5": "",
    }
    if label_choice == "6" or label_choice not in mapping:
        return

    note = input("Note (optionnel) > ").strip()
    rec = set_manual_label(address, mapping[label_choice], note)
    clear()
    banner()
    print(color("\nLabel appliqué", CYAN, bold=True))
    print(hr())
    print(rec)
    pause()


def omegax_behavior_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nOMEGA-X — Anomalies de comportement", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    rows = rank_behavior_anomalies(devices, load_scan_history(), 20)
    for row in rows:
        d = row["device"]
        print(
            f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
            f"anomaly={row['anomaly_score']} | "
            f"{', '.join(row['anomalies']) if row['anomalies'] else '-'}"
        )
    pause()


def omegax_daily_report_view():
    report = build_daily_report(load_scan_history())
    clear()
    banner()
    print(color("\nOMEGA-X — Rapport quotidien", CYAN, bold=True))
    print(hr())
    for line in daily_report_lines(report):
        print(line)
    pause()


def omegax_daily_report_generate():
    result = save_daily_report()
    clear()
    banner()
    print(color("\nOMEGA-X — Rapport quotidien généré", CYAN, bold=True))
    print(hr())
    for line in daily_report_lines(result["report"]):
        print(line)
    print()
    print(f"JSON: {result['json']}")
    print(f"TXT : {result['txt']}")
    pause()


def omegax_center():
    while True:
        clear()
        banner()
        print(color("\nOMEGA-X Center", CYAN, bold=True))
        print(hr())
        print("1) Base de connaissance")
        print("2) Rechercher un appareil connu")
        print("3) Étiqueter un appareil")
        print("4) Anomalies de comportement")
        print("5) Rapport quotidien")
        print("6) Générer le rapport quotidien")
        print("7) Retour")

        choice = input("Choix > ").strip()
        if choice == "1":
            omegax_known_devices_view()
        elif choice == "2":
            omegax_search_known_device()
        elif choice == "3":
            omegax_label_device()
        elif choice == "4":
            omegax_behavior_view()
        elif choice == "5":
            omegax_daily_report_view()
        elif choice == "6":
            omegax_daily_report_generate()
        elif choice == "7":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()




def show_argus_quick_summary(devices):
    rows = rank_priority(devices, load_scan_history(), 5)
    print()
    print(color("ARGUS quick summary", CYAN, bold=True))
    print(hr())

    if not rows:
        print("Aucune cible prioritaire.")
        return

    for row in rows[:3]:
        d = row["device"]
        print(
            f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
            f"priority={row['priority_score']} | trust={row['trust_label']} | "
            f"persist={row['persistence'].get('persistence_score',0)}"
        )


def argus_priority_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nARGUS — Priorités", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    rows = rank_priority(devices, load_scan_history(), 20)
    for row in rows:
        d = row["device"]
        print(
            f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
            f"priority={row['priority_score']} | trust={row['trust_label']} | "
            f"reasons={', '.join(row['reasons']) if row['reasons'] else '-'}"
        )
    pause()


def argus_casefile_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nARGUS — Case file", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    rows = rank_priority(devices, load_scan_history(), 20)
    if not rows:
        print(color("Aucune cible.", YELLOW, bold=True))
        pause()
        return

    for i, row in enumerate(rows, start=1):
        d = row["device"]
        print(f"{i}) {d.get('name','Inconnu')} | {d.get('address','-')} | priority={row['priority_score']}")
    print("0) Retour")

    raw = input("Choix > ").strip()
    if raw == "0":
        return
    if not raw.isdigit():
        return

    idx = int(raw) - 1
    if not (0 <= idx < len(rows)):
        return

    case = build_case_file(rows[idx]["device"], load_scan_history())

    clear()
    banner()
    print(color("\nARGUS — Case file détaillé", CYAN, bold=True))
    print(hr())
    for line in case_file_lines(case):
        print(line)
    pause()


def argus_actions_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nARGUS — Actions recommandées", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    rows = rank_priority(devices, load_scan_history(), 10)
    actions = argus_recommended_actions(rows)
    for a in actions:
        print(f"- {a}")
    pause()


def argus_center():
    while True:
        clear()
        banner()
        print(color("\nARGUS Center", CYAN, bold=True))
        print(hr())
        print("1) Voir les priorités")
        print("2) Ouvrir un case file")
        print("3) Voir les actions recommandées")
        print("4) Retour")

        choice = input("Choix > ").strip()
        if choice == "1":
            argus_priority_view()
        elif choice == "2":
            argus_casefile_view()
        elif choice == "3":
            argus_actions_view()
        elif choice == "4":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()




def show_sentinel_quick_summary(devices):
    history = load_scan_history()
    previous_devices = history[-2].get("devices", []) if len(history) >= 2 else []
    report = build_sentinel_report(devices, previous_devices, history)

    print()
    print(color("SENTINEL quick summary", CYAN, bold=True))
    print(hr())
    for line in sentinel_lines(report)[:10]:
        print(line)


def sentinel_dashboard():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nSENTINEL — Dashboard", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    history = load_scan_history()
    previous_devices = history[-2].get("devices", []) if len(history) >= 2 else []
    report = build_sentinel_report(devices, previous_devices, history)

    for line in sentinel_lines(report):
        print(line)
    pause()


def sentinel_campaigns_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nSENTINEL — Campaign view", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    history = load_scan_history()
    previous_devices = history[-2].get("devices", []) if len(history) >= 2 else []
    report = build_sentinel_report(devices, previous_devices, history)

    campaigns = report.get("campaigns", [])
    if not campaigns:
        print(color("Aucune campagne détectée.", GREEN, bold=True))
        pause()
        return

    for camp in campaigns:
        print(
            f"- {camp['vendor']} | {camp['profile']} | devices={len(camp['devices'])} | "
            f"watch_hits={camp['watch_hits']} | trackers={camp['trackers']} | "
            f"max_priority={camp['max_priority']}"
        )
        for d in camp["devices"][:5]:
            print(
                f"   • {d['name']} | {d['address']} | priority={d['priority_score']} | "
                f"trust={d['trust_label']} | alert={d['alert_level']}"
            )
    pause()


def sentinel_escalations_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nSENTINEL — Escalades", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    history = load_scan_history()
    previous_devices = history[-2].get("devices", []) if len(history) >= 2 else []
    report = build_sentinel_report(devices, previous_devices, history)

    escalations = report.get("escalations", [])
    if not escalations:
        print(color("Aucune escalade détectée.", GREEN, bold=True))
        pause()
        return

    for row in escalations:
        d = row["current"]["device"]
        print(
            f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
            f"delta={row['delta']} | reasons={', '.join(row['reasons'])}"
        )
    pause()


def sentinel_watch_session_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nSENTINEL — Sauvegarder watch session", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    history = load_scan_history()
    previous_devices = history[-2].get("devices", []) if len(history) >= 2 else []
    report = build_sentinel_report(devices, previous_devices, history)
    result = save_watch_session(report)

    for line in sentinel_lines(report):
        print(line)
    print()
    print(f"JSON: {result['json']}")
    print(f"TXT : {result['txt']}")
    pause()


def sentinel_center():
    while True:
        clear()
        banner()
        print(color("\nSENTINEL Center", CYAN, bold=True))
        print(hr())
        print("1) Dashboard de menace")
        print("2) Campaign view")
        print("3) Escalades")
        print("4) Sauvegarder une watch session")
        print("5) Retour")

        choice = input("Choix > ").strip()
        if choice == "1":
            sentinel_dashboard()
        elif choice == "2":
            sentinel_campaigns_view()
        elif choice == "3":
            sentinel_escalations_view()
        elif choice == "4":
            sentinel_watch_session_view()
        elif choice == "5":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()




def show_atlas_quick_summary(devices):
    snap = atlas_snapshot(devices, load_scan_history())
    print()
    print(color("ATLAS quick summary", CYAN, bold=True))
    print(hr())

    edges = snap.get("hot_edges", [])
    clusters = snap.get("clusters", [])
    groups = snap.get("risk_groups", [])

    print(f"Hot edges   : {len(edges)}")
    print(f"Clusters    : {len(clusters)}")
    print(f"Risk groups : {len(groups)}")

    if edges:
        e = edges[0]
        print(f"Top edge    : {e['a_name']} <-> {e['b_name']} | co-présence={e['weight']}")


def atlas_hot_edges_view():
    rows = hot_edges(load_scan_history(), 20, 2)
    clear()
    banner()
    print(color("\nATLAS — Hot edges", CYAN, bold=True))
    print(hr())

    if not rows:
        print(color("Aucune co-présence forte.", YELLOW, bold=True))
        pause()
        return

    for row in rows:
        print(
            f"- {row['a_name']} | {row['a']}  <->  {row['b_name']} | {row['b']} | "
            f"co-présence={row['weight']}"
        )
    pause()


def atlas_neighbors_view():
    history = load_scan_history()
    clear()
    banner()
    print(color("\nATLAS — Voisins d'un appareil", CYAN, bold=True))
    print(hr())

    if not history:
        print(color("Historique vide.", YELLOW, bold=True))
        pause()
        return

    query = input("Recherche nom / adresse / vendor > ").strip()
    matches = search_device_summaries(query, history, 12)

    if not matches:
        print(color("Aucun résultat.", YELLOW, bold=True))
        pause()
        return

    for i, row in enumerate(matches, start=1):
        print(f"{i}) {row['name']} | {row['address']} | persist={row['persistence_score']}")
    print("0) Retour")

    raw = input("Choix > ").strip()
    if raw == "0":
        return
    if not raw.isdigit():
        return

    idx = int(raw) - 1
    if not (0 <= idx < len(matches)):
        return

    selected = matches[idx]
    neigh = neighbors_for_address(selected["address"], history, 20, 1)

    clear()
    banner()
    print(color("\nATLAS — Voisins historiques", CYAN, bold=True))
    print(hr())
    print(f"Cible: {selected['name']} | {selected['address']}")
    print()

    if not neigh:
        print(color("Aucun voisin significatif.", YELLOW, bold=True))
        pause()
        return

    for row in neigh:
        print(f"- {row['name']} | {row['address']} | co-présence={row['weight']}")
    pause()


def atlas_clusters_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nATLAS — Clusters vendor/profile", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    rows = vendor_profile_clusters(devices, load_scan_history(), 15)
    if not rows:
        print(color("Aucun cluster notable.", YELLOW, bold=True))
        pause()
        return

    for row in rows:
        print(
            f"- {row['vendor']} | {row['profile']} | count={row['count']} | "
            f"max_priority={row['max_priority']} | avg={row['avg_priority']} | "
            f"watch_hits={row['watch_hits']} | high={row['critical_like']}"
        )
    pause()


def atlas_risk_groups_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nATLAS — Groupes de risque", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    groups = risk_groups(devices, load_scan_history(), 12)
    if not groups:
        print(color("Aucun groupe de risque.", GREEN, bold=True))
        pause()
        return

    for grp in groups:
        print(f"- {grp['key']} | count={grp['count']} | top_priority={grp['top_priority']}")
        for row in grp["rows"][:4]:
            d = row["device"]
            print(
                f"   • {d.get('name','Inconnu')} | {d.get('address','-')} | "
                f"priority={row['priority_score']} | trust={row['trust_label']}"
            )
    pause()


def atlas_center():
    while True:
        clear()
        banner()
        print(color("\nATLAS Center", CYAN, bold=True))
        print(hr())
        print("1) Hot edges")
        print("2) Voisins d'un appareil")
        print("3) Clusters vendor/profile")
        print("4) Groupes de risque")
        print("5) Retour")

        choice = input("Choix > ").strip()
        if choice == "1":
            atlas_hot_edges_view()
        elif choice == "2":
            atlas_neighbors_view()
        elif choice == "3":
            atlas_clusters_view()
        elif choice == "4":
            atlas_risk_groups_view()
        elif choice == "5":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()




def show_helios_quick_summary(devices):
    report = build_helios_report(devices, load_scan_history())
    print()
    print(color("HELIOS quick summary", CYAN, bold=True))
    print(hr())
    for line in helios_lines(report)[:10]:
        print(line)


def helios_dashboard():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nHELIOS — Executive dashboard", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    report = build_helios_report(devices, load_scan_history())
    for line in helios_lines(report):
        print(line)
    pause()


def helios_targets_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nHELIOS — Top cibles immédiates", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    report = build_helios_report(devices, load_scan_history())
    targets = report.get("immediate_targets", [])
    if not targets:
        print(color("Aucune cible immédiate.", GREEN, bold=True))
        pause()
        return

    for t in targets:
        print(
            f"- {t['name']} | {t['address']} | priority={t['priority_score']} | "
            f"trust={t['trust_label']} | alert={t['alert_level']} | "
            f"reasons={', '.join(t['reasons']) if t['reasons'] else '-'}"
        )
    pause()


def helios_recommendations_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nHELIOS — Recommandations fusionnées", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    report = build_helios_report(devices, load_scan_history())
    recs = report.get("recommendations", [])
    if not recs:
        print(color("Aucune recommandation.", GREEN, bold=True))
        pause()
        return

    for r in recs:
        print(f"- {r}")
    pause()


def helios_center():
    while True:
        clear()
        banner()
        print(color("\nHELIOS Center", CYAN, bold=True))
        print(hr())
        print("1) Executive dashboard")
        print("2) Top cibles immédiates")
        print("3) Recommandations fusionnées")
        print("4) Retour")

        choice = input("Choix > ").strip()
        if choice == "1":
            helios_dashboard()
        elif choice == "2":
            helios_targets_view()
        elif choice == "3":
            helios_recommendations_view()
        elif choice == "4":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()




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




def show_nebula_quick_summary(devices):
    report = build_nebula_report(devices, load_scan_history())
    print()
    print(color("NEBULA quick summary", CYAN, bold=True))
    print(hr())
    for line in nebula_lines(report)[:10]:
        print(line)


def nebula_dashboard():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nNEBULA — Master dashboard", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    report = build_nebula_report(devices, load_scan_history())
    for line in nebula_lines(report):
        print(line)
    pause()


def nebula_session_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nNEBULA — Résumé de session", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    summary = build_session_summary(devices, load_scan_history())
    for line in session_summary_lines(summary):
        print(line)
    pause()


def nebula_save_session_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nNEBULA — Sauvegarder résumé de session", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    result = save_session_summary(build_session_summary(devices, load_scan_history()))
    for line in session_summary_lines(result["summary"]):
        print(line)
    print()
    print(f"JSON: {result['json']}")
    print(f"TXT : {result['txt']}")
    pause()


def nebula_cases_view():
    rows = list_cases(30)
    clear()
    banner()
    print(color("\nNEBULA — Dossiers d'enquête", CYAN, bold=True))
    print(hr())

    if not rows:
        print(color("Aucun dossier.", YELLOW, bold=True))
        pause()
        return

    for row in rows:
        print(
            f"- {row.get('name','Inconnu')} | {row.get('address','-')} | "
            f"status={row.get('status','open')} | alert={row.get('alert_level','faible')} | "
            f"score={row.get('final_score',0)} | updated={row.get('updated_at','-')}"
        )
    pause()


def nebula_create_case_view():
    devices = sort_by_score(load_last_scan())[:20]
    clear()
    banner()
    print(color("\nNEBULA — Ouvrir / mettre à jour un dossier", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    selected = select_device_interactive(devices, "Choisir un appareil", 20)
    if not selected:
        return

    case = upsert_case_from_device(selected, load_scan_history())
    clear()
    banner()
    print(color("\nDossier mis à jour", CYAN, bold=True))
    print(hr())
    print(case)
    pause()


def nebula_add_note_view():
    rows = list_cases(30)
    clear()
    banner()
    print(color("\nNEBULA — Ajouter une note", CYAN, bold=True))
    print(hr())

    if not rows:
        print(color("Aucun dossier.", YELLOW, bold=True))
        pause()
        return

    for i, row in enumerate(rows, start=1):
        print(f"{i}) {row.get('name','Inconnu')} | {row.get('address','-')} | status={row.get('status','open')}")
    print("0) Retour")

    raw = input("Choix > ").strip()
    if raw == "0":
        return
    if not raw.isdigit():
        return

    idx = int(raw) - 1
    if not (0 <= idx < len(rows)):
        return

    note = input("Note > ").strip()
    if not note:
        return

    row = append_case_note(rows[idx]["address"], note)
    clear()
    banner()
    print(color("\nNote ajoutée", CYAN, bold=True))
    print(hr())
    print(row)
    pause()


def nebula_close_case_view():
    rows = [r for r in list_cases(30) if r.get("status","open") == "open"]
    clear()
    banner()
    print(color("\nNEBULA — Fermer un dossier", CYAN, bold=True))
    print(hr())

    if not rows:
        print(color("Aucun dossier ouvert.", YELLOW, bold=True))
        pause()
        return

    for i, row in enumerate(rows, start=1):
        print(f"{i}) {row.get('name','Inconnu')} | {row.get('address','-')}")
    print("0) Retour")

    raw = input("Choix > ").strip()
    if raw == "0":
        return
    if not raw.isdigit():
        return

    idx = int(raw) - 1
    if not (0 <= idx < len(rows)):
        return

    row = close_case(rows[idx]["address"])
    clear()
    banner()
    print(color("\nDossier fermé", CYAN, bold=True))
    print(hr())
    print(row)
    pause()


def nebula_center():
    while True:
        clear()
        banner()
        print(color("\nNEBULA Center", CYAN, bold=True))
        print(hr())
        print("1) Master dashboard")
        print("2) Résumé de session")
        print("3) Sauvegarder résumé de session")
        print("4) Voir les dossiers")
        print("5) Ouvrir / mettre à jour un dossier")
        print("6) Ajouter une note")
        print("7) Fermer un dossier")
        print("8) Retour")

        choice = input("Choix > ").strip()
        if choice == "1":
            nebula_dashboard()
        elif choice == "2":
            nebula_session_view()
        elif choice == "3":
            nebula_save_session_view()
        elif choice == "4":
            nebula_cases_view()
        elif choice == "5":
            nebula_create_case_view()
        elif choice == "6":
            nebula_add_note_view()
        elif choice == "7":
            nebula_close_case_view()
        elif choice == "8":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()




def show_citadel_quick_summary():
    report = build_citadel_report()
    print()
    print(color("CITADEL quick summary", CYAN, bold=True))
    print(hr())
    for line in citadel_lines(report)[:8]:
        print(line)


def citadel_dashboard():
    report = build_citadel_report()
    clear()
    banner()
    print(color("\nCITADEL — Check-up global", CYAN, bold=True))
    print(hr())
    for line in citadel_lines(report):
        print(line)
    pause()


def citadel_save_report_view():
    result = save_citadel_report()
    clear()
    banner()
    print(color("\nCITADEL — Rapport sauvegardé", CYAN, bold=True))
    print(hr())
    for line in citadel_lines(result["report"]):
        print(line)
    print()
    print(f"JSON: {result['json']}")
    print(f"TXT : {result['txt']}")
    pause()


def citadel_export_global_view():
    result = export_global_bundle(include_snapshots=True)
    clear()
    banner()
    print(color("\nCITADEL — Export global", CYAN, bold=True))
    print(hr())
    print(f"ZIP  : {result['zip']}")
    print(f"Files: {result['files']}")
    pause()


def citadel_incident_pack_view():
    result = export_incident_pack()
    clear()
    banner()
    print(color("\nCITADEL — Incident pack", CYAN, bold=True))
    print(hr())
    print(f"ZIP  : {result['zip']}")
    print(f"Files: {result['files']}")
    pause()


def citadel_maintenance_view():
    result = run_maintenance_cycle()
    clear()
    banner()
    print(color("\nCITADEL — Maintenance cycle", CYAN, bold=True))
    print(hr())
    print(f"Réparé JSON : {result['repaired'] if result['repaired'] else 'aucune réparation'}")
    print(f"Snapshot    : {result['snapshot']['path']}")
    print(f"Report JSON : {result['saved_report']['json']}")
    print(f"Report TXT  : {result['saved_report']['txt']}")
    print()
    for line in citadel_lines(result["report"]):
        print(line)
    pause()


def citadel_center():
    while True:
        clear()
        banner()
        print(color("\nCITADEL Center", CYAN, bold=True))
        print(hr())
        print("1) Check-up global")
        print("2) Sauvegarder rapport CITADEL")
        print("3) Export global du projet")
        print("4) Incident pack")
        print("5) Maintenance intégrée")
        print("6) Retour")

        choice = input("Choix > ").strip()
        if choice == "1":
            citadel_dashboard()
        elif choice == "2":
            citadel_save_report_view()
        elif choice == "3":
            citadel_export_global_view()
        elif choice == "4":
            citadel_incident_pack_view()
        elif choice == "5":
            citadel_maintenance_view()
        elif choice == "6":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()




def show_commander_quick_summary(devices):
    brief = build_commander_brief(devices, load_scan_history())
    print()
    print(color("COMMANDER quick summary", CYAN, bold=True))
    print(hr())
    for line in commander_brief_lines(brief)[:8]:
        print(line)


def commander_startup_view():
    status = build_startup_status()
    clear()
    banner()
    print(color("\nCOMMANDER — Startup check", CYAN, bold=True))
    print(hr())
    for line in startup_lines(status):
        print(line)
    pause()


def commander_brief_view():
    devices = load_last_scan()
    clear()
    banner()
    print(color("\nCOMMANDER — Brief opérateur", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    brief = build_commander_brief(devices, load_scan_history())
    for line in commander_brief_lines(brief):
        print(line)
    pause()


def commander_workflows_view():
    clear()
    banner()
    print(color("\nCOMMANDER — Workflows", CYAN, bold=True))
    print(hr())
    for line in workflow_lines():
        print(line)
    pause()


def commander_manual_view():
    clear()
    banner()
    print(color("\nCOMMANDER — Manuel local", CYAN, bold=True))
    print(hr())

    if not MANUAL_FILE.exists():
        print(color("MANUAL_OMEGA.md manquant.", YELLOW, bold=True))
        pause()
        return

    print(MANUAL_FILE.read_text(encoding="utf-8"))
    pause()


def commander_simple_mode():
    while True:
        clear()
        banner()
        print(color("\nCOMMANDER — Mode simple", CYAN, bold=True))
        print(hr())
        print("1) Scan + briefing")
        print("2) Audit rapide")
        print("3) Réponse tracker")
        print("4) Réponse watch hit")
        print("5) Maintenance")
        print("6) Retour")

        choice = input("Choix > ").strip()
        if choice == "1":
            do_scan_mode("normal")
        elif choice == "2":
            do_scan_mode("normal")
            export_audit_from_last_scan()
        elif choice == "3":
            do_scan_mode("deep")
            show_trackers_only()
        elif choice == "4":
            show_watchlist()
            sentinel_watch_session_view()
        elif choice == "5":
            citadel_maintenance_view()
        elif choice == "6":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def commander_center():
    while True:
        clear()
        banner()
        print(color("\nCOMMANDER Center", CYAN, bold=True))
        print(hr())
        print("1) Startup check")
        print("2) Brief opérateur")
        print("3) Mode simple")
        print("4) Workflows")
        print("5) Manuel local")
        print("6) Retour")

        choice = input("Choix > ").strip()
        if choice == "1":
            commander_startup_view()
        elif choice == "2":
            commander_brief_view()
        elif choice == "3":
            commander_simple_mode()
        elif choice == "4":
            commander_workflows_view()
        elif choice == "5":
            commander_manual_view()
        elif choice == "6":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()




def _batch34_sev(alert):
    return {"faible": 0, "moyen": 1, "élevé": 2, "critique": 3}.get(str(alert or "faible"), 0)


def _batch34_label_device(d):
    return (
        f"{d.get('name','Inconnu')} | {d.get('address','-')} | "
        f"score={d.get('final_score', d.get('score', 0))} | "
        f"alert={d.get('alert_level','faible')} | rssi={d.get('rssi', -100)}"
    )


def _batch34_show_devices(title, devices, limit=20):
    clear()
    banner()
    print(color(f"\n{title}", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucune donnée.", YELLOW, bold=True))
        pause()
        return

    for d in devices[:limit]:
        flags = []
        if d.get("watch_hit"):
            flags.append("watch")
        if d.get("possible_suivi"):
            flags.append("suivi")
        if d.get("persistent_nearby"):
            flags.append("persist")
        if d.get("profile") == "tracker_probable":
            flags.append("tracker")

        extra = f" | flags={','.join(flags)}" if flags else ""
        print(_batch34_label_device(d) + extra)
    pause()


def _batch34_pick(items, label_fn, title):
    clear()
    banner()
    print(color(f"\n{title}", CYAN, bold=True))
    print(hr())

    if not items:
        print(color("Aucune donnée.", YELLOW, bold=True))
        pause()
        return None

    for i, item in enumerate(items[:20], start=1):
        print(f"{i}) {label_fn(item)}")
    print("0) Retour")

    raw = input("Choix > ").strip()
    if raw == "0":
        return None
    if not raw.isdigit():
        return None
    idx = int(raw) - 1
    if not (0 <= idx < min(len(items), 20)):
        return None
    return items[idx]


def _batch34_commander_after_scan():
    devices = load_last_scan()
    if not devices:
        return
    clear()
    banner()
    print(color("\nScan Hub — Brief final", CYAN, bold=True))
    print(hr())
    brief = build_commander_brief(devices, load_scan_history())
    for line in commander_brief_lines(brief):
        print(line)
    pause()


def batch34_scan_hub():
    while True:
        clear()
        banner()
        print(color("\n1) Scan Hub", CYAN, bold=True))
        print(hr())
        print("1) Scan normal enrichi")
        print("2) Scan profond")
        print("3) Scan adaptatif auto")
        print("4) Scan terrain + audit")
        print("5) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            do_scan_mode("normal")
            _batch34_commander_after_scan()
        elif choice == "2":
            do_scan_mode("deep")
            _batch34_commander_after_scan()
        elif choice == "3":
            devices = load_last_scan()
            history = load_scan_history()
            mode = "normal"
            if devices:
                try:
                    brief = build_commander_brief(devices, history)
                    if int(brief.get("top_priority", 0)) >= 60 or int(brief.get("watch_hits", 0)) >= 1:
                        mode = "deep"
                except Exception:
                    mode = "normal"
            do_scan_mode(mode)
            _batch34_commander_after_scan()
        elif choice == "4":
            do_scan_mode("deep")
            export_audit_from_last_scan()
            _batch34_commander_after_scan()
        elif choice == "5":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch34_alert_center():
    while True:
        devices = load_last_scan()
        history = load_scan_history()
        previous_devices = history[-2].get("devices", []) if len(history) >= 2 else []
        sentinel = build_sentinel_report(devices, previous_devices, history) if devices else {"escalations": []}

        clear()
        banner()
        print(color("\n2) Alert Center", CYAN, bold=True))
        print(hr())

        if not devices:
            print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
            pause()
            return

        critical = [d for d in devices if d.get("alert_level") == "critique"]
        high = [d for d in devices if d.get("alert_level") == "élevé"]
        medium = [d for d in devices if d.get("alert_level") == "moyen"]
        rising = sentinel.get("escalations", [])

        print(f"Critiques : {len(critical)}")
        print(f"Élevées   : {len(high)}")
        print(f"Moyennes  : {len(medium)}")
        print(f"Montantes : {len(rising)}")
        print()
        print("1) Voir critiques")
        print("2) Voir élevées")
        print("3) Voir moyennes")
        print("4) Voir nouvelles / montantes")
        print("5) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            _batch34_show_devices("Alertes critiques", critical)
        elif choice == "2":
            _batch34_show_devices("Alertes élevées", high)
        elif choice == "3":
            _batch34_show_devices("Alertes moyennes", medium)
        elif choice == "4":
            clear()
            banner()
            print(color("\nAlertes nouvelles / montantes", CYAN, bold=True))
            print(hr())
            if not rising:
                print(color("Aucune alerte montante.", GREEN, bold=True))
            else:
                for row in rising[:20]:
                    d = row["current"]["device"]
                    print(
                        f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
                        f"delta={row['delta']} | reasons={', '.join(row['reasons'])}"
                    )
            pause()
        elif choice == "5":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch34_tracker_hunt():
    while True:
        devices = load_last_scan()
        history = load_scan_history()

        clear()
        banner()
        print(color("\n3) Tracker Hunt+", CYAN, bold=True))
        print(hr())

        if not devices:
            print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
            pause()
            return

        tracker_rows = []
        anomalies = {str(r["device"].get("address","-")).upper(): r for r in rank_behavior_anomalies(devices, history, 50)}
        for row in rank_priority(devices, history, 50):
            d = row["device"]
            if (
                d.get("profile") == "tracker_probable"
                or d.get("possible_suivi")
                or d.get("watch_hit")
                or d.get("persistent_nearby")
            ):
                tracker_rows.append((row, anomalies.get(str(d.get("address","-")).upper())))

        print(f"Trackers / signaux: {len(tracker_rows)}")
        print()
        print("1) Voir ranking tracker")
        print("2) Voir anomalies tracker")
        print("3) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            clear()
            banner()
            print(color("\nRanking tracker", CYAN, bold=True))
            print(hr())
            if not tracker_rows:
                print(color("Aucun tracker probable.", GREEN, bold=True))
            else:
                for row, anom in tracker_rows[:20]:
                    d = row["device"]
                    print(
                        f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
                        f"priority={row['priority_score']} | trust={row['trust_label']} | "
                        f"reasons={', '.join(row['reasons']) if row['reasons'] else '-'}"
                    )
            pause()
        elif choice == "2":
            clear()
            banner()
            print(color("\nAnomalies tracker", CYAN, bold=True))
            print(hr())
            if not tracker_rows:
                print(color("Aucun tracker probable.", GREEN, bold=True))
            else:
                for row, anom in tracker_rows[:20]:
                    d = row["device"]
                    anomaly_score = anom["anomaly_score"] if anom else 0
                    anomaly_text = ", ".join(anom["anomalies"]) if anom and anom["anomalies"] else "-"
                    print(
                        f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
                        f"anomaly={anomaly_score} | {anomaly_text}"
                    )
            pause()
        elif choice == "3":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch34_investigation_hub():
    while True:
        history = load_scan_history()
        devices = load_last_scan()

        clear()
        banner()
        print(color("\n4) Investigation Hub", CYAN, bold=True))
        print(hr())

        print("1) Rechercher un appareil dans l'historique")
        print("2) Ouvrir un case file depuis le dernier scan")
        print("3) Voir les voisins ATLAS d'un appareil")
        print("4) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            query = input("Recherche nom / adresse / vendor > ").strip()
            rows = search_device_summaries(query, history, 20)
            picked = _batch34_pick(
                rows,
                lambda r: f"{r['name']} | {r['address']} | persist={r['persistence_score']} | occ={r['occurrences']}",
                "Résultats historique"
            )
            if picked:
                tl = timeline_for_address(picked["address"], history, 80)
                clear()
                banner()
                print(color("\nTimeline détaillée", CYAN, bold=True))
                print(hr())
                for line in timeline_lines(picked, tl, 50):
                    print(line)
                pause()

        elif choice == "2":
            if not devices:
                print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
                pause()
                continue
            rows = rank_priority(devices, history, 20)
            picked = _batch34_pick(
                rows,
                lambda r: f"{r['device'].get('name','Inconnu')} | {r['device'].get('address','-')} | priority={r['priority_score']}",
                "Case files disponibles"
            )
            if picked:
                case = build_case_file(picked["device"], history)
                clear()
                banner()
                print(color("\nCase file détaillé", CYAN, bold=True))
                print(hr())
                for line in case_file_lines(case):
                    print(line)
                pause()

        elif choice == "3":
            query = input("Recherche cible > ").strip()
            rows = search_device_summaries(query, history, 20)
            picked = _batch34_pick(
                rows,
                lambda r: f"{r['name']} | {r['address']} | persist={r['persistence_score']}",
                "Choisir une cible"
            )
            if picked:
                neigh = neighbors_for_address(picked["address"], history, 20, 1)
                clear()
                banner()
                print(color("\nVoisins ATLAS", CYAN, bold=True))
                print(hr())
                print(f"Cible: {picked['name']} | {picked['address']}")
                print()
                if not neigh:
                    print(color("Aucun voisin significatif.", YELLOW, bold=True))
                else:
                    for row in neigh:
                        print(f"- {row['name']} | {row['address']} | co-présence={row['weight']}")
                pause()

        elif choice == "4":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch34_smart_views():
    while True:
        devices = load_last_scan()
        history = load_scan_history()

        clear()
        banner()
        print(color("\n5) Smart Views Pro", CYAN, bold=True))
        print(hr())

        if not devices:
            print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
            pause()
            return

        ranked = rank_priority(devices, history, 50)

        new_devices = [d for d in devices if d.get("is_new_device")]
        near_devices = [d for d in devices if int(d.get("rssi", -200)) >= -70]
        persistent_devices = [d for d in devices if d.get("persistent_nearby") or int(d.get("seen_count", 0)) >= 2]
        suspicious_devices = [
            r["device"] for r in ranked
            if r["priority_score"] >= 60
            or r["device"].get("watch_hit")
            or r["device"].get("possible_suivi")
            or _batch34_sev(r["device"].get("alert_level")) >= 2
        ]
        known_devices = [d for d in devices if str(d.get("name","Inconnu")) != "Inconnu"]
        quiet_noise = [d for d in devices if int(d.get("final_score", d.get("score", 0))) <= 15]

        print("1) Nouveaux appareils")
        print("2) Appareils proches")
        print("3) Appareils persistants")
        print("4) Appareils suspects")
        print("5) Appareils connus")
        print("6) Bruit faible")
        print("7) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            _batch34_show_devices("Vue — Nouveaux appareils", new_devices)
        elif choice == "2":
            _batch34_show_devices("Vue — Appareils proches", near_devices)
        elif choice == "3":
            _batch34_show_devices("Vue — Appareils persistants", persistent_devices)
        elif choice == "4":
            _batch34_show_devices("Vue — Appareils suspects", suspicious_devices)
        elif choice == "5":
            _batch34_show_devices("Vue — Appareils connus", known_devices)
        elif choice == "6":
            _batch34_show_devices("Vue — Bruit faible", quiet_noise)
        elif choice == "7":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()



def batch35_command_center_pro():
    while True:
        clear()
        banner()
        print(color("\n6) Command Center Pro", CYAN, bold=True))
        print(hr())
        print("1) Startup check COMMANDER")
        print("2) Brief opérateur COMMANDER")
        print("3) Scan + briefing")
        print("4) Alert Center")
        print("5) Tracker Hunt+")
        print("6) Incident pack CITADEL")
        print("7) Maintenance CITADEL")
        print("8) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            commander_startup_view()
        elif choice == "2":
            commander_brief_view()
        elif choice == "3":
            do_scan_mode("normal")
            _batch34_commander_after_scan()
        elif choice == "4":
            batch34_alert_center()
        elif choice == "5":
            batch34_tracker_hunt()
        elif choice == "6":
            citadel_incident_pack_view()
        elif choice == "7":
            citadel_maintenance_view()
        elif choice == "8":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch35_query_vault():
    while True:
        clear()
        banner()
        print(color("\n7) Query Vault+", CYAN, bold=True))
        print(hr())
        print("1) Voir les requêtes sauvegardées")
        print("2) Rechercher dans l'historique")
        print("3) Rechercher dans la base de connaissance")
        print("4) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            saved_queries_menu()

        elif choice == "2":
            history = load_scan_history()
            query = input("Recherche historique > ").strip()
            rows = search_device_summaries(query, history, 20)

            clear()
            banner()
            print(color("\nRésultats historique", CYAN, bold=True))
            print(hr())

            if not rows:
                print(color("Aucun résultat.", YELLOW, bold=True))
            else:
                for row in rows:
                    print(
                        f"- {row['name']} | {row['address']} | "
                        f"persist={row['persistence_score']} | occ={row['occurrences']} | "
                        f"patterns={', '.join(row['patterns']) if row['patterns'] else '-'}"
                    )
            pause()

        elif choice == "3":
            from ble_radar.knowledge import search_known_devices

            query = input("Recherche base de connaissance > ").strip()
            rows = search_known_devices(query, 20)

            clear()
            banner()
            print(color("\nRésultats base de connaissance", CYAN, bold=True))
            print(hr())

            if not rows:
                print(color("Aucun résultat.", YELLOW, bold=True))
            else:
                for row in rows:
                    print(
                        f"- {row.get('last_name','Inconnu')} | {row.get('address','-')} | "
                        f"trust={row.get('trust_label','unknown')} | "
                        f"sightings={row.get('sightings',0)} | "
                        f"note={row.get('note','') or '-'}"
                    )
            pause()

        elif choice == "4":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch35_audit_export_pro():
    while True:
        clear()
        banner()
        print(color("\n8) Audit Export Pro", CYAN, bold=True))
        print(hr())
        print("1) Audit terrain depuis le dernier scan")
        print("2) Rapport CITADEL")
        print("3) Incident pack")
        print("4) Export global du projet")
        print("5) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            export_audit_from_last_scan()
        elif choice == "2":
            citadel_save_report_view()
        elif choice == "3":
            citadel_incident_pack_view()
        elif choice == "4":
            citadel_export_global_view()
        elif choice == "5":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch35_metrics_anomalies_pro():
    from ble_radar.ops import radio_health

    devices = load_last_scan()
    history = load_scan_history()

    clear()
    banner()
    print(color("\n9) Metrics & Anomalies Pro", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    previous_devices = history[-2].get("devices", []) if len(history) >= 2 else []
    sentinel = build_sentinel_report(devices, previous_devices, history)
    anomalies = rank_behavior_anomalies(devices, history, 15)
    health = radio_health(devices)

    print(f"Santé radio        : {health.get('score', 0)} ({health.get('label', '-')})")
    print(f"Devices            : {len(devices)}")
    print(f"Threat state       : {sentinel.get('threat_state', 'bruit_normal')}")
    print(f"Critiques          : {sentinel.get('critical_count', 0)}")
    print(f"Élevés             : {sentinel.get('high_count', 0)}")
    print(f"Trackers           : {sentinel.get('tracker_count', 0)}")
    print(f"Watch hits         : {sentinel.get('watch_hits', 0)}")
    print(f"Escalades          : {len(sentinel.get('escalations', []))}")
    print(f"Campaigns          : {len(sentinel.get('campaigns', []))}")
    print()

    print("Top anomalies comportementales:")
    if anomalies:
        for row in anomalies[:10]:
            d = row["device"]
            print(
                f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
                f"anomaly={row['anomaly_score']} | "
                f"{', '.join(row['anomalies']) if row['anomalies'] else '-'}"
            )
    else:
        print("- aucune")

    pause()


def batch35_replay_lab_pro():
    from ble_radar.ops import compare_scan_sets, changed_alerts

    history = load_scan_history()

    clear()
    banner()
    print(color("\n10) Replay Lab Pro", CYAN, bold=True))
    print(hr())

    if len(history) < 2:
        print(color("Pas assez d'historique pour comparer.", YELLOW, bold=True))
        pause()
        return

    last = history[-1]
    prev = history[-2]

    last_devices = last.get("devices", [])
    prev_devices = prev.get("devices", [])

    comparison = compare_scan_sets(prev_devices, last_devices)
    changes = changed_alerts(prev_devices, last_devices)

    print(f"Scan précédent : {prev.get('stamp', prev.get('timestamp', '-'))}")
    print(f"Dernier scan   : {last.get('stamp', last.get('timestamp', '-'))}")
    print()
    print(f"Ajoutés        : {len(comparison.get('added', []))}")
    print(f"Retirés        : {len(comparison.get('removed', []))}")
    print(f"Communs        : {len(comparison.get('common', []))}")
    print(f"Alertes changées: {len(changes) if changes else 0}")
    print()

    print("Historique récent:")
    for scan in history[-8:]:
        stamp = scan.get('stamp', scan.get('timestamp', '-'))
        count = scan.get('count', len(scan.get('devices', [])))
        crit = scan.get('critical', 0)
        high = scan.get('high', 0)
        med = scan.get('medium', 0)
        print(f"- {stamp} | count={count} | crit={crit} | high={high} | med={med}")

    print()
    print("Ajoutés (top 10):")
    for row in comparison.get("added", [])[:10]:
        print(f"- {row.get('name','Inconnu')} | {row.get('address','-')}")

    print()
    print("Retirés (top 10):")
    for row in comparison.get("removed", [])[:10]:
        print(f"- {row.get('name','Inconnu')} | {row.get('address','-')}")

    print()
    print("Alertes changées (top 10):")
    if changes:
        for row in changes[:10]:
            print(str(row))
    else:
        print("- aucune")

    pause()



def batch36_operator_profiles_pro():
    while True:
        clear()
        banner()
        prof = active_profile()
        print(color("\n11) Operator Profiles Pro", CYAN, bold=True))
        print(hr())
        print(f"Profil actif : {prof.get('label', '-')}")
        print(f"Key          : {prof.get('key', '-')}")
        if prof.get("description"):
            print(f"Description  : {prof.get('description')}")
        print()
        print("1) Voir le profil actif")
        print("2) Changer de profil")
        print("3) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            clear()
            banner()
            print(color("\nProfil actif", CYAN, bold=True))
            print(hr())
            for k, v in prof.items():
                print(f"{k}: {v}")
            pause()
        elif choice == "2":
            profiles_menu()
        elif choice == "3":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch36_mission_modes_pro():
    while True:
        clear()
        banner()
        mission = active_mission()
        print(color("\n12) Mission Modes Pro", CYAN, bold=True))
        print(hr())
        print(f"Mission active : {mission.get('label', '-')}")
        print(f"Key            : {mission.get('key', '-')}")
        if mission.get("focus"):
            print(f"Focus          : {mission.get('focus')}")
        if mission.get("description"):
            print(f"Description    : {mission.get('description')}")
        print()
        print("1) Voir la mission active")
        print("2) Changer de mission")
        print("3) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            clear()
            banner()
            print(color("\nMission active", CYAN, bold=True))
            print(hr())
            for k, v in mission.items():
                print(f"{k}: {v}")
            pause()
        elif choice == "2":
            missions_menu()
        elif choice == "3":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch36_mission_dashboard_pro():
    devices = load_last_scan()
    history = load_scan_history()

    clear()
    banner()
    print(color("\n13) Mission Dashboard Pro", CYAN, bold=True))
    print(hr())

    mission = active_mission()
    print(f"Mission active : {mission.get('label', '-')}")
    if mission.get("focus"):
        print(f"Focus          : {mission.get('focus')}")
    print()

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    helios = build_helios_report(devices, history)
    oracle = build_oracle_report(devices, history)
    nebula = build_nebula_report(devices, history)

    print(f"HELIOS threat   : {helios.get('threat_state', '-')}")
    print(f"HELIOS focus    : {helios.get('focus', '-')}")
    print(f"Top priority    : {helios.get('top_priority', 0)}")
    print(f"ORACLE outlook  : {oracle.get('outlook', '-')}")
    print(f"ORACLE immédiat : {oracle.get('immediate_count', 0)}")
    print(f"NEBULA state    : {nebula.get('master_state', '-')}")
    print()

    print("Top cibles mission:")
    targets = helios.get("immediate_targets", [])
    if targets:
        for t in targets[:6]:
            print(
                f"- {t['name']} | {t['address']} | priority={t['priority_score']} | "
                f"trust={t['trust_label']} | alert={t['alert_level']}"
            )
    else:
        print("- aucune")

    print()
    print("Recommandations:")
    recs = helios.get("recommendations", [])
    if recs:
        for r in recs[:8]:
            print(f"- {r}")
    else:
        print("- aucune")

    pause()


def batch36_guided_scenarios_pro():
    while True:
        clear()
        banner()
        print(color("\n14) Guided Scenarios Pro", CYAN, bold=True))
        print(hr())
        print("1) Ouvrir le menu scénarios")
        print("2) Voir le scénario recommandé")
        print("3) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            scenario_menu()
        elif choice == "2":
            devices = load_last_scan()
            history = load_scan_history()

            clear()
            banner()
            print(color("\nScénario recommandé", CYAN, bold=True))
            print(hr())

            if not devices:
                print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
                pause()
                continue

            helios = build_helios_report(devices, history)
            oracle = build_oracle_report(devices, history)
            brief = build_commander_brief(devices, history)

            if helios.get("watch_hits", 0) >= 1:
                label = "Réponse watch hit"
                steps = [
                    "Consulter la watchlist",
                    "Ouvrir ARGUS case file",
                    "Créer une watch session SENTINEL",
                    "Exporter un incident pack",
                ]
            elif oracle.get("immediate_count", 0) >= 1:
                label = "Réponse cible chaude"
                steps = [
                    "Ouvrir ORACLE",
                    "Ouvrir ARGUS",
                    "Comparer avec ATLAS / NEXUS",
                    "Exporter un audit terrain",
                ]
            elif helios.get("top_priority", 0) >= 60:
                label = "Investigation renforcée"
                steps = [
                    "Ouvrir HELIOS",
                    "Ouvrir Alert Center",
                    "Ouvrir Investigation Hub",
                    "Sauvegarder une watch session si besoin",
                ]
            else:
                label = "Surveillance standard"
                steps = [
                    "Lancer un scan normal",
                    "Lire le brief COMMANDER",
                    "Consulter Smart Views Pro",
                    "Faire un rapport quotidien si nécessaire",
                ]

            print(f"Scénario : {label}")
            print(f"Action suivante : {brief.get('next_action', '-')}")
            print()
            for s in steps:
                print(f"- {s}")
            pause()
        elif choice == "3":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch36_html_dashboard_pro():
    from pathlib import Path

    reports_dir = Path("reports")

    while True:
        clear()
        banner()
        print(color("\n15) HTML Dashboard Pro", CYAN, bold=True))
        print(hr())
        print("1) Ouvrir le dernier HTML")
        print("2) Voir les derniers dashboards HTML")
        print("3) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            open_last()

        elif choice == "2":
            clear()
            banner()
            print(color("\nDerniers dashboards HTML", CYAN, bold=True))
            print(hr())

            if not reports_dir.exists():
                print(color("Dossier reports introuvable.", YELLOW, bold=True))
                pause()
                continue

            html_files = sorted(reports_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)

            if not html_files:
                print(color("Aucun dashboard HTML.", YELLOW, bold=True))
            else:
                for p in html_files[:15]:
                    print(f"- {p}")
            pause()

        elif choice == "3":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()



def _batch37_list_files(title, folder, pattern="*", limit=20):
    from pathlib import Path

    clear()
    banner()
    print(color(f"\n{title}", CYAN, bold=True))
    print(hr())

    folder = Path(folder)
    if not folder.exists():
        print(color("Dossier introuvable.", YELLOW, bold=True))
        pause()
        return

    files = sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print(color("Aucun fichier.", YELLOW, bold=True))
        pause()
        return

    for p in files[:limit]:
        print(f"- {p}")
    pause()


def _batch37_sentinel_brief():
    devices = load_last_scan()
    history = load_scan_history()
    previous_devices = history[-2].get("devices", []) if len(history) >= 2 else []

    clear()
    banner()
    print(color("\nSweep sentinelle", CYAN, bold=True))
    print(hr())

    if not devices:
        print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    report = build_sentinel_report(devices, previous_devices, history)
    for line in sentinel_lines(report)[:14]:
        print(line)
    pause()


def _batch37_whitelist_rows():
    from ble_radar.state import load_json
    from ble_radar.config import WHITELIST_FILE

    rows = load_json(WHITELIST_FILE, [])
    return rows if isinstance(rows, list) else []


def _batch37_whitelist_item_text(item):
    if isinstance(item, dict):
        addr = item.get("address") or item.get("value") or item.get("addr") or "-"
        name = item.get("name") or item.get("label") or "Inconnu"
        return f"{name} | {addr}"
    return str(item)


def batch37_history_local_pro():
    while True:
        history = load_scan_history()

        clear()
        banner()
        print(color("\n16) Historique Local Pro", CYAN, bold=True))
        print(hr())

        print(f"Scans enregistrés : {len(history)}")
        if history:
            last = history[-1]
            print(f"Dernier scan      : {last.get('stamp', last.get('timestamp', '-'))}")
        print()
        print("1) Résumé historique")
        print("2) Voir les derniers scans")
        print("3) Voir les daily reports")
        print("4) Voir les watch sessions")
        print("5) Voir les sessions NEBULA")
        print("6) Voir les snapshots")
        print("7) Ouvrir l'historique classique")
        print("8) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            clear()
            banner()
            print(color("\nRésumé historique", CYAN, bold=True))
            print(hr())
            if not history:
                print(color("Historique vide.", YELLOW, bold=True))
            else:
                for scan in history[-12:]:
                    stamp = scan.get("stamp", scan.get("timestamp", "-"))
                    count = scan.get("count", len(scan.get("devices", [])))
                    crit = scan.get("critical", 0)
                    high = scan.get("high", 0)
                    med = scan.get("medium", 0)
                    print(f"- {stamp} | count={count} | crit={crit} | high={high} | med={med}")
            pause()
        elif choice == "2":
            _batch37_list_files("Derniers scans", "reports", "scan_*.*", 25)
        elif choice == "3":
            _batch37_list_files("Daily reports", "history/daily_reports", "*", 25)
        elif choice == "4":
            _batch37_list_files("Watch sessions", "history/watch_sessions", "*", 25)
        elif choice == "5":
            _batch37_list_files("Sessions NEBULA", "history/nebula_sessions", "*", 25)
        elif choice == "6":
            _batch37_list_files("Snapshots", "snapshots", "*", 25)
        elif choice == "7":
            show_history()
        elif choice == "8":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch37_live_radar_pro():
    while True:
        clear()
        banner()
        print(color("\n17) Radar Live Pro", CYAN, bold=True))
        print(hr())
        print("1) Radar live standard")
        print("2) Sweep normal + briefing")
        print("3) Sweep profond + briefing")
        print("4) Sweep sentinelle")
        print("5) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            live_radar()
        elif choice == "2":
            do_scan_mode("normal")
            _batch34_commander_after_scan()
        elif choice == "3":
            do_scan_mode("deep")
            _batch34_commander_after_scan()
        elif choice == "4":
            do_scan_mode("deep")
            _batch37_sentinel_brief()
        elif choice == "5":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch37_whitelist_view_pro():
    rows = _batch37_whitelist_rows()
    devices = load_last_scan()

    clear()
    banner()
    print(color("\n18) Whitelist View Pro", CYAN, bold=True))
    print(hr())
    print(f"Entrées whitelist : {len(rows)}")
    print()

    if rows:
        for item in rows[:50]:
            print(f"- {_batch37_whitelist_item_text(item)}")
    else:
        print(color("Whitelist vide.", YELLOW, bold=True))

    if devices and rows:
        print()
        print("Matches dans le dernier scan :")
        raw_text = " ".join(_batch37_whitelist_item_text(x).upper() for x in rows)
        found = 0
        for d in devices:
            addr = str(d.get("address", "-")).upper()
            name = str(d.get("name", "Inconnu")).upper()
            if addr in raw_text or name in raw_text:
                print(f"- {d.get('name','Inconnu')} | {d.get('address','-')}")
                found += 1
        if found == 0:
            print("- aucun")
    pause()


def batch37_whitelist_add_pro():
    while True:
        rows = _batch37_whitelist_rows()
        devices = load_last_scan()

        clear()
        banner()
        print(color("\n19) Whitelist Add Pro", CYAN, bold=True))
        print(hr())
        print(f"Entrées actuelles : {len(rows)}")
        print(f"Devices dernier scan : {len(devices) if devices else 0}")
        print()
        print("1) Ajouter depuis le dernier scan")
        print("2) Voir la whitelist")
        print("3) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            add_last_seen_to_named_list("white")
        elif choice == "2":
            batch37_whitelist_view_pro()
        elif choice == "3":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch37_whitelist_remove_pro():
    while True:
        rows = _batch37_whitelist_rows()

        clear()
        banner()
        print(color("\n20) Whitelist Remove Pro", CYAN, bold=True))
        print(hr())
        print(f"Entrées actuelles : {len(rows)}")
        print()
        print("1) Retirer une entrée")
        print("2) Voir la whitelist")
        print("3) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            remove_from_named_list("white")
        elif choice == "2":
            batch37_whitelist_view_pro()
        elif choice == "3":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()



def _batch38_watchlist_rows():
    from ble_radar.state import load_json
    from ble_radar.config import WATCHLIST_FILE

    rows = load_json(WATCHLIST_FILE, [])
    return rows if isinstance(rows, list) else []


def _batch38_named_item_text(item):
    if isinstance(item, dict):
        addr = item.get("address") or item.get("value") or item.get("addr") or "-"
        name = item.get("name") or item.get("label") or "Inconnu"
        return f"{name} | {addr}"
    return str(item)


def batch38_watchlist_view_pro():
    rows = _batch38_watchlist_rows()
    devices = load_last_scan()

    clear()
    banner()
    print(color("\n21) Watchlist View Pro", CYAN, bold=True))
    print(hr())
    print(f"Entrées watchlist : {len(rows)}")
    print()

    if rows:
        for item in rows[:50]:
            print(f"- {_batch38_named_item_text(item)}")
    else:
        print(color("Watchlist vide.", YELLOW, bold=True))

    if devices and rows:
        print()
        print("Matches dans le dernier scan :")
        raw_text = " ".join(_batch38_named_item_text(x).upper() for x in rows)
        found = 0
        for d in devices:
            addr = str(d.get("address", "-")).upper()
            name = str(d.get("name", "Inconnu")).upper()
            if addr in raw_text or name in raw_text:
                print(
                    f"- {d.get('name','Inconnu')} | {d.get('address','-')} | "
                    f"score={d.get('final_score', d.get('score', 0))} | "
                    f"alert={d.get('alert_level','faible')}"
                )
                found += 1
        if found == 0:
            print("- aucun")
    pause()


def batch38_watchlist_add_pro():
    while True:
        rows = _batch38_watchlist_rows()
        devices = load_last_scan()

        clear()
        banner()
        print(color("\n22) Watchlist Add Pro", CYAN, bold=True))
        print(hr())
        print(f"Entrées actuelles : {len(rows)}")
        print(f"Devices dernier scan : {len(devices) if devices else 0}")
        print()
        print("1) Ajouter depuis le dernier scan")
        print("2) Voir la watchlist")
        print("3) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            add_last_seen_to_named_list("watch")
        elif choice == "2":
            batch38_watchlist_view_pro()
        elif choice == "3":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch38_watchlist_remove_pro():
    while True:
        rows = _batch38_watchlist_rows()

        clear()
        banner()
        print(color("\n23) Watchlist Remove Pro", CYAN, bold=True))
        print(hr())
        print(f"Entrées actuelles : {len(rows)}")
        print()
        print("1) Retirer une entrée")
        print("2) Voir la watchlist")
        print("3) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            remove_from_named_list("watch")
        elif choice == "2":
            batch38_watchlist_view_pro()
        elif choice == "3":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch38_top_recurrents_pro():
    history = load_scan_history()

    clear()
    banner()
    print(color("\n24) Top Récurrents Pro", CYAN, bold=True))
    print(hr())

    rows = persistence_rankings(history, 25)
    if not rows:
        print(color("Aucune donnée historique.", YELLOW, bold=True))
        pause()
        return

    for row in rows:
        print(
            f"- {row['name']} | {row['address']} | "
            f"persist={row['persistence_score']} | occ={row['occurrences']} | "
            f"days={row['unique_days']} | "
            f"patterns={', '.join(row['patterns']) if row['patterns'] else '-'}"
        )
    pause()


def batch38_event_log_pro():
    while True:
        clear()
        banner()
        print(color("\n25) Event Log Pro", CYAN, bold=True))
        print(hr())
        print("1) Voir le journal d'événements")
        print("2) Voir seulement WARNING/ERROR")
        print("3) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            show_event_log()

        elif choice == "2":
            from ble_radar.eventlog import read_events

            events = read_events(300)
            clear()
            banner()
            print(color("\nJournal WARNING / ERROR", CYAN, bold=True))
            print(hr())

            filtered = [e for e in events if str(e.get("level", "")).lower() in ("warning", "error")]
            if not filtered:
                print(color("Aucun événement WARNING/ERROR.", GREEN, bold=True))
            else:
                for e in filtered[:80]:
                    print(f"- [{e.get('ts','-')}] {e.get('level','-').upper()} | {e.get('message','-')}")
            pause()

        elif choice == "3":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()



def batch40_argus_center_pro():
    while True:
        clear()
        banner()
        print(color("\n31) ARGUS Center Pro", CYAN, bold=True))
        print(hr())
        print("1) Ouvrir ARGUS Center")
        print("2) Voir les priorités")
        print("3) Ouvrir un case file")
        print("4) Voir les actions recommandées")
        print("5) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            argus_center()
        elif choice == "2":
            argus_priority_view()
        elif choice == "3":
            argus_casefile_view()
        elif choice == "4":
            argus_actions_view()
        elif choice == "5":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch40_sentinel_center_pro():
    while True:
        clear()
        banner()
        print(color("\n32) SENTINEL Center Pro", CYAN, bold=True))
        print(hr())
        print("1) Ouvrir SENTINEL Center")
        print("2) Dashboard de menace")
        print("3) Campaign view")
        print("4) Escalades")
        print("5) Sauvegarder une watch session")
        print("6) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            sentinel_center()
        elif choice == "2":
            sentinel_dashboard()
        elif choice == "3":
            sentinel_campaigns_view()
        elif choice == "4":
            sentinel_escalations_view()
        elif choice == "5":
            sentinel_watch_session_view()
        elif choice == "6":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch40_atlas_center_pro():
    while True:
        clear()
        banner()
        print(color("\n33) ATLAS Center Pro", CYAN, bold=True))
        print(hr())
        print("1) Ouvrir ATLAS Center")
        print("2) Hot edges")
        print("3) Voisins d'un appareil")
        print("4) Clusters vendor/profile")
        print("5) Groupes de risque")
        print("6) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            atlas_center()
        elif choice == "2":
            atlas_hot_edges_view()
        elif choice == "3":
            atlas_neighbors_view()
        elif choice == "4":
            atlas_clusters_view()
        elif choice == "5":
            atlas_risk_groups_view()
        elif choice == "6":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch40_helios_center_pro():
    while True:
        clear()
        banner()
        print(color("\n34) HELIOS Center Pro", CYAN, bold=True))
        print(hr())
        print("1) Ouvrir HELIOS Center")
        print("2) Executive dashboard")
        print("3) Top cibles immédiates")
        print("4) Recommandations fusionnées")
        print("5) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            helios_center()
        elif choice == "2":
            helios_dashboard()
        elif choice == "3":
            helios_targets_view()
        elif choice == "4":
            helios_recommendations_view()
        elif choice == "5":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch40_aegis_center_pro():
    while True:
        clear()
        banner()
        print(color("\n35) AEGIS Center Pro", CYAN, bold=True))
        print(hr())
        print("1) Ouvrir AEGIS Center")
        print("2) Dashboard")
        print("3) Incidents composés")
        print("4) Playbooks actifs")
        print("5) Seuils / moteur")
        print("6) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            aegis_center()
        elif choice == "2":
            aegis_dashboard()
        elif choice == "3":
            aegis_incidents_view()
        elif choice == "4":
            aegis_playbooks_view()
        elif choice == "5":
            aegis_thresholds_view()
        elif choice == "6":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()



def batch41_oracle_center_pro():
    while True:
        clear()
        banner()
        print(color("\n36) ORACLE Center Pro", CYAN, bold=True))
        print(hr())
        print("1) Ouvrir ORACLE Center")
        print("2) Forecast dashboard")
        print("3) Risques à venir")
        print("4) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            oracle_center()
        elif choice == "2":
            oracle_dashboard()
        elif choice == "3":
            oracle_targets_view()
        elif choice == "4":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch41_nebula_center_pro():
    while True:
        clear()
        banner()
        print(color("\n37) NEBULA Center Pro", CYAN, bold=True))
        print(hr())
        print("1) Ouvrir NEBULA Center")
        print("2) Master dashboard")
        print("3) Résumé de session")
        print("4) Sauvegarder résumé de session")
        print("5) Voir les dossiers")
        print("6) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            nebula_center()
        elif choice == "2":
            nebula_dashboard()
        elif choice == "3":
            nebula_session_view()
        elif choice == "4":
            nebula_save_session_view()
        elif choice == "5":
            nebula_cases_view()
        elif choice == "6":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch41_citadel_center_pro():
    while True:
        clear()
        banner()
        print(color("\n38) CITADEL Center Pro", CYAN, bold=True))
        print(hr())
        print("1) Ouvrir CITADEL Center")
        print("2) Check-up global")
        print("3) Sauvegarder rapport CITADEL")
        print("4) Export global")
        print("5) Incident pack")
        print("6) Maintenance intégrée")
        print("7) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            citadel_center()
        elif choice == "2":
            citadel_dashboard()
        elif choice == "3":
            citadel_save_report_view()
        elif choice == "4":
            citadel_export_global_view()
        elif choice == "5":
            citadel_incident_pack_view()
        elif choice == "6":
            citadel_maintenance_view()
        elif choice == "7":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch41_commander_center_pro():
    while True:
        clear()
        banner()
        print(color("\n39) COMMANDER Center Pro", CYAN, bold=True))
        print(hr())
        print("1) Ouvrir COMMANDER Center")
        print("2) Startup check")
        print("3) Brief opérateur")
        print("4) Mode simple")
        print("5) Workflows")
        print("6) Manuel local")
        print("7) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            commander_center()
        elif choice == "2":
            commander_startup_view()
        elif choice == "3":
            commander_brief_view()
        elif choice == "4":
            commander_simple_mode()
        elif choice == "5":
            commander_workflows_view()
        elif choice == "6":
            commander_manual_view()
        elif choice == "7":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch41_exit_pro():
    devices = load_last_scan()
    history = load_scan_history()

    clear()
    banner()
    print(color("\n40) Quitter Pro", CYAN, bold=True))
    print(hr())

    print(f"FORTRESS : {integrity_status_label()}")

    if devices:
        try:
            brief = build_commander_brief(devices, history)
            print(f"Top priority : {brief.get('top_priority', 0)}")
            print(f"Threat state : {brief.get('threat_state', '-')}")
            print(f"Action suivante : {brief.get('next_action', '-')}")
        except Exception as e:
            print(f"Brief indisponible : {e}")
    else:
        print("Aucun dernier scan disponible.")

    print()
    print("Sortie propre OMEGA.")
    return True

def saved_queries_menu():
    while True:
        clear()
        banner()
        queries = load_saved_queries()
        print(color("\nSaved queries", CYAN, bold=True))
        print(hr())
        for i, q in enumerate(queries, start=1):
            print(f"{i}) {q}")
        print("a) Ajouter une requête")
        print("r) Supprimer une requête")
        print("x) Exécuter une requête")
        print("0) Retour")

        choice = input("Choix > ").strip().lower()

        if choice == "0":
            break
        elif choice == "a":
            q = input("Nouvelle requête > ").strip()
            if q:
                add_saved_query(q)
        elif choice == "r":
            raw = input("Index à supprimer > ").strip()
            if raw.isdigit():
                remove_saved_query(int(raw) - 1)
        elif choice == "x":
            raw = input("Index à exécuter > ").strip()
            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < len(queries):
                    search_last_scan_interactive(queries[idx])
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def export_audit_from_last_scan():
    devices = load_last_scan()
    if not devices:
        clear()
        banner()
        print(color("\nAucun dernier scan disponible.", YELLOW, bold=True))
        pause()
        return

    comp = compare_last_two_scans()
    package = build_audit_package(devices, comp)
    paths = save_audit_package(package)

    clear()
    banner()
    print(color("\nAudit exporté", CYAN, bold=True))
    print(hr())
    print("JSON :", paths["json"])
    print("TXT  :", paths["txt"])
    pause()


def profiles_menu():
    while True:
        clear()
        banner()
        current = active_profile()
        print(color("\nProfils opérateur", CYAN, bold=True))
        print(hr())
        print(f"Actif: {current['label']} ({current['key']})")
        print()

        profiles = list_profiles()
        for i, p in enumerate(profiles, start=1):
            print(f"{i}) {p['label']} | key={p['key']} | scan={p['scan_seconds']}s | live={p['live_seconds']}s | alert_floor={p['alert_floor']}")
            print(f"   {p['description']}")
        print("0) Retour")

        raw = input("Choix > ").strip()
        if raw == "0":
            break
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(profiles):
                chosen = profiles[idx]
                set_profile_key(chosen["key"])
                print(color(f"\nProfil actif: {chosen['label']}", GREEN, bold=True))
                pause()


def missions_menu():
    while True:
        clear()
        banner()
        current = active_mission()
        print(color("\nModes de mission", CYAN, bold=True))
        print(hr())
        print(f"Mission active: {current['label']} ({current['key']})")
        print()

        missions = list_missions()
        for i, m in enumerate(missions, start=1):
            print(f"{i}) {m['label']} | key={m['key']} | focus={m['focus']}")
            print(f"   {m['description']}")
        print("0) Retour")

        raw = input("Choix > ").strip()
        if raw == "0":
            break
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(missions):
                chosen = missions[idx]
                set_active_mission(chosen["key"])
                print(color(f"\nMission active: {chosen['label']}", GREEN, bold=True))
                pause()


def show_metrics():
    devices = load_last_scan()
    if not devices:
        result = run_engine_cycle(seconds=prof_scan_seconds(), save_reports=False)
        devices = result["devices"]

    current, baseline, anomalies = compute_metrics(devices)

    clear()
    banner()
    print(color(f"\nMétriques, santé radio & anomalies [{active_profile()['label']}]", CYAN, bold=True))
    print(hr())

    for line in metrics_to_lines(current, baseline, anomalies):
        print(line)

    print()
    show_radio_health(devices)
    print()
    show_mission_summary(devices)
    pause()


def replay_lab():
    while True:
        scans = list_recent_scans(12)

        clear()
        banner()
        print(color("\nReplay lab", CYAN, bold=True))
        print(hr())

        if not scans:
            print(color("Aucun scan historique.", YELLOW, bold=True))
            pause()
            return

        for pos, (hist_idx, scan) in enumerate(scans, start=1):
            stamp = scan.get("stamp", scan.get("timestamp", "-"))
            print(f"{pos}) {stamp} | total={scan.get('count',0)} | crit={scan.get('critical',0)} | high={scan.get('high',0)} | medium={scan.get('medium',0)}")
        print("v) Voir un scan")
        print("c) Comparer deux scans")
        print("0) Retour")

        choice = input("Choix > ").strip().lower()

        if choice == "0":
            break
        elif choice == "v":
            raw = input("Index scan > ").strip()
            if raw.isdigit():
                pos = int(raw) - 1
                if 0 <= pos < len(scans):
                    _, scan = scans[pos]
                    devices = scan_devices(scan)
                    render_devices(devices, f"Replay: {scan.get('stamp', scan.get('timestamp', '-'))}")
                    print()
                    print(color("Résumé scan historique", CYAN, bold=True))
                    print(hr())
                    for line in scan_summary_lines(scan):
                        print(line)
                    pause()
        elif choice == "c":
            raw1 = input("Index scan A > ").strip()
            raw2 = input("Index scan B > ").strip()
            if raw1.isdigit() and raw2.isdigit():
                p1 = int(raw1) - 1
                p2 = int(raw2) - 1
                if 0 <= p1 < len(scans) and 0 <= p2 < len(scans):
                    _, scan_a = scans[p1]
                    _, scan_b = scans[p2]
                    comp = compare_scan_sets(scan_devices(scan_b), scan_devices(scan_a))
                    clear()
                    banner()
                    print(color("\nComparaison replay", CYAN, bold=True))
                    print(hr())
                    print(f"A: {scan_a.get('stamp', scan_a.get('timestamp', '-'))}")
                    print(f"B: {scan_b.get('stamp', scan_b.get('timestamp', '-'))}")
                    print()
                    print(f"Nouveaux: {len(comp['added'])}")
                    print(f"Disparus: {len(comp['removed'])}")
                    print(f"Communs : {len(comp['common'])}")
                    pause()
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def command_center():
    clear()
    banner()
    print(color("\nCommand center", CYAN, bold=True))
    print(hr())
    print("Exemples:")
    for line in command_help_lines():
        print(f"- {line}")
    print()

    cmd = input("Commande > ").strip()
    parsed = parse_command(cmd)
    action = parsed.get("action")

    if action == "scan":
        do_scan()
    elif action == "alerts":
        show_alerts_only()
    elif action == "trackers":
        show_trackers_only()
    elif action == "investigation":
        open_investigation_menu()
    elif action == "views":
        smart_views_menu()
    elif action == "history":
        show_history()
    elif action == "compare":
        show_last_two_scan_compare()
    elif action == "suggestions":
        show_query_suggestions()
    elif action == "audit":
        export_audit_from_last_scan()
    elif action == "metrics":
        show_metrics()
    elif action == "replay":
        replay_lab()
    elif action == "open_html":
        open_last()
    elif action == "search_last":
        search_last_scan_interactive(parsed.get("query"))
    elif action == "search_history":
        search_history_interactive(parsed.get("query"))
    elif action == "profile":
        q = (parsed.get("query") or "").strip()
        if q:
            set_profile_key(q)
            print(color(f"\nProfil actif: {active_profile()['label']}", GREEN, bold=True))
            pause()
        else:
            profiles_menu()
    elif action == "view_critical":
        run_view("Vue critique", view_critical)
    elif action == "view_high":
        run_view("Vue élevés +", view_high_plus)
    elif action == "view_watch_hits":
        run_view("Vue watchlist hits", view_watch_hits)
    elif action == "view_new":
        run_view("Vue nouveaux appareils", view_new_devices)
    elif action == "view_near":
        run_view("Vue proximité persistante", view_nearby)
    elif action == "view_apple":
        run_view("Vue Apple-like", view_apple_like)
    elif action == "view_random":
        run_view("Vue MAC random", view_random_mac)
    elif action == "view_unknown_vendor":
        run_view("Vue vendor inconnu", view_unknown_vendor)
    else:
        print(color("\nCommande inconnue.", YELLOW, bold=True))
        pause()


def live_radar():
    previous_cycle = []
    try:
        while True:
            devices = only_alerts(run_engine_scan(prof_live_seconds()), prof_alert_floor())
            if not devices:
                devices = run_engine_scan(prof_live_seconds())

            comp = compare_scan_sets(devices, previous_cycle)
            changes = changed_alerts(devices, previous_cycle)

            render_devices(devices, f"Radar live IA [{active_profile()['label']} | {active_mission()['label']}] (Ctrl+C pour sortir)")
            show_vendor_summary(devices)
            print()
            print(color("Changements live", CYAN, bold=True))
            print(hr())
            print(f"Nouveaux: {len(comp['added'])} | Disparus: {len(comp['removed'])} | Changement niveau/score: {len(changes)}")
            for row in changes[:6]:
                cur = row["current"]
                prev = row["previous"]
                print(
                    f"- {cur.get('name','Inconnu')} | {cur.get('address','-')} | "
                    f"{prev.get('alert_level','faible')}->{cur.get('alert_level','faible')} | "
                    f"{prev.get('final_score', prev.get('score', 0))}->{cur.get('final_score', cur.get('score', 0))}"
                )

            print()
            print(color(f"Rafraîchissement auto toutes les {prof_live_seconds()} secondes...", CYAN, bold=True))
            previous_cycle = devices
            time.sleep(prof_live_seconds())
    except KeyboardInterrupt:
        print()
        print(color("Sortie du radar live.", GREEN, bold=True))
        pause()

















def main_menu():
    while True:
        clear()
        banner()
        prof = active_profile()
        mission = active_mission()
        fortress = integrity_status_label()
        print(color(f"\nBLE RADAR OMEGA — COMMANDER CITADEL NEBULA ORACLE AEGIS HELIOS ATLAS SENTINEL ARGUS OMEGA-X NEXUS TITAN [{prof['label']} | {mission['label']} | {fortress}]\n", CYAN, bold=True))
        print("1) Scan Hub Pro")
        print("2) Alert Center Pro")
        print("3) Tracker Hunt+ Pro")
        print("4) Investigation Hub Pro")
        print("5) Smart Views Pro")
        print("6) Command Center Pro")
        print("7) Query Vault+")
        print("8) Audit Export Pro")
        print("9) Metrics & Anomalies Pro")
        print("10) Replay Lab Pro")
        print("11) Operator Profiles Pro")
        print("12) Mission Modes Pro")
        print("13) Mission Dashboard Pro")
        print("14) Guided Scenarios Pro")
        print("15) HTML Dashboard Pro")
        print("16) Historique Local Pro")
        print("17) Radar Live Pro")
        print("18) Whitelist View Pro")
        print("19) Whitelist Add Pro")
        print("20) Whitelist Remove Pro")
        print("21) Watchlist View Pro")
        print("22) Watchlist Add Pro")
        print("23) Watchlist Remove Pro")
        print("24) Top Récurrents Pro")
        print("25) Event Log Pro")
        print("26) Automation Center Pro")
        print("27) Doctor / Integrity Pro")
        print("28) Snapshots / Restore Pro")
        print("29) NEXUS Center Pro")
        print("30) OMEGA-X Center Pro")
        print("31) ARGUS Center Pro")
        print("32) SENTINEL Center Pro")
        print("33) ATLAS Center Pro")
        print("34) HELIOS Center Pro")
        print("35) AEGIS Center Pro")
        print("36) ORACLE Center Pro")
        print("37) NEBULA Center Pro")
        print("38) CITADEL Center Pro")
        print("39) COMMANDER Center Pro")
        print("40) Quitter Pro")

        choice = input("Choix > ").strip()

        if choice == "1":
            batch34_scan_hub()
        elif choice == "2":
            batch34_alert_center()
        elif choice == "3":
            batch34_tracker_hunt()
        elif choice == "4":
            batch34_investigation_hub()
        elif choice == "5":
            batch34_smart_views()
        elif choice == "6":
            batch35_command_center_pro()
        elif choice == "7":
            batch35_query_vault()
        elif choice == "8":
            batch35_audit_export_pro()
        elif choice == "9":
            batch35_metrics_anomalies_pro()
        elif choice == "10":
            batch35_replay_lab_pro()
        elif choice == "11":
            batch36_operator_profiles_pro()
        elif choice == "12":
            batch36_mission_modes_pro()
        elif choice == "13":
            batch36_mission_dashboard_pro()
        elif choice == "14":
            batch36_guided_scenarios_pro()
        elif choice == "15":
            batch36_html_dashboard_pro()
        elif choice == "16":
            batch37_history_local_pro()
        elif choice == "17":
            batch37_live_radar_pro()
        elif choice == "18":
            batch37_whitelist_view_pro()
        elif choice == "19":
            batch37_whitelist_add_pro()
        elif choice == "20":
            batch37_whitelist_remove_pro()
        elif choice == "21":
            batch38_watchlist_view_pro()
        elif choice == "22":
            batch38_watchlist_add_pro()
        elif choice == "23":
            batch38_watchlist_remove_pro()
        elif choice == "24":
            batch38_top_recurrents_pro()
        elif choice == "25":
            batch38_event_log_pro()
        elif choice == "26":
            batch39_automation_center_pro()
        elif choice == "27":
            batch39_doctor_integrity_pro()
        elif choice == "28":
            batch39_snapshots_restore_pro()
        elif choice == "29":
            batch39_nexus_center_pro()
        elif choice == "30":
            batch39_omegax_center_pro()
        elif choice == "31":
            batch40_argus_center_pro()
        elif choice == "32":
            batch40_sentinel_center_pro()
        elif choice == "33":
            batch40_atlas_center_pro()
        elif choice == "34":
            batch40_helios_center_pro()
        elif choice == "35":
            batch40_aegis_center_pro()
        elif choice == "36":
            batch41_oracle_center_pro()
        elif choice == "37":
            batch41_nebula_center_pro()
        elif choice == "38":
            batch41_citadel_center_pro()
        elif choice == "39":
            batch41_commander_center_pro()
        elif choice == "40":
            if batch41_exit_pro():
                break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()

def main():
    main_menu()

def show_automation_result(auto_result):
    print()
    print(color("Automation engine", CYAN, bold=True))
    print(hr())

    if not auto_result.get("enabled", True):
        print("Moteur automation: désactivé")
        return

    ctx = auto_result.get("context", {})
    print(f"critical    : {ctx.get('critical', 0)}")
    print(f"high        : {ctx.get('high', 0)}")
    print(f"trackers    : {ctx.get('trackers', 0)}")
    print(f"watch_hits  : {ctx.get('watch_hits', 0)}")
    print(f"health      : {ctx.get('health_score', 0)} ({ctx.get('health_label', '-')})")

    executed = auto_result.get("executed", [])
    if not executed:
        print("Aucune action auto exécutée.")
        return

    print()
    print("Actions exécutées:")
    for item in executed:
        print(f"- {item.get('label', item.get('action', '-'))}")


def show_event_log():
    from ble_radar.eventlog import read_events

    events = read_events(60)
    clear()
    banner()
    print(color("\nJournal d'événements", CYAN, bold=True))
    print(hr())

    if not events:
        print(color("Aucun événement.", YELLOW, bold=True))
        pause()
        return

    for e in events:
        print(f"[{e.get('ts','-')}] {e.get('level','-').upper()} | {e.get('kind','-')} | {e.get('message','-')}")
    pause()


def automation_center():
    from ble_radar.automation import (
        load_automation_config,
        toggle_automation_engine,
        toggle_rule_by_index,
        run_automation_pipeline,
    )

    while True:
        cfg = load_automation_config()
        clear()
        banner()
        print(color("\nAutomation Center", CYAN, bold=True))
        print(hr())
        print(f"Moteur global: {'ON' if cfg.get('enabled', True) else 'OFF'}")
        print()

        rules = cfg.get("rules", [])
        for i, r in enumerate(rules, start=1):
            print(
                f"{i}) [{'ON' if r.get('enabled', True) else 'OFF'}] "
                f"{r.get('label','-')} | cond={r.get('condition','-')} | "
                f"seuil={r.get('threshold','-')} | action={r.get('action','-')}"
            )

        print()
        print("1) Toggle moteur global")
        print("2) Toggle une règle")
        print("3) Tester les automations sur le dernier scan")
        print("4) Voir le journal d'événements")
        print("5) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            toggle_automation_engine()
        elif choice == "2":
            raw = input("Index règle > ").strip()
            if raw.isdigit():
                toggle_rule_by_index(int(raw) - 1)
        elif choice == "3":
            devices = load_last_scan()
            clear()
            banner()
            print(color("\nTest automation sur dernier scan", CYAN, bold=True))
            print(hr())
            if not devices:
                print(color("Aucun dernier scan disponible.", YELLOW, bold=True))
            else:
                result = run_automation_pipeline(devices)
                show_automation_result(result)
            pause()
        elif choice == "4":
            show_event_log()
        elif choice == "5":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()

def batch39_automation_center_pro():
    while True:
        clear()
        banner()
        print(color("\n26) Automation Center Pro", CYAN, bold=True))
        print(hr())

        try:
            cfg = load_automation_config()
            enabled = cfg.get("enabled", True)
            rules = cfg.get("rules", [])
            print(f"Moteur automation : {'ON' if enabled else 'OFF'}")
            print(f"Règles           : {len(rules)}")
        except Exception as e:
            print(color(f"Lecture automation impossible: {e}", YELLOW, bold=True))

        print()
        print("1) Ouvrir Automation Center")
        print("2) Lancer un scan + pipeline auto")
        print("3) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            automation_center()
        elif choice == "2":
            do_scan_mode("normal")
            _batch34_commander_after_scan()
        elif choice == "3":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch39_doctor_integrity_pro():
    while True:
        clear()
        banner()
        print(color("\n27) Doctor / Integrity Pro", CYAN, bold=True))
        print(hr())

        try:
            report = build_doctor_report()
            stable = build_stableplus_report()
            print(f"FORTRESS : {integrity_status_label()}")
            print(f"Fichiers : {report['files_ok']}/{report['files_total']}")
            print(f"Imports  : {report['imports_ok']}/{report['imports_total']}")
            print(f"JSON     : {report['json_ok']}/{report['json_total']}")
            print(f"Stable+  : {stable.get('status', 'STABLE+ WARN')}")
            print(f"Doublons : {stable.get('duplicate_count', 0)}")
        except Exception as e:
            print(color(f"Doctor indisponible: {e}", YELLOW, bold=True))

        print()
        print("1) Ouvrir Doctor / integrity status")
        print("2) Voir le rapport Doctor détaillé")
        print("3) Voir l'audit Stable+")
        print("4) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            doctor_menu()
        elif choice == "2":
            clear()
            banner()
            print(color("\nRapport Doctor détaillé", CYAN, bold=True))
            print(hr())
            report = build_doctor_report()
            for line in doctor_lines(report):
                print(line)
            print()
            print(f"FORTRESS = {integrity_status_label()}")
            pause()
        elif choice == "3":
            clear()
            banner()
            print(color("\nAudit Stable+", CYAN, bold=True))
            print(hr())
            stable = build_stableplus_report()
            for line in stableplus_lines(stable):
                print(line)
            pause()
        elif choice == "4":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()



def create_snapshot(devices=None):
    return _create_snapshot_impl(devices, globals())

def batch39_snapshots_restore_pro():
    return _batch39_snapshots_restore_pro_impl(create_snapshot_fn=create_snapshot)


def batch39_nexus_center_pro():
    while True:
        clear()
        banner()
        print(color("\n29) NEXUS Center Pro", CYAN, bold=True))
        print(hr())
        print("1) Ouvrir NEXUS Center")
        print("2) Timeline appareil")
        print("3) Top persistance")
        print("4) Motifs récurrents")
        print("5) Ce qui a changé aujourd'hui")
        print("6) Incident enrichi")
        print("7) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            nexus_center()
        elif choice == "2":
            nexus_timeline_search()
        elif choice == "3":
            nexus_persistence_view()
        elif choice == "4":
            nexus_patterns_view()
        elif choice == "5":
            nexus_daily_changes()
        elif choice == "6":
            nexus_enriched_incident()
        elif choice == "7":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch39_omegax_center_pro():
    while True:
        clear()
        banner()
        print(color("\n30) OMEGA-X Center Pro", CYAN, bold=True))
        print(hr())
        print("1) Ouvrir OMEGA-X Center")
        print("2) Base de connaissance")
        print("3) Rechercher un appareil connu")
        print("4) Étiqueter un appareil")
        print("5) Anomalies de comportement")
        print("6) Rapport quotidien")
        print("7) Générer le rapport quotidien")
        print("8) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            omegax_center()
        elif choice == "2":
            omegax_known_devices_view()
        elif choice == "3":
            omegax_search_known_device()
        elif choice == "4":
            omegax_label_device()
        elif choice == "5":
            omegax_behavior_view()
        elif choice == "6":
            omegax_daily_report_view()
        elif choice == "7":
            omegax_daily_report_generate()
        elif choice == "8":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()

def _batch43_brief():
    devices = load_last_scan()
    history = load_scan_history()
    out = {
        "devices": len(devices) if devices else 0,
        "top_priority": 0,
        "threat_state": "bruit_normal",
        "next_action": "-",
    }
    if devices:
        try:
            brief = build_commander_brief(devices, history)
            out["top_priority"] = brief.get("top_priority", 0)
            out["threat_state"] = brief.get("threat_state", "bruit_normal")
            out["next_action"] = brief.get("next_action", "-")
        except Exception:
            pass
    return out


def _batch43_header(title):
    clear()
    banner()
    print(color(f"\\n{title}", CYAN, bold=True))
    print(hr())
    s = _batch43_brief()
    print(
        f"Devices={s['devices']} | "
        f"Top={s['top_priority']} | "
        f"Threat={s['threat_state']} | "
        f"Next={s['next_action']}"
    )
    print()


def _batch43_scan_and_brief(mode="normal"):
    do_scan_mode(mode)
    _batch34_commander_after_scan()


def batch35_command_center_pro():
    while True:
        _batch43_header("6) Command Center Pro")
        print("1) Startup check")
        print("2) Brief opérateur")
        print("3) Scan normal + brief")
        print("4) Scan profond + brief")
        print("5) Alert Center")
        print("6) Tracker Hunt+")
        print("7) Incident pack")
        print("8) Maintenance")
        print("9) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            commander_startup_view()
        elif choice == "2":
            commander_brief_view()
        elif choice == "3":
            _batch43_scan_and_brief("normal")
        elif choice == "4":
            _batch43_scan_and_brief("deep")
        elif choice == "5":
            batch34_alert_center()
        elif choice == "6":
            batch34_tracker_hunt()
        elif choice == "7":
            citadel_incident_pack_view()
        elif choice == "8":
            citadel_maintenance_view()
        elif choice == "9":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch39_nexus_center_pro():
    while True:
        _batch43_header("29) NEXUS Center Pro")
        print("1) Timeline appareil")
        print("2) Top persistance")
        print("3) Motifs récurrents")
        print("4) Changements du jour")
        print("5) Incident enrichi")
        print("6) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            nexus_timeline_search()
        elif choice == "2":
            nexus_persistence_view()
        elif choice == "3":
            nexus_patterns_view()
        elif choice == "4":
            nexus_daily_changes()
        elif choice == "5":
            nexus_enriched_incident()
        elif choice == "6":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch39_omegax_center_pro():
    while True:
        _batch43_header("30) OMEGA-X Center Pro")
        print("1) Base de connaissance")
        print("2) Rechercher un appareil connu")
        print("3) Étiqueter un appareil")
        print("4) Anomalies comportementales")
        print("5) Rapport quotidien")
        print("6) Générer rapport quotidien")
        print("7) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            omegax_known_devices_view()
        elif choice == "2":
            omegax_search_known_device()
        elif choice == "3":
            omegax_label_device()
        elif choice == "4":
            omegax_behavior_view()
        elif choice == "5":
            omegax_daily_report_view()
        elif choice == "6":
            omegax_daily_report_generate()
        elif choice == "7":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch40_argus_center_pro():
    while True:
        _batch43_header("31) ARGUS Center Pro")
        print("1) Voir les priorités")
        print("2) Ouvrir un case file")
        print("3) Actions recommandées")
        print("4) Investigation Hub")
        print("5) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            argus_priority_view()
        elif choice == "2":
            argus_casefile_view()
        elif choice == "3":
            argus_actions_view()
        elif choice == "4":
            batch34_investigation_hub()
        elif choice == "5":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch40_sentinel_center_pro():
    while True:
        _batch43_header("32) SENTINEL Center Pro")
        print("1) Dashboard de menace")
        print("2) Campaign view")
        print("3) Escalades")
        print("4) Sauvegarder watch session")
        print("5) Sweep profond + brief")
        print("6) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            sentinel_dashboard()
        elif choice == "2":
            sentinel_campaigns_view()
        elif choice == "3":
            sentinel_escalations_view()
        elif choice == "4":
            sentinel_watch_session_view()
        elif choice == "5":
            _batch43_scan_and_brief("deep")
        elif choice == "6":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch40_atlas_center_pro():
    while True:
        _batch43_header("33) ATLAS Center Pro")
        print("1) Hot edges")
        print("2) Voisins d'un appareil")
        print("3) Clusters vendor/profile")
        print("4) Groupes de risque")
        print("5) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            atlas_hot_edges_view()
        elif choice == "2":
            atlas_neighbors_view()
        elif choice == "3":
            atlas_clusters_view()
        elif choice == "4":
            atlas_risk_groups_view()
        elif choice == "5":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch40_helios_center_pro():
    while True:
        _batch43_header("34) HELIOS Center Pro")
        print("1) Executive dashboard")
        print("2) Top cibles immédiates")
        print("3) Recommandations fusionnées")
        print("4) Scan normal + brief")
        print("5) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            helios_dashboard()
        elif choice == "2":
            helios_targets_view()
        elif choice == "3":
            helios_recommendations_view()
        elif choice == "4":
            _batch43_scan_and_brief("normal")
        elif choice == "5":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch40_aegis_center_pro():
    while True:
        _batch43_header("35) AEGIS Center Pro")
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


def batch41_oracle_center_pro():
    while True:
        _batch43_header("36) ORACLE Center Pro")
        print("1) Forecast dashboard")
        print("2) Risques à venir")
        print("3) Scan normal + brief")
        print("4) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            oracle_dashboard()
        elif choice == "2":
            oracle_targets_view()
        elif choice == "3":
            _batch43_scan_and_brief("normal")
        elif choice == "4":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch41_nebula_center_pro():
    while True:
        _batch43_header("37) NEBULA Center Pro")
        print("1) Master dashboard")
        print("2) Résumé de session")
        print("3) Sauvegarder résumé de session")
        print("4) Voir les dossiers")
        print("5) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            nebula_dashboard()
        elif choice == "2":
            nebula_session_view()
        elif choice == "3":
            nebula_save_session_view()
        elif choice == "4":
            nebula_cases_view()
        elif choice == "5":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch41_citadel_center_pro():
    while True:
        _batch43_header("38) CITADEL Center Pro")
        print("1) Check-up global")
        print("2) Sauvegarder rapport CITADEL")
        print("3) Export global")
        print("4) Incident pack")
        print("5) Maintenance intégrée")
        print("6) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            citadel_dashboard()
        elif choice == "2":
            citadel_save_report_view()
        elif choice == "3":
            citadel_export_global_view()
        elif choice == "4":
            citadel_incident_pack_view()
        elif choice == "5":
            citadel_maintenance_view()
        elif choice == "6":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch41_commander_center_pro():
    while True:
        _batch43_header("39) COMMANDER Center Pro")
        try:
            stable = build_stableplus_report()
            print(f"Stable+={stable.get('status','STABLE+ WARN')} | Doublons={stable.get('duplicate_count', 0)}")
            print()
        except Exception:
            pass

        print("1) Startup check")
        print("2) Brief opérateur")
        print("3) Mode simple")
        print("4) Workflows")
        print("5) Manuel local")
        print("6) Audit Stable+")
        print("7) Retour")

        choice = input("Choix > ").strip()

        if choice == "1":
            commander_startup_view()
        elif choice == "2":
            commander_brief_view()
        elif choice == "3":
            commander_simple_mode()
        elif choice == "4":
            commander_workflows_view()
        elif choice == "5":
            commander_manual_view()
        elif choice == "6":
            clear()
            banner()
            print(color("\nAudit Stable+", CYAN, bold=True))
            print(hr())
            stable = build_stableplus_report()
            for line in stableplus_lines(stable):
                print(line)
            pause()
        elif choice == "7":
            break
        else:
            print(color("Choix invalide", RED, bold=True))
            pause()


def batch41_exit_pro():
    devices = load_last_scan()
    history = load_scan_history()

    _batch43_header("40) Quitter Pro")

    if devices:
        try:
            brief = build_commander_brief(devices, history)
            print(f"Top priority    : {brief.get('top_priority', 0)}")
            print(f"Threat state    : {brief.get('threat_state', '-')}")
            print(f"Action suivante : {brief.get('next_action', '-')}")
        except Exception as e:
            print(f"Brief indisponible : {e}")
    else:
        print("Aucun dernier scan disponible.")

    print()
    print("Sortie propre OMEGA.")
    return True

def _batch43_safe_int(value, default=0):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, (list, tuple, set, dict)):
        return len(value)
    try:
        return int(value)
    except Exception:
        return default


def _batch43_fallback_brief():
    devices = load_last_scan() or []

    top_priority = 0
    critical = 0
    high = 0
    medium = 0
    watch_hits = 0
    suspicious = 0

    for d in devices:
        score = _batch43_safe_int(d.get("final_score", d.get("score", 0)))
        if score > top_priority:
            top_priority = score

        alert = str(d.get("alert_level", "faible"))
        if alert == "critique":
            critical += 1
        elif alert == "élevé":
            high += 1
        elif alert == "moyen":
            medium += 1

        if d.get("watch_hit"):
            watch_hits += 1
        if d.get("possible_suivi") or d.get("persistent_nearby"):
            suspicious += 1

    if critical >= 1 or watch_hits >= 1:
        threat_state = "menace_active"
        next_action = "ouvrir SENTINEL / AEGIS / ARGUS immédiatement"
    elif high >= 1 or suspicious >= 1:
        threat_state = "incident_probable"
        next_action = "ouvrir Investigation Hub puis ARGUS"
    elif medium >= 1 or top_priority >= 40:
        threat_state = "vigilance"
        next_action = "surveiller les cibles chaudes"
    else:
        threat_state = "bruit_normal"
        next_action = "surveillance standard"

    return {
        "devices": len(devices),
        "top_priority": top_priority,
        "threat_state": threat_state,
        "next_action": next_action,
    }


def _batch43_brief():
    devices = load_last_scan()
    history = load_scan_history()
    out = {
        "devices": len(devices) if devices else 0,
        "top_priority": 0,
        "threat_state": "bruit_normal",
        "next_action": "-",
    }

    if not devices:
        return out

    try:
        brief = build_commander_brief(devices, history)
        out["top_priority"] = _batch43_safe_int(brief.get("top_priority", 0))
        out["threat_state"] = str(brief.get("threat_state", "bruit_normal"))
        out["next_action"] = str(brief.get("next_action", "-"))
        return out
    except Exception:
        fallback = _batch43_fallback_brief()
        out["top_priority"] = fallback["top_priority"]
        out["threat_state"] = fallback["threat_state"]
        out["next_action"] = fallback["next_action"]
        return out


def batch41_exit_pro():
    _batch43_header("40) Quitter Pro")
    s = _batch43_brief()

    print(f"Top priority    : {s.get('top_priority', 0)}")
    print(f"Threat state    : {s.get('threat_state', 'bruit_normal')}")
    print(f"Action suivante : {s.get('next_action', '-')}")
    print()
    print("Sortie propre OMEGA.")
    return True


def _omega_safe_int(value, default=0):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, (list, tuple, set, dict)):
        return len(value)
    try:
        return int(value)
    except Exception:
        return default

if __name__ == "__main__":
    main()
