"""Focused dashboard panel test for operator outcome learning."""

from ble_radar import dashboard


def test_render_operator_outcome_learning_panel_sections_present():
    summary = {
        "outcome_learning": [
            {
                "scope_type": "device",
                "scope_id": "d1",
                "action_pattern": "collect_additional_supporting_evidence",
                "confidence_level": "high",
                "reopen_delta": -1,
                "stability_delta": 18,
                "observed_outcome": "stabilized_after_action",
                "caution_flags": [],
                "recommended_reuse": "reuse_with_similar_scope",
            }
        ],
        "high_value_action_patterns": [
            {
                "scope_type": "device",
                "scope_id": "d1",
                "action_pattern": "collect_additional_supporting_evidence",
                "confidence_level": "high",
            }
        ],
        "reopen_reduction_signals": [
            {
                "scope_type": "device",
                "scope_id": "d1",
                "reopen_delta": -1,
                "stability_delta": 18,
            }
        ],
        "mixed_result_patterns": [
            {
                "scope_type": "case",
                "scope_id": "c1",
                "observed_outcome": "mixed_with_reopen",
                "caution_flags": ["fragile_resolution_quality"],
            }
        ],
        "recommended_reuse": [
            {
                "scope_type": "device",
                "scope_id": "d1",
                "action_pattern": "collect_additional_supporting_evidence",
                "recommended_reuse": "reuse_with_similar_scope",
            }
        ],
    }

    html = dashboard.render_operator_outcome_learning_panel(summary)

    assert "Outcome learning records" in html
    assert "High value action patterns" in html
    assert "Reopen reduction signals" in html
    assert "Mixed result patterns" in html
    assert "Recommended reuse" in html
