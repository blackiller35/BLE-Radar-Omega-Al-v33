"""Tests for lightweight evidence pack / operator dossier system (step 18)."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_evidence_log(tmp_path, monkeypatch):
    import ble_radar.history.operator_evidence_pack as ep
    monkeypatch.setattr(ep, "EVIDENCE_PACK_LOG_FILE", tmp_path / "operator_evidence_packs.json")


def _mod():
    import ble_radar.history.operator_evidence_pack as m
    return m


def test_build_evidence_packs_returns_expected_scopes_and_fields():
    m = _mod()

    packs = m.build_evidence_packs(
        focus_address="AA:BB:CC:DD:EE:01",
        watch_cases={"AA:BB:CC:DD:EE:01": {"status": "investigating"}},
        investigation_profile={
            "address": "AA:BB:CC:DD:EE:01",
            "triage": {"triage_score": 64, "triage_bucket": "critical"},
            "case": {"status": "investigating"},
        },
        workflow_summary={"needs_action": [{"address": "AA:BB:CC:DD:EE:01"}]},
        timeline_events=[{"source": "triage", "summary": "critical spike"}],
        playbook_recommendations=[
            {
                "address": "AA:BB:CC:DD:EE:01",
                "playbook_id": "pb-critical-pack",
                "recommended_action": "Escalate",
            }
        ],
        rule_summary={"auto_applied": [{"rule_id": "x"}], "pending_confirmations": []},
        briefing={"top_priorities": [{"address": "AA:BB:CC:DD:EE:01"}]},
        alerts=[{"device_address": "AA:BB:CC:DD:EE:01", "severity": "critical"}],
        clusters=[
            {
                "cluster_id": "cluster-aabb-2",
                "member_addresses": ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"],
                "member_count": 2,
                "reason_summary": "shared signals",
                "risk_level": "high",
                "top_signals": ["triage bucket proximity"],
                "recommended_followup": "Review cluster",
            }
        ],
        campaigns=[
            {
                "campaign_id": "campaign-aabb",
                "member_addresses": ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"],
                "member_count": 2,
                "status": "recurring",
                "first_seen": "2026-04-18_10-00-00",
                "last_seen": "2026-04-18_10-30-00",
                "activity_trend": "flat",
                "risk_level": "high",
                "reason_summary": "-",
                "recommended_followup": "Review campaign",
            }
        ],
        artifact_index={
            "scan_manifests": {"latest": "scan_manifest_a"},
            "session_diff_reports": {"latest": "session_diff_a"},
            "export_contexts": {"latest": "export_ctx_a"},
            "incident_packs": {"latest": "incident_pack_a"},
        },
        generated_at="2026-04-18_16-00-00",
        persist=True,
    )

    assert len(packs) == 4
    scopes = {p["scope_type"] for p in packs}
    assert scopes == {"device", "case", "cluster", "campaign"}

    required = {
        "pack_id",
        "scope_type",
        "scope_id",
        "generated_at",
        "summary",
        "key_findings",
        "risk_level",
        "timeline_highlights",
        "alerts_summary",
        "recommended_followup",
        "included_artifacts",
    }
    for p in packs:
        assert required.issubset(set(p.keys()))

    persisted = m.load_evidence_packs()
    assert len(persisted) >= 4


def test_summarize_evidence_packs_sections():
    m = _mod()
    summary = m.summarize_evidence_packs(
        packs=[
            {
                "pack_id": "pack-1",
                "scope_type": "campaign",
                "scope_id": "campaign-a",
                "generated_at": "2026-04-18_16-00-00",
                "summary": "Campaign dossier",
                "key_findings": ["k1"],
                "risk_level": "high",
                "timeline_highlights": [],
                "alerts_summary": "critical=1",
                "recommended_followup": "Review",
                "included_artifacts": [],
            }
        ],
        persisted_packs=[],
    )

    assert "recent_evidence_packs" in summary
    assert "ready_for_review_dossiers" in summary
    assert "campaign_evidence_summary" in summary
    assert len(summary["campaign_evidence_summary"]) == 1
