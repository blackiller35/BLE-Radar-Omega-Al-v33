from collections import Counter, defaultdict
from itertools import combinations

from ble_radar.state import load_scan_history
from ble_radar.argus import rank_priority
from ble_radar.nexus import search_device_summaries


def _addr(device):
    return str(device.get("address", "-")).upper()


def build_copresence_graph(history=None, min_weight: int = 2):
    if history is None:
        history = load_scan_history()

    nodes = {}
    edges = Counter()

    for scan in history:
        devices = scan.get("devices", [])
        addrs = []
        for d in devices:
            addr = _addr(d)
            if not addr or addr == "-":
                continue
            addrs.append(addr)
            if addr not in nodes:
                nodes[addr] = {
                    "address": addr,
                    "name": d.get("name", "Inconnu"),
                    "vendor": d.get("vendor", "Unknown"),
                    "profile": d.get("profile", "general_ble"),
                }

        for a, b in combinations(sorted(set(addrs)), 2):
            edges[(a, b)] += 1

    hot_edges = []
    for (a, b), w in edges.items():
        if w >= min_weight:
            hot_edges.append({
                "a": a,
                "b": b,
                "weight": w,
                "a_name": nodes.get(a, {}).get("name", "Inconnu"),
                "b_name": nodes.get(b, {}).get("name", "Inconnu"),
            })

    hot_edges.sort(key=lambda x: x["weight"], reverse=True)
    return {
        "nodes": nodes,
        "edges": hot_edges,
    }


def hot_edges(history=None, limit: int = 20, min_weight: int = 2):
    graph = build_copresence_graph(history, min_weight=min_weight)
    return graph["edges"][:limit]


def neighbors_for_address(address: str, history=None, limit: int = 20, min_weight: int = 1):
    graph = build_copresence_graph(history, min_weight=min_weight)
    addr = str(address or "").upper().strip()

    out = []
    for edge in graph["edges"]:
        if edge["a"] == addr:
            out.append({
                "address": edge["b"],
                "name": graph["nodes"].get(edge["b"], {}).get("name", "Inconnu"),
                "weight": edge["weight"],
            })
        elif edge["b"] == addr:
            out.append({
                "address": edge["a"],
                "name": graph["nodes"].get(edge["a"], {}).get("name", "Inconnu"),
                "weight": edge["weight"],
            })

    out.sort(key=lambda x: x["weight"], reverse=True)
    return out[:limit]


def vendor_profile_clusters(devices: list[dict], history=None, limit: int = 15):
    ranked = rank_priority(devices, history, 200)
    groups = {}

    for row in ranked:
        d = row["device"]
        vendor = d.get("vendor", "Unknown")
        profile = d.get("profile", "general_ble")
        key = f"{vendor} | {profile}"

        grp = groups.setdefault(key, {
            "key": key,
            "vendor": vendor,
            "profile": profile,
            "count": 0,
            "max_priority": 0,
            "avg_priority_sum": 0,
            "watch_hits": 0,
            "critical_like": 0,
            "devices": [],
        })

        grp["count"] += 1
        grp["max_priority"] = max(grp["max_priority"], row["priority_score"])
        grp["avg_priority_sum"] += row["priority_score"]
        if d.get("watch_hit"):
            grp["watch_hits"] += 1
        if d.get("alert_level") in ("élevé", "critique"):
            grp["critical_like"] += 1
        grp["devices"].append({
            "name": d.get("name", "Inconnu"),
            "address": d.get("address", "-"),
            "priority": row["priority_score"],
            "trust": row["trust_label"],
        })

    out = []
    for grp in groups.values():
        grp["avg_priority"] = round(grp["avg_priority_sum"] / max(1, grp["count"]), 2)
        del grp["avg_priority_sum"]
        out.append(grp)

    out.sort(
        key=lambda g: (
            g["count"],
            g["watch_hits"],
            g["critical_like"],
            g["max_priority"],
        ),
        reverse=True,
    )
    return out[:limit]


def risk_groups(devices: list[dict], history=None, limit: int = 12):
    ranked = rank_priority(devices, history, 200)

    buckets = {
        "critical_targets": [],
        "suspicious_cluster": [],
        "tracker_cluster": [],
        "known_noise": [],
    }

    for row in ranked:
        d = row["device"]
        trust = row["trust_label"]
        pr = row["priority_score"]

        if trust == "critical" or pr >= 85 or d.get("watch_hit"):
            buckets["critical_targets"].append(row)
        elif trust == "suspicious" or pr >= 60:
            buckets["suspicious_cluster"].append(row)
        elif d.get("profile") == "tracker_probable" or d.get("possible_suivi"):
            buckets["tracker_cluster"].append(row)
        elif trust in ("friendly", "known"):
            buckets["known_noise"].append(row)

    groups = []
    for key, rows in buckets.items():
        if not rows:
            continue
        groups.append({
            "key": key,
            "count": len(rows),
            "top_priority": rows[0]["priority_score"] if rows else 0,
            "rows": rows[:8],
        })

    groups.sort(key=lambda g: (g["count"], g["top_priority"]), reverse=True)
    return groups[:limit]


def atlas_snapshot(devices: list[dict], history=None):
    if history is None:
        history = load_scan_history()

    return {
        "hot_edges": hot_edges(history, 8, 2),
        "clusters": vendor_profile_clusters(devices, history, 8),
        "risk_groups": risk_groups(devices, history, 8),
    }
