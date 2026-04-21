from ble_radar.operator_profiles import (
    DEFAULT_OPERATOR_PROFILE,
    get_operator_profile,
    list_operator_profiles,
    profile_summary_lines,
    resolve_operator_profile,
)


def test_list_operator_profiles_contains_expected_profiles():
    profiles = list_operator_profiles()
    assert "balanced" in profiles
    assert "stealth" in profiles
    assert "aggressive" in profiles
    assert "audit" in profiles


def test_get_operator_profile_returns_default_for_unknown():
    profile = get_operator_profile("unknown")
    assert profile["name"] == DEFAULT_OPERATOR_PROFILE
    assert profile["label"] == "Balanced"


def test_resolve_operator_profile_normalizes_known_profile():
    assert resolve_operator_profile("Aggressive") == "aggressive"


def test_profile_summary_lines_contains_label():
    lines = profile_summary_lines("audit")
    assert any("Audit" in line for line in lines)
