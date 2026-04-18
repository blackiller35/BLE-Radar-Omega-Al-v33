"""Tests for lightweight operator session journal / shift continuity system (step 24)."""
from __future__ import annotations

from ble_radar.history.operator_session_journal import build_operator_session_journal, summarize_operator_session_journal


def test_build_operator_session_journal_required_fields():
    journal = build_operator_session_journal(
        queue_items=[
            {
                "item_id": "q-device-aabb",
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "queue_state": "in_review",
                "created_at": "2026-04-18 10:00:00",
                "updated_at": "2026-04-18 10:10:00",
            },
            {
                "item_id": "q-campaign-aabb",
                "scope_type": "campaign",
                "scope_id": "campaign-aabb",
                "queue_state": "waiting",
                "created_at": "2026-04-18 10:05:00",
                "updated_at": "2026-04-18 10:20:00",
            },
        ],
        campaigns=[
            {
                "campaign_id": "campaign-aabb",
                "status": "expanding",
                "risk_level": "high",
            }
        ],
        alerts=[{"device_address": "AA:BB:CC:DD:EE:01", "severity": "high"}],
        outcomes=[
            {
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "outcome_label": "resolved_cleanly",
                "created_at": "2026-04-18 10:25:00",
            }
        ],
        readiness_profiles=[
            {
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "readiness_state": "ready_for_handoff",
            }
        ],
        evidence_packs=[
            {
                "pack_id": "pack-device-aabb",
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "generated_at": "2026-04-18 10:12:00",
            }
        ],
        queue_health_snapshot={
            "queue_pressure": "high",
            "stale_items": [
                {
                    "item_id": "q-campaign-aabb",
                    "scope_type": "campaign",
                    "scope_id": "campaign-aabb",
                    "queue_state": "waiting",
                    "age_minutes": 260,
                }
            ],
        },
        generated_at="2026-04-18 18:00:00",
    )

    required = {
        "session_id",
        "started_at",
        "ended_at",
        "items_touched",
        "campaigns_updated",
        "alerts_reviewed",
        "outcomes_recorded",
        "readiness_changes",
        "handoff_summary",
        "next_shift_priorities",
    }
    assert required.issubset(set(journal.keys()))
    assert journal["items_touched"] >= 2
    assert isinstance(journal["next_shift_priorities"], list)


def test_summarize_operator_session_journal_sections_exist():
    summary = summarize_operator_session_journal(
        {
            "session_id": "opsession-a",
            "started_at": "2026-04-18 10:00:00",
            "ended_at": "2026-04-18 12:00:00",
            "items_touched": 3,
            "campaigns_updated": 1,
            "alerts_reviewed": 2,
            "outcomes_recorded": 1,
            "readiness_changes": 1,
            "handoff_summary": "ok",
            "next_shift_priorities": ["Review carry-over"],
        },
        queue_items=[
            {
                "item_id": "q-case-aabb",
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "queue_state": "waiting",
            }
        ],
        outcomes=[
            {
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "outcome_label": "resolved_cleanly",
            }
        ],
        readiness_profiles=[
            {
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "readiness_state": "ready_for_handoff",
            }
        ],
    )

    assert "current_session_journal" in summary
    assert "shift_activity" in summary
    assert "carry_over_items" in summary
    assert "next_shift_priorities" in summary
    assert "recent_handoffs" in summary
    assert len(summary["carry_over_items"]) == 1
    assert len(summary["recent_handoffs"]) >= 1
