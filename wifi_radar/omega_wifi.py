from __future__ import annotations

from wifi_radar.dashboard import save_wifi_dashboard
from wifi_radar.history import summarize_wifi_history, update_wifi_history
from wifi_radar.scanner import save_wifi_scan, scan_wifi_nmcli
from wifi_radar.analyzer import analyze_wifi_networks


def run_wifi_omega_pipeline() -> dict:
    networks = analyze_wifi_networks(scan_wifi_nmcli())
    scan_path = save_wifi_scan(networks)
    history = update_wifi_history(networks)
    summary = summarize_wifi_history(history)
    dashboard_path = save_wifi_dashboard()

    return {
        "networks": networks,
        "scan_path": str(scan_path),
        "dashboard_path": str(dashboard_path),
        "summary": summary,
    }


def main() -> None:
    result = run_wifi_omega_pipeline()
    summary = result["summary"]

    print("📡 OMEGA WiFi Pipeline")
    print(f"Networks found: {len(result['networks'])}")
    print(f"Known networks: {summary['total_known_networks']}")
    print(f"Hidden: {summary['hidden_networks']}")
    print(f"Medium/High: {summary['medium_or_high_risk']}")
    print(f"Very close: {summary['very_close']}")
    print(f"Scan saved: {result['scan_path']}")
    print(f"Dashboard saved: {result['dashboard_path']}")


if __name__ == "__main__":
    main()
