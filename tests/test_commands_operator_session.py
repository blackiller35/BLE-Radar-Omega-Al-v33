from ble_radar.commands import parse_command


def test_parse_command_operator_session_unlock_action():
    assert parse_command("session unlock")["action"] == "operator_session_unlock"
    assert parse_command("opunlock")["action"] == "operator_session_unlock"


def test_parse_command_operator_session_lock_action():
    assert parse_command("session lock")["action"] == "operator_session_lock"
    assert parse_command("oplock")["action"] == "operator_session_lock"


def test_parse_command_operator_session_status_action():
    assert parse_command("session status")["action"] == "operator_session_status"
    assert parse_command("opstatus")["action"] == "operator_session_status"
