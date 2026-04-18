"""Tests for lightweight campaign tracking / cluster lifecycle (step 17)."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_campaign_log(tmp_path, monkeypatch):
    import ble_radar.history.operator_campaign_tracking as ct
    monkeypatch.setattr(ct, "CAMPAIGN_LOG_FILE", tmp_path / "operator_campaigns.json")


def _mod():
    import ble_radar.history.operator_campaign_tracking as m
    return m


def test_build_campaign_lifecycle_new_campaign_contains_required_fields():
    m = _mod()
    clusters = [
        {
            "cluster_id": "cluster-aabb-2",
            "member_addresses": ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"],
            "member_count": 2,
            "reason_summary": "triage bucket proximity | alert similarity",
            "risk_level": "high",
            "top_signals": ["triage bucket proximity", "operator alert similarity"],
            "recommended_followup": "Review campaign continuity",
        }
    ]

    rows = m.build_campaign_lifecycle(clusters, previous_campaigns=[], stamp="2026-04-18_14-00-00", persist=True)
    assert rows
    c = rows[0]

    for key in (
        "campaign_id",
        "member_addresses",
        "member_count",
        "status",
        "first_seen",
        "last_seen",
        "activity_trend",
        "risk_level",
        "reason_summary",
        "recommended_followup",
    ):
        assert key in c

    assert c["status"] == "new"
    assert m.load_campaign_records()


def test_build_campaign_lifecycle_matches_previous_and_closes_unmatched():
    m = _mod()
    previous = [
        {
            "campaign_id": "campaign-aa-prev",
            "member_addresses": ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"],
            "member_count": 2,
            "status": "recurring",
            "first_seen": "2026-04-17_10-00-00",
            "last_seen": "2026-04-17_10-00-00",
            "activity_trend": "flat",
            "risk_level": "high",
            "reason_summary": "-",
            "recommended_followup": "-",
            "top_signals": ["operator timeline proximity", "operator alert similarity", "playbook similarity"],
        },
        {
            "campaign_id": "campaign-zz-prev",
            "member_addresses": ["ZZ:ZZ:ZZ:ZZ:ZZ:01", "ZZ:ZZ:ZZ:ZZ:ZZ:02"],
            "member_count": 2,
            "status": "stable",
            "first_seen": "2026-04-17_09-00-00",
            "last_seen": "2026-04-17_09-00-00",
            "activity_trend": "flat",
            "risk_level": "medium",
            "reason_summary": "-",
            "recommended_followup": "-",
            "top_signals": ["session movement overlap"],
        },
    ]

    clusters = [
        {
            "cluster_id": "cluster-aabb-3",
            "member_addresses": ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02", "AA:BB:CC:DD:EE:03"],
            "member_count": 3,
            "reason_summary": "timeline | alert | playbook",
            "risk_level": "high",
            "top_signals": ["operator timeline proximity", "operator alert similarity", "playbook similarity"],
            "recommended_followup": "Review campaign continuity",
        }
    ]

    rows = m.build_campaign_lifecycle(clusters, previous_campaigns=previous, stamp="2026-04-18_15-00-00", persist=False)

    active = [r for r in rows if r["campaign_id"] == "campaign-aa-prev"][0]
    assert active["status"] == "expanding"
    assert active["first_seen"] == "2026-04-17_10-00-00"

    closed = [r for r in rows if r["campaign_id"] == "campaign-zz-prev"][0]
    assert closed["status"] == "closed"


def test_summarize_campaigns_sections():
    m = _mod()
    summary = m.summarize_campaigns(
        [
            {
                "campaign_id": "campaign-aa",
                "member_addresses": ["AA", "BB"],
                "member_count": 2,
                "status": "recurring",
                "first_seen": "2026-04-17_10-00-00",
                "last_seen": "2026-04-18_10-00-00",
                "activity_trend": "flat",
                "risk_level": "high",
                "reason_summary": "x",
                "recommended_followup": "y",
            }
        ]
    )

    assert "active_campaigns" in summary
    assert "recurring_clusters" in summary
    assert "expanding_groups" in summary
    assert "needs_campaign_review" in summary
    assert len(summary["active_campaigns"]) == 1
