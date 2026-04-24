from __future__ import annotations

import json
import subprocess

from wifi_radar.analyzer import analyze_wifi_networks
from wifi_radar.history import summarize_wifi_history, update_wifi_history
from datetime import datetime
from pathlib import Path


def scan_wifi_nmcli() -> list[dict]:
    """
    Passive WiFi scan using nmcli.
    Safe: no monitor mode, no packet injection.
    """
    cmd = [
        "nmcli",
        "-t",
        "-f",
        "SSID,BSSID,CHAN,FREQ,SIGNAL,SECURITY",
        "dev",
        "wifi",
        "list",
        "--rescan",
        "yes",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return []

    networks = []

    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        parts = line.split(":")
        if len(parts) < 6:
            continue

        ssid = parts[0] or "Hidden"
        bssid = ":".join(parts[1:7]) if len(parts) >= 7 else parts[1]
        rest = parts[7:] if len(parts) >= 7 else parts[2:]

        chan = rest[0] if len(rest) > 0 else ""
        freq = rest[1] if len(rest) > 1 else ""
        signal = rest[2] if len(rest) > 2 else "0"
        security = ":".join(rest[3:]) if len(rest) > 3 else ""

        try:
            signal_value = int(signal)
        except ValueError:
            signal_value = 0

        bssid = bssid.replace("\\:", ":")
        key = bssid.upper()

        item = {
            "ssid": ssid,
            "bssid": bssid,
            "channel": chan,
            "frequency": freq,
            "signal": signal_value,
            "security": security or "OPEN",
            "seen_at": datetime.now().isoformat(timespec="seconds"),
        }

        existing = next((n for n in networks if n["bssid"].upper() == key), None)
        if existing is None:
            networks.append(item)
        elif item["signal"] > existing.get("signal", 0):
            existing.update(item)

    return networks


def save_wifi_scan(networks: list[dict], output_dir: str | Path = "reports/wifi") -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = output / f"wifi_scan_{stamp}.json"
    path.write_text(json.dumps(networks, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> None:
    networks = analyze_wifi_networks(scan_wifi_nmcli())
    path = save_wifi_scan(networks)
    history = update_wifi_history(networks)
    summary = summarize_wifi_history(history)

    print(f"OMEGA WiFi Scanner")
    print(f"Networks found: {len(networks)}")
    print(f"Saved: {path}")
    print(f"Known networks: {summary['total_known_networks']} | Hidden: {summary['hidden_networks']} | Medium/High: {summary['medium_or_high_risk']} | Very close: {summary['very_close']}")

    for net in networks[:20]:
        print(
            f"- {net['ssid']} | {net['bssid']} | "
            f"CH {net['channel']} | Signal {net['signal']} | {net['security']} | "
            f"Risk {net.get('risk_level', 'low')}:{net.get('risk_score', 0)} | "
            f"Tags {','.join(net.get('risk_tags', [])) or 'NONE'}"
        )


if __name__ == "__main__":
    main()
