from __future__ import annotations
from typing import Any, Dict, List, Tuple


def build_correlation_pairs(session_devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    addresses = [d.get("address") for d in session_devices if d.get("address")]
    pairs: List[Tuple[str, str]] = []
    for i, a in enumerate(addresses):
        for b in addresses[i + 1:]:
            pair = tuple(sorted((a, b)))
            pairs.append(pair)

    return [
        {"device_a": a, "device_b": b, "co_seen_count": 1, "correlation_score": 10}
        for a, b in pairs
    ]


def top_correlated(pairs: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    return sorted(
        pairs,
        key=lambda x: (x.get("co_seen_count", 0), x.get("correlation_score", 0)),
        reverse=True,
    )[:limit]
