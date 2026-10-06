from agent.infrastructure.windows_named_pipe import (
    PipePeerAuthenticationError,
    _single_control_principal,
    win32_error_details,
)


def test_win32_authentication_failure_exposes_code_without_error_message():
    error = OSError(1314, "sensitive or platform-specific detail")

    assert win32_error_details(error) == {
        "win32_error_code": 1314,
        "win32_error_name": "ERROR_PRIVILEGE_NOT_HELD",
    }


def test_unknown_win32_error_keeps_numeric_code_and_generic_name():
    error = OSError(987654, "not returned")

    assert win32_error_details(error) == {
        "win32_error_code": 987654,
        "win32_error_name": "WIN32_ERROR_UNKNOWN",
    }


def test_non_win32_error_has_no_diagnostic_details():
    assert win32_error_details(ValueError("invalid")) == {}


def test_peer_authentication_diagnostic_names_the_failed_win32_stage():
    error = PipePeerAuthenticationError("process_id_to_session_id", 5)

    assert win32_error_details(error) == {
        "win32_error_code": 5,
        "win32_error_name": "ERROR_ACCESS_DENIED",
        "auth_stage": "process_id_to_session_id",
    }


def test_pipe_server_requires_one_configured_control_principal():
    assert _single_control_principal((r"HOST\AgentService",)) == r"HOST\AgentService"

    try:
        _single_control_principal((r"HOST\AgentService", r"HOST\MT5RuntimeUser"))
    except ValueError as exc:
        assert str(exc) == "PIPE_SERVER_REQUIRES_EXACTLY_ONE_CONTROL_PRINCIPAL"
    else:
        raise AssertionError("multiple pipe principals must not create a server")
