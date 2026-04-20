"""Unit tests for operator outcome learning / historical effectiveness feedback."""

from ble_radar.history.operator_outcome_learning import (
    build_operator_outcome_learning_records,
    summarize_operator_outcome_learning,
)


def test_build_operator_outcome_learning_records_required_fields():
    quality_records = [
        {
            "quality_id": "quality-device-d1",
            "scope_type": "device",
            "scope_id": "d1",
            "lineage_id": "lineage-device-d1",
            "resolution_quality": "mostly_stable",
            "stability_score": 62,
        }
    ]

    learning = build_operator_outcome_learning_records(
        learning_scopes=[{"scope_type": "device", "scope_id": "d1"}],
        resolution_quality_records=quality_records,
        improvement_plans=[
            {
                "scope_type": "device",
                "scope_id": "d1",
                "expected_stability_gain": 18,
                "recommended_actions": ["collect_additional_supporting_evidence"],
            }
        ],
        lifecycle_lineage=[
            {
                "lineage_id": "lineage-device-d1",
                "scope_type": "device",
                "scope_id": "d1",
                "reopened_count": 1,
            }
        ],
        operator_outcomes=[
            {
                "scope_type": "device",
                "scope_id": "d1",
                "outcome_label": "resolved_cleanly",
                "effectiveness": 82,
                "reopened": False,
            }
        ],
        reopen_policy_records=[
            {
                "scope_type": "device",
                "scope_id": "d1",
            }
        ],
        recommendation_tuning=[
            {
                "scope_type": "device",
                "scope_id": "d1",
                "confidence_level": "high",
            }
        ],
    )

    assert len(learning) == 1
    row = learning[0]

    required_fields = {
        "learning_id",
        "scope_type",
        "scope_id",
        "quality_id",
        "lineage_id",
        "action_pattern",
        "observed_outcome",
        "stability_delta",
        "reopen_delta",
        "confidence_level",
        "learning_summary",
        "recommended_reuse",
        "caution_flags",
        "updated_at",
    }

    for field in required_fields:
        assert field in row

    assert row["confidence_level"] in {"high", "medium", "low"}
    assert isinstance(row["stability_delta"], int)
    assert isinstance(row["reopen_delta"], int)
    assert isinstance(row["caution_flags"], list)
    assert row["learning_type"] in {
        "high_value_action_pattern",
        "mixed_result_pattern",
        "fragile_followup_pattern",
        "reopen_reduction_pattern",
        "needs_more_history",
    }


def test_build_operator_outcome_learning_records_supports_all_scope_types():
    scope_types = ["device", "case", "cluster", "campaign", "evidence_pack", "queue_item"]
    quality_records = []
    learning_scopes = []
    for index, scope_type in enumerate(scope_types, start=1):
        scope_id = f"{scope_type}-{index}"
        learning_scopes.append({"scope_type": scope_type, "scope_id": scope_id})
        quality_records.append(
            {
                "quality_id": f"quality-{scope_type}-{scope_id}",
                "scope_type": scope_type,
                "scope_id": scope_id,
                "lineage_id": f"lineage-{scope_type}-{scope_id}",
                "resolution_quality": "fragile" if scope_type in {"cluster", "campaign"} else "mostly_stable",
                "stability_score": 56,
            }
        )

    rows = build_operator_outcome_learning_records(
        learning_scopes=learning_scopes,
        resolution_quality_records=quality_records,
    )

    assert len(rows) == 6
    assert {r["scope_type"] for r in rows} == set(scope_types)


def test_summarize_operator_outcome_learning_sections_exist():
    rows = [
        {
            "learning_id": "learning-device-d1",
            "scope_type": "device",
            "scope_id": "d1",
            "quality_id": "quality-device-d1",
            "lineage_id": "lineage-device-d1",
            "action_pattern": "collect_additional_supporting_evidence",
            "observed_outcome": "stabilized_after_action",
            "stability_delta": 18,
            "reopen_delta": -1,
            "confidence_level": "high",
            "learning_summary": "summary",
            "recommended_reuse": "reuse_with_similar_scope",
            "caution_flags": [],
            "learning_type": "high_value_action_pattern",
            "updated_at": "2026-04-19 12:00:00",
        },
        {
            "learning_id": "learning-case-c1",
            "scope_type": "case",
            "scope_id": "c1",
            "quality_id": "quality-case-c1",
            "lineage_id": "lineage-case-c1",
            "action_pattern": "review_closure_decision_logic",
            "observed_outcome": "mixed_with_reopen",
            "stability_delta": 5,
            "reopen_delta": 1,
            "confidence_level": "medium",
            "learning_summary": "summary",
            "recommended_reuse": "reuse_with_operator_review",
            "caution_flags": ["fragile_resolution_quality"],
            "learning_type": "mixed_result_pattern",
            "updated_at": "2026-04-19 12:00:00",
        },
    ]

    summary = summarize_operator_outcome_learning(rows)

    assert "outcome_learning" in summary
    assert "high_value_action_patterns" in summary
    assert "reopen_reduction_signals" in summary
    assert "mixed_result_patterns" in summary
    assert "recommended_reuse" in summary
