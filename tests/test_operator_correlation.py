"""Tests for lightweight operator correlation cluster system (step 16)."""
from __future__ import annotations

from ble_radar.history.operator_correlation import build_correlation_clusters, summarize_clusters


def test_build_correlation_clusters_returns_compact_cluster_fields():
    devices = [
        {"address": "AA:BB:CC:DD:EE:01", "name": "Beacon-1"},
        {"address": "AA:BB:CC:DD:EE:02", "name": "Beacon-2"},
        {"address": "AA:BB:CC:DD:EE:03", "name": "Beacon-3"},
    ]
    triage_results = [
        {"address": "AA:BB:CC:DD:EE:01", "triage_score": 62, "triage_bucket": "critical"},
        {"address": "AA:BB:CC:DD:EE:02", "triage_score": 58, "triage_bucket": "critical"},
        {"address": "AA:BB:CC:DD:EE:03", "triage_score": 12, "triage_bucket": "watch"},
    ]
    movement = {
        "new": [],
        "disappeared": [],
        "recurring": [
            {"address": "AA:BB:CC:DD:EE:01"},
            {"address": "AA:BB:CC:DD:EE:02"},
            {"address": "AA:BB:CC:DD:EE:03"},
        ],
        "score_changes": [
            {"address": "AA:BB:CC:DD:EE:01", "delta": 4},
            {"address": "AA:BB:CC:DD:EE:02", "delta": 2},
        ],
    }
    workflow_summary = {
        "needs_action": [
            {"address": "AA:BB:CC:DD:EE:01"},
            {"address": "AA:BB:CC:DD:EE:02"},
        ],
        "investigating": [
            {"address": "AA:BB:CC:DD:EE:01"},
            {"address": "AA:BB:CC:DD:EE:02"},
        ],
        "open": [],
        "resolved": [],
    }
    timeline_by_address = {
        "AA:BB:CC:DD:EE:01": [{"action": "score_change"}],
        "AA:BB:CC:DD:EE:02": [{"action": "score_change"}],
    }
    playbooks = [
        {"address": "AA:BB:CC:DD:EE:01", "playbook_id": "pb-critical-pack", "priority": "critical"},
        {"address": "AA:BB:CC:DD:EE:02", "playbook_id": "pb-critical-pack", "priority": "critical"},
    ]
    alerts = [
        {"device_address": "AA:BB:CC:DD:EE:01", "severity": "critical"},
        {"device_address": "AA:BB:CC:DD:EE:02", "severity": "critical"},
    ]
    watch_cases = {
        "AA:BB:CC:DD:EE:01": {"status": "investigating"},
        "AA:BB:CC:DD:EE:02": {"status": "investigating"},
    }
    investigation_profiles = {
        "AA:BB:CC:DD:EE:01": {
            "address": "AA:BB:CC:DD:EE:01",
            "triage": {"triage_score": 62, "triage_bucket": "critical"},
            "case": {"status": "investigating"},
        }
    }

    clusters = build_correlation_clusters(
        devices,
        movement=movement,
        triage_results=triage_results,
        investigation_profiles=investigation_profiles,
        watch_cases=watch_cases,
        workflow_summary=workflow_summary,
        timeline_by_address=timeline_by_address,
        playbook_recommendations=playbooks,
        alerts=alerts,
    )

    assert clusters
    c = clusters[0]
    for key in (
        "cluster_id",
        "member_addresses",
        "member_count",
        "reason_summary",
        "risk_level",
        "top_signals",
        "recommended_followup",
    ):
        assert key in c
    assert c["member_count"] >= 2


def test_build_correlation_clusters_returns_empty_when_no_meaningful_overlap():
    devices = [
        {"address": "AA:BB:CC:DD:EE:01", "name": "Beacon-1"},
        {"address": "AA:BB:CC:DD:EE:02", "name": "Beacon-2"},
    ]
    triage_results = [
        {"address": "AA:BB:CC:DD:EE:01", "triage_score": 60, "triage_bucket": "critical"},
        {"address": "AA:BB:CC:DD:EE:02", "triage_score": 5, "triage_bucket": "normal"},
    ]
    movement = {
        "new": [{"address": "AA:BB:CC:DD:EE:01"}],
        "disappeared": [{"address": "AA:BB:CC:DD:EE:02"}],
        "recurring": [],
        "score_changes": [],
    }

    clusters = build_correlation_clusters(
        devices,
        movement=movement,
        triage_results=triage_results,
        workflow_summary={"open": [], "investigating": [], "needs_action": [], "resolved": []},
    )

    assert clusters == []


def test_summarize_clusters_returns_expected_sections():
    summary = summarize_clusters(
        [
            {
                "cluster_id": "cluster-aa-2",
                "member_addresses": ["AA", "BB"],
                "member_count": 2,
                "reason_summary": "triage bucket proximity",
                "risk_level": "high",
                "top_signals": ["triage bucket proximity"],
                "recommended_followup": "Review",
            }
        ]
    )

    assert "top_correlation_clusters" in summary
    assert "possible_coordinated_devices" in summary
    assert "needs_cluster_review" in summary
    assert len(summary["top_correlation_clusters"]) == 1
