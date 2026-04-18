"""Tests for lightweight operator queue health / aging / bottleneck system (step 20)."""
from __future__ import annotations

from ble_radar.history.operator_queue_health import build_queue_health_snapshot, summarize_queue_health


def test_build_queue_health_snapshot_returns_required_fields_and_aging():
    queue_items = [
        {
            "item_id": "q-device-aabb",
            "scope_type": "device",
            "scope_id": "AA:BB:CC:DD:EE:01",
            "queue_state": "ready",
            "priority": "high",
            "owner_hint": "Operator",
            "reason_summary": "triage high",
            "recommended_action": "Review",
            "blocking_factors": [],
            "created_at": "2026-04-18 10:00:00",
            "updated_at": "2026-04-18 10:00:00",
        },
        {
            "item_id": "q-case-aabb",
            "scope_type": "case",
            "scope_id": "AA:BB:CC:DD:EE:01",
            "queue_state": "blocked",
            "priority": "critical",
            "owner_hint": "Senior Operator",
            "reason_summary": "pending confirmations",
            "recommended_action": "Resolve blocker",
            "blocking_factors": ["2 pending confirmations"],
            "created_at": "2026-04-18 01:00:00",
            "updated_at": "2026-04-18 01:00:00",
        },
    ]

    snapshot = build_queue_health_snapshot(
        queue_items,
        workflow_summary={"needs_action": [{"address": "AA:BB:CC:DD:EE:01"}]},
        pending_confirmations=[{"address": "AA:BB:CC:DD:EE:01"}],
        alerts=[{"device_address": "AA:BB:CC:DD:EE:01", "severity": "critical"}],
        campaigns=[{"status": "expanding"}],
        evidence_packs=[{"risk_level": "high"}],
        generated_at="2026-04-18 12:00:00",
    )

    required = {
        "snapshot_id",
        "generated_at",
        "total_items",
        "ready_count",
        "blocked_count",
        "in_review_count",
        "aging_buckets",
        "stale_items",
        "bottleneck_reasons",
        "queue_pressure",
        "recommended_followup",
    }
    assert required.issubset(set(snapshot.keys()))
    assert snapshot["total_items"] == 2
    assert snapshot["blocked_count"] == 1
    assert snapshot["aging_buckets"]["stale"] >= 1
    assert snapshot["queue_pressure"] in {"low", "medium", "high", "critical"}


def test_summarize_queue_health_returns_dashboard_sections():
    queue_items = [
        {
            "item_id": "q-device-aabb",
            "scope_type": "device",
            "scope_id": "AA",
            "queue_state": "waiting",
            "priority": "high",
            "owner_hint": "Operator",
            "reason_summary": "x",
            "recommended_action": "y",
            "blocking_factors": ["pending"],
            "created_at": "2026-04-18 10:00:00",
            "updated_at": "2026-04-18 10:00:00",
        }
    ]
    snapshot = build_queue_health_snapshot(queue_items, generated_at="2026-04-18 18:00:00")
    summary = summarize_queue_health(snapshot, queue_items)

    assert "queue_health" in summary
    assert "aging_overview" in summary
    assert "blocked_items" in summary
    assert "stale_items" in summary
    assert "operator_pressure" in summary
