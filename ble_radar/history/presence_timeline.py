from __future__ import annotations
from typing import Any, Dict, List


def build_presence_timeline(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    timeline: Dict[str, int] = {}
    for record in records:
        for bucket in record.get("presence_buckets", []):
            timeline[bucket] = timeline.get(bucket, 0) + 1

    ordered = sorted(timeline.items(), key=lambda x: x[0])
    return {
        "timeline": [{"bucket": bucket, "device_count": count} for bucket, count in ordered],
        "bucket_count": len(ordered),
    }


def mark_session_presence(previous_addresses: List[str], current_addresses: List[str]) -> Dict[str, Any]:
    prev = set(previous_addresses or [])
    curr = set(current_addresses or [])

    return {
        "new": sorted(curr - prev),
        "disappeared": sorted(prev - curr),
        "reappeared_hint": [],
        "stable": sorted(curr & prev),
    }
