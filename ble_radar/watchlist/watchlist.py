from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List


def load_watchlist(path: str = "data/watchlist/watchlist.json") -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def match_watchlist(device: Dict[str, Any], watchlist: List[Dict[str, Any]]) -> Dict[str, Any]:
    address = (device.get("address") or "").lower()
    name = (device.get("name") or "").lower()
    vendor = (device.get("vendor") or "").lower()

    for rule in watchlist:
        rule_address = (rule.get("address") or "").lower()
        rule_name = (rule.get("name") or "").lower()
        rule_vendor = (rule.get("vendor") or "").lower()

        if rule_address and rule_address == address:
            return {"matched": True, "reason": rule.get("reason", "address match")}
        if rule_name and rule_name in name:
            return {"matched": True, "reason": rule.get("reason", "name match")}
        if rule_vendor and rule_vendor in vendor:
            return {"matched": True, "reason": rule.get("reason", "vendor match")}

    return {"matched": False, "reason": ""}
