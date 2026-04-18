"""Tests for lightweight operator queue / case board system (step 19)."""
from __future__ import annotations

from ble_radar.history.operator_queue import build_operator_queue, summarize_operator_queue


def test_build_operator_queue_contains_all_scope_types():
    rows = build_operator_queue(
        triage_results=[
            {"address": "AA:BB:CC:DD:EE:01", "triage_score": 70, "triage_bucket": "critical"},
            {"address": "AA:BB:CC:DD:EE:02", "triage_score": 55, "triage_bucket": "review"},
        ],
        workflow_summary={
            "needs_action": [{"address": "AA:BB:CC:DD:EE:01", "status": "review"}],
            "investigating": [{"address": "AA:BB:CC:DD:EE:02", "status": "investigating"}],
        },
        pending_confirmations=[{"address": "AA:BB:CC:DD:EE:01"}],
        alerts=[{"device_address": "AA:BB:CC:DD:EE:01", "severity": "critical"}],
        briefing={"suggested_next_steps": ["Review pending confirmation"]},
        clusters=[
            {
                "cluster_id": "cluster-aabb-2",
                "member_addresses": ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"],
                "member_count": 2,
                "risk_level": "high",
                "reason_summary": "shared triage",
                "recommended_followup": "Review cluster",
            }
        ],
        campaigns=[
            {
                "campaign_id": "campaign-aabb",
                "member_addresses": ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"],
                "member_count": 2,
                "status": "expanding",
                "activity_trend": "up",
                "risk_level": "high",
                "recommended_followup": "Review campaign",
            }
        ],
        evidence_packs=[
            {
                "pack_id": "pack-device-aabb",
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "summary": "Device dossier",
                "risk_level": "high",
                "recommended_followup": "Review pack",
                "generated_at": "2026-04-18_17-00-00",
            }
        ],
        watch_cases={"AA:BB:CC:DD:EE:01": {"status": "review"}},
        stamp="2026-04-18_17-30-00",
    )

    assert rows
    scope_types = {r["scope_type"] for r in rows}
    assert {"device", "case", "cluster", "campaign", "evidence_pack"}.issubset(scope_types)

    required = {
        "item_id",
        "scope_type",
        "scope_id",
        "queue_state",
        "priority",
        "owner_hint",
        "reason_summary",
        "recommended_action",
        "blocking_factors",
        "created_at",
        "updated_at",
    }
    for row in rows:
        assert required.issubset(set(row.keys()))


def test_summarize_operator_queue_sections_exist():
    summary = summarize_operator_queue(
        [
            {
                "item_id": "q-device-aabb",
                "scope_type": "device",
                "scope_id": "AA:BB",
                "queue_state": "ready",
                "priority": "high",
                "owner_hint": "Operator",
                "reason_summary": "x",
                "recommended_action": "y",
                "blocking_factors": [],
                "created_at": "2026-04-18_17-00-00",
                "updated_at": "2026-04-18_17-30-00",
            }
        ]
    )

    assert "operator_queue" in summary
    assert "needs_review" in summary
    assert "blocked_items" in summary
    assert "ready_now" in summary
    assert "recently_resolved" in summary
    assert len(summary["ready_now"]) == 1
