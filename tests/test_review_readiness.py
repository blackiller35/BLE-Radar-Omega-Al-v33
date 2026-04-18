"""Tests for lightweight review readiness / readiness gate system (step 23)."""
from __future__ import annotations

from ble_radar.history.review_readiness import build_review_readiness_profiles, summarize_review_readiness


def test_build_review_readiness_profiles_required_fields_and_scope_support():
    queue_items = [
        {
            "item_id": "q-device-aabb",
            "scope_type": "device",
            "scope_id": "AA:BB:CC:DD:EE:01",
            "queue_state": "in_review",
            "created_at": "2026-04-18 10:00:00",
            "updated_at": "2026-04-18 10:00:00",
        },
        {
            "item_id": "q-case-aabb",
            "scope_type": "case",
            "scope_id": "AA:BB:CC:DD:EE:01",
            "queue_state": "waiting",
            "created_at": "2026-04-18 10:05:00",
            "updated_at": "2026-04-18 10:05:00",
        },
        {
            "item_id": "q-cluster-a",
            "scope_type": "cluster",
            "scope_id": "cluster-aabb-2",
            "queue_state": "ready",
            "created_at": "2026-04-18 10:10:00",
            "updated_at": "2026-04-18 10:10:00",
        },
        {
            "item_id": "q-campaign-a",
            "scope_type": "campaign",
            "scope_id": "campaign-aabb",
            "queue_state": "in_review",
            "created_at": "2026-04-18 10:15:00",
            "updated_at": "2026-04-18 10:15:00",
        },
        {
            "item_id": "q-pack-a",
            "scope_type": "evidence_pack",
            "scope_id": "pack-device-aabb",
            "queue_state": "resolved",
            "created_at": "2026-04-18 10:20:00",
            "updated_at": "2026-04-18 10:20:00",
        },
    ]

    rows = build_review_readiness_profiles(
        queue_items,
        evidence_packs=[
            {
                "pack_id": "pack-device-aabb",
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "risk_level": "medium",
            }
        ],
        queue_health_snapshot={
            "queue_pressure": "medium",
            "stale_items": [
                {
                    "item_id": "q-case-aabb",
                    "scope_type": "case",
                    "scope_id": "AA:BB:CC:DD:EE:01",
                    "queue_state": "waiting",
                    "age_minutes": 300,
                }
            ],
        },
        outcomes=[
            {
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "outcome_label": "resolved_cleanly",
            },
            {
                "scope_type": "campaign",
                "scope_id": "campaign-aabb",
                "outcome_label": "stabilized",
            },
        ],
        alerts=[{"device_address": "AA:BB:CC:DD:EE:01", "severity": "low"}],
        timeline_events=[{"source": "triage", "summary": "context"}],
        campaigns=[{"campaign_id": "campaign-aabb", "status": "stable", "risk_level": "medium"}],
        workflow_summary={"resolved": [{"address": "AA:BB:CC:DD:EE:01", "status": "resolved"}]},
        investigation_profile={"triage": {"triage_score": 35}},
        generated_at="2026-04-18 18:00:00",
    )

    assert rows
    scope_types = {r["scope_type"] for r in rows}
    assert {"device", "case", "cluster", "campaign", "evidence_pack", "queue_item"}.issubset(scope_types)

    required = {
        "review_id",
        "scope_type",
        "scope_id",
        "readiness_state",
        "readiness_score",
        "missing_elements",
        "strengths",
        "review_notes",
        "recommended_disposition",
    }
    for row in rows:
        assert required.issubset(set(row.keys()))

    states = {r["readiness_state"] for r in rows}
    assert states.issubset(
        {
            "not_ready",
            "needs_more_data",
            "ready_for_review",
            "ready_for_handoff",
            "ready_for_archive",
        }
    )


def test_summarize_review_readiness_sections_exist():
    summary = summarize_review_readiness(
        [
            {
                "review_id": "review-device-aabb",
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "readiness_state": "ready_for_review",
                "readiness_score": 68,
                "missing_elements": [],
                "strengths": ["evidence_pack_available"],
                "review_notes": "ok",
                "recommended_disposition": "review",
            },
            {
                "review_id": "review-case-aabb",
                "scope_type": "case",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "readiness_state": "needs_more_data",
                "readiness_score": 41,
                "missing_elements": ["evidence_pack"],
                "strengths": [],
                "review_notes": "need evidence",
                "recommended_disposition": "collect_more_evidence",
            },
            {
                "review_id": "review-campaign-aabb",
                "scope_type": "campaign",
                "scope_id": "campaign-aabb",
                "readiness_state": "ready_for_handoff",
                "readiness_score": 79,
                "missing_elements": [],
                "strengths": ["campaign_status=stable"],
                "review_notes": "handoff",
                "recommended_disposition": "handoff",
            },
            {
                "review_id": "review-pack-aabb",
                "scope_type": "evidence_pack",
                "scope_id": "pack-device-aabb",
                "readiness_state": "ready_for_archive",
                "readiness_score": 89,
                "missing_elements": [],
                "strengths": ["resolved"],
                "review_notes": "archive",
                "recommended_disposition": "archive",
            },
        ]
    )

    assert "review_readiness" in summary
    assert "ready_for_review" in summary
    assert "needs_more_evidence" in summary
    assert "ready_for_handoff" in summary
    assert "ready_for_archive" in summary
    assert len(summary["ready_for_review"]) == 1
    assert len(summary["needs_more_evidence"]) == 1
    assert len(summary["ready_for_handoff"]) == 1
    assert len(summary["ready_for_archive"]) == 1
