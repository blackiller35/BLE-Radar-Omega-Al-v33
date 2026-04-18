"""Session movement summary — step 5 of v1.1 metatron evolution.

Compares a current device list to a previous one and classifies each device as
new, disappeared, or recurring.  When a device registry is supplied the registry
score change (current minus previous snapshot score) is included for each
recurring device.

The module is standalone: it does not import any anomaly, behavior, or intel
analysis modules.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ble_radar.history.device_scoring import compute_device_score


def _addr(device: Dict[str, Any]) -> str:
    return str(device.get("address") or "").strip().upper()


def _label(device: Dict[str, Any]) -> str:
    name = str(device.get("name") or "Inconnu")
    addr = _addr(device) or "-"
    return f"{name} ({addr})"


def build_session_movement(
    current_devices: List[Dict[str, Any]],
    previous_devices: List[Dict[str, Any]],
    registry: Dict[str, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Return a movement summary dict comparing *current_devices* to *previous_devices*.

    Keys in the returned dict
    -------------------------
    new          — devices whose address was not present in the previous scan.
    disappeared  — devices present in the previous scan but absent now.
    recurring    — devices present in both scans.
    score_changes — list of score-delta entries for recurring devices where the
                    registry score changed (sorted by abs delta descending).
    counts       — convenience sub-dict {new, disappeared, recurring, total_current}.
    """
    reg = registry if isinstance(registry, dict) else {}

    prev_map: Dict[str, Dict[str, Any]] = {}
    for d in (previous_devices or []):
        a = _addr(d)
        if a:
            prev_map[a] = d

    curr_map: Dict[str, Dict[str, Any]] = {}
    for d in (current_devices or []):
        a = _addr(d)
        if a:
            curr_map[a] = d

    new: List[Dict[str, Any]] = []
    recurring: List[Dict[str, Any]] = []
    disappeared: List[Dict[str, Any]] = []

    for addr, dev in curr_map.items():
        if addr in prev_map:
            recurring.append(dev)
        else:
            new.append(dev)

    for addr, dev in prev_map.items():
        if addr not in curr_map:
            disappeared.append(dev)

    score_changes: List[Dict[str, Any]] = []
    for dev in recurring:
        addr = _addr(dev)
        rec = reg.get(addr, {})

        # Current score is computed against the live registry record.
        curr_score = compute_device_score(dev, rec)

        # Previous score: simulate what the record looked like one sighting ago
        # by decrementing seen_count by 1 (conservative; session_count unchanged).
        prev_rec: Dict[str, Any] = dict(rec)
        prev_seen = max(0, int(rec.get("seen_count") or 0) - 1)
        prev_rec["seen_count"] = prev_seen
        prev_score = compute_device_score(prev_map[addr], prev_rec)

        delta = curr_score - prev_score
        if delta != 0:
            score_changes.append({
                "address": addr,
                "name": str(dev.get("name") or "Inconnu"),
                "prev_score": prev_score,
                "curr_score": curr_score,
                "delta": delta,
            })

    score_changes.sort(key=lambda x: abs(x["delta"]), reverse=True)

    return {
        "new": new,
        "disappeared": disappeared,
        "recurring": recurring,
        "score_changes": score_changes,
        "counts": {
            "new": len(new),
            "disappeared": len(disappeared),
            "recurring": len(recurring),
            "total_current": len(curr_map),
        },
    }
