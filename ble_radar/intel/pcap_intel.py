from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from subprocess import run
from typing import List
import json


@dataclass
class DeviceHit:
    address: str
    hits: int
    risk_tags: List[str]


def _build_risk_tags(address: str, hits: int) -> List[str]:
    tags: List[str] = []

    if hits >= 3000:
        tags.append("PERSISTENT_DEVICE")
        tags.append("HIGH_ACTIVITY")
    elif hits >= 1000:
        tags.append("ACTIVE_DEVICE")
    elif hits >= 250:
        tags.append("OBSERVED_DEVICE")

    first_byte = address.split(":")[0].lower() if address else ""
    if first_byte in {"26", "06", "16", "17", "3e", "4e", "51", "59"}:
        tags.append("RANDOMIZED_BLE_ADDRESS")

    return tags


def extract_advertising_addresses(pcap_path: str | Path) -> List[str]:
    pcap_path = Path(pcap_path)

    result = run(
        [
            "tshark",
            "-r",
            str(pcap_path),
            "-T",
            "fields",
            "-e",
            "btle.advertising_address",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    addresses = []
    for line in result.stdout.splitlines():
        value = line.strip().lower()
        if value and value.count(":") == 5:
            addresses.append(value)

    return addresses


def summarize_pcap(pcap_path: str | Path, top_n: int = 20) -> List[DeviceHit]:
    addresses = extract_advertising_addresses(pcap_path)
    counts = Counter(addresses)

    ranked = counts.most_common(top_n)
    return [
        DeviceHit(
            address=address,
            hits=hits,
            risk_tags=_build_risk_tags(address, hits),
        )
        for address, hits in ranked
    ]


def export_summary_json(
    pcap_path: str | Path, output_path: str | Path, top_n: int = 20
) -> Path:
    summary = summarize_pcap(pcap_path, top_n=top_n)
    output_path = Path(output_path)

    payload = {
        "source_pcap": str(pcap_path),
        "device_count": len(summary),
        "devices": [asdict(item) for item in summary],
    }

    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path
