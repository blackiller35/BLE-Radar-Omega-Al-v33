"""Tests for lightweight operator pattern library / recurring case memory (step 25)."""
from __future__ import annotations

from ble_radar.history.operator_pattern_library import (
    build_operator_pattern_records,
    match_scopes_to_patterns,
    summarize_operator_pattern_library,
)


def test_build_operator_pattern_records_required_fields():
    patterns = build_operator_pattern_records(
        outcomes=[
            {
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "outcome_label": "resolved_cleanly",
                "effectiveness": 82,
                "source_action": "escalate_incident_pack",
                "source_playbook": "pb-critical-pack",
                "created_at": "2026-04-18 19:00:00",
            }
        ],
        recommendation_profiles=[
            {
                "scope_id": "AA:BB:CC:DD:EE:01",
                "source_playbook": "pb-critical-pack",
                "confidence_level": "high",
            }
        ],
        alerts=[{"device_address": "AA:BB:CC:DD:EE:01", "severity": "high"}],
        campaigns=[{"campaign_id": "campaign-aabb", "status": "expanding"}],
        clusters=[{"cluster_id": "cluster-aabb"}],
        queue_items=[
            {
                "item_id": "q-device-aabb",
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "queue_state": "in_review",
                "updated_at": "2026-04-18 19:01:00",
            }
        ],
        readiness_profiles=[
            {
                "scope_type": "device",
                "scope_id": "AA:BB:CC:DD:EE:01",
                "readiness_state": "ready_for_handoff",
            }
        ],
        session_journal={
            "items_touched": 4,
            "campaigns_updated": 1,
            "alerts_reviewed": 2,
        },
        generated_at="2026-04-18 19:30:00",
    )

    assert patterns
    required = {
        "pattern_id",
        "pattern_type",
        "title",
        "match_signals",
        "risk_profile",
        "common_outcomes",
        "recommended_playbooks",
        "known_pitfalls",
        "confidence_level",
        "last_seen",
    }
    assert required.issubset(set(patterns[0].keys()))


def test_match_and_summarize_operator_pattern_library():
    patterns = [
        {
            "pattern_id": "pattern-device-aabbccddee01",
            "pattern_type": "device",
            "title": "Recurring device pattern",
            "match_signals": ["queue:in_review", "readiness:ready_for_handoff"],
            "risk_profile": "medium",
            "common_outcomes": ["resolved_cleanly"],
            "recommended_playbooks": ["pb-critical-pack"],
            "known_pitfalls": ["none"],
            "confidence_level": "high",
            "last_seen": "2026-04-18 19:00:00",
        }
    ]
    matches = match_scopes_to_patterns(
        [
            {
                "scope_type": "device",
                "scope_id": "aabbccddee01",
                "queue_state": "in_review",
            }
        ],
        patterns,
    )

    assert matches
    assert matches[0]["pattern_id"] == "pattern-device-aabbccddee01"

    summary = summarize_operator_pattern_library(patterns, matches=matches)
    assert "known_patterns" in summary
    assert "recurring_case_types" in summary
    assert "likely_matches" in summary
    assert "pattern_based_guidance" in summary
