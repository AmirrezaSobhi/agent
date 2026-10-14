import json
import uuid

import pytest

from agent.contracts.configuration import ConfigurationError, ManagementPipeConfig
from agent.infrastructure.environment_config import EnvironmentConfigurationProvider
from agent.infrastructure.management_named_pipe import (
    MAX_MESSAGE_BYTES,
    PIPE_NAME,
    CallerIdentityError,
    ManagementNamedPipeServer,
    ManagementProtocolError,
    build_status,
    encode_message,
    parse_request,
)


def request(operation="status.get", version=1, **extra):
    return {
        "protocol_version": version,
        "request_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
        "operation": operation,
        "payload": {},
        **extra,
    }


def test_management_protocol_has_fixed_pipe_and_bounded_frame():
    assert PIPE_NAME == r"\\.\pipe\MT5Agent.Management.v1"
    assert MAX_MESSAGE_BYTES == 65536
    body = request()
    assert parse_request(json.dumps(body).encode())["operation"] == "status.get"


def test_management_log_query_is_a_fixed_read_only_operation():
    body = request("logs.query")
    body["payload"] = {"limit": 10, "severity": "WARNING"}
    assert parse_request(json.dumps(body).encode())["operation"] == "logs.query"
    assert parse_request(json.dumps(body).encode())["payload"]["severity"] == "WARNING"


def test_management_event_buffer_is_bounded_and_contains_only_fixed_safe_fields():
    server = ManagementNamedPipeServer(lambda: {"observed_at_utc": "2026-10-08T00:00:00Z"}, ())
    for _ in range(250):
        server._record_event("INFO", "STATUS_OBSERVED", "Read-only Agent status was observed.")
    result = server._query_events({"limit": 100, "severity": "ALL"})
    assert result["count"] == 100
    assert set(result["events"][0]) == {"timestamp_utc", "severity", "source", "code", "message"}
    assert "account" not in json.dumps(result).lower()


@pytest.mark.parametrize("payload", [
    {"limit": 0, "severity": "ALL"},
    {"limit": 101, "severity": "ALL"},
    {"limit": True, "severity": "ALL"},
    {"limit": 10, "severity": "TRACE"},
])
def test_management_log_query_rejects_unbounded_or_unknown_filters(payload):
    server = ManagementNamedPipeServer(lambda: {}, ())
    with pytest.raises(ManagementProtocolError, match="INVALID_REQUEST"):
        server._query_events(payload)


@pytest.mark.parametrize("body,code", [
    (b"not-json", "INVALID_REQUEST"),
    (b"[]", "INVALID_REQUEST"),
    (json.dumps(request(version=2)).encode(), "PROTOCOL_MISMATCH"),
    (json.dumps(request("command.execute")).encode(), "UNSUPPORTED_OPERATION"),
    (json.dumps({**request(), "request_id": "bad"}).encode(), "INVALID_REQUEST"),
])
def test_invalid_requests_are_rejected(body, code):
    with pytest.raises(ManagementProtocolError) as error:
        parse_request(body)
    assert error.value.code == code


def test_oversized_request_is_rejected_before_json_parsing():
    with pytest.raises(ManagementProtocolError) as error:
        parse_request(b"x" * (MAX_MESSAGE_BYTES + 1))
    assert error.value.code == "MESSAGE_TOO_LARGE"


def test_encoding_enforces_response_limit():
    with pytest.raises(ManagementProtocolError, match="MESSAGE_TOO_LARGE"):
        encode_message({"data": "x" * MAX_MESSAGE_BYTES})


def test_default_deny_and_caller_claim_is_ignored():
    called = []
    allow = "S-1-5-21-100-200-300-1001"
    server = ManagementNamedPipeServer(lambda: called.append(True) or {"observed_at_utc": "now"}, (allow,))
    raw = json.dumps(request(claimed_sid="S-1-5-18", caller_sid="S-1-5-18")).encode()
    denied, _ = server._handle(raw, "S-1-5-21-100-200-300-1002")
    assert denied["code"] == "UNAUTHORIZED"
    assert called == []
    accepted, operation = server._handle(raw, allow)
    assert accepted["code"] == "OK"
    assert operation == "status.get"
    assert called == [True]


def test_only_protocol_negotiation_and_read_only_status_are_implemented():
    server = ManagementNamedPipeServer(lambda: {"observed_at_utc": "now"}, ("S-1-5-21-1-2-3-4",))
    negotiate, operation = server._handle(json.dumps(request("protocol.negotiate")).encode(), "S-1-5-21-1-2-3-4")
    assert operation == "protocol.negotiate"
    assert negotiate["data"]["supported_versions"] == [1]
    trading, _ = server._handle(json.dumps(request("trade.place")).encode(), "S-1-5-21-1-2-3-4")
    assert trading["code"] == "UNSUPPORTED_OPERATION"


def test_management_status_does_not_infer_worker_or_trading_readiness():
    class Health:
        state = type("State", (), {"value": "running"})()
        runtime_state = "RUNTIME_UNAVAILABLE"
        runtime = {"worker_available": False, "mt5_connected": False}

    status = build_status(type("Agent", (), {"health": lambda self: Health()})())
    assert status["service_state"] == "UNKNOWN"
    assert status["agent_state"] == "AGENT_RUNNING"
    assert status["agent_lifecycle_state"] == "RUNNING"
    assert status["worker_available"] is False
    assert status["worker_state"] == "DISCONNECTED"
    assert status["mt5_connected"] is False
    assert status["mt5_state"] == "DISCONNECTED"
    assert status["central_state"] == "NOT_CONFIGURED"
    assert status["trading_capability"] == "UNSUPPORTED"
    assert status["trading_authorized"] == "UNKNOWN"
    assert status["trading_readiness"] == "UNAVAILABLE"
    assert status["source_identity"] == "MT5Agent.AgentCore"
    assert status["agent_version"]
    assert status["management_protocol_version"] == 1
    assert status["worker_session_id"] is None
    assert status["worker_protocol_version"] is None
    assert "terminal_path" not in status and "terminal_pid" not in status
    assert status["freshness"] == "FRESH"
    assert status["observed_at_utc"].endswith("Z")


def test_management_status_does_not_fabricate_worker_or_mt5_when_health_is_missing():
    class Health:
        state = type("State", (), {"value": "starting"})()
        runtime_state = "INITIALIZING"
        runtime = None

    status = build_status(type("Agent", (), {"health": lambda self: Health()})())
    assert status["agent_state"] == "AGENT_STARTING"
    assert status["worker_available"] is None
    assert status["worker_state"] == "UNKNOWN"
    assert status["mt5_connected"] is None
    assert status["mt5_state"] == "INITIALIZING"


def test_management_status_preserves_the_worker_contract_state_after_a_live_health_response():
    class Health:
        state = type("State", (), {"value": "running"})()
        runtime_state = "MT5_CONNECTED"
        runtime = {"worker_available": True, "worker_state": "WORKER_READY", "mt5_connected": True,
                   "worker_session_id": 3, "protocol_version": "1", "last_successful_mt5_operation": "initialize",
                   "terminal_path": "C:/private/terminal.exe", "terminal_pid": 1234}

    status = build_status(type("Agent", (), {"health": lambda self: Health()})())
    assert status["worker_available"] is True
    assert status["worker_state"] == "WORKER_READY"
    assert status["mt5_state"] == "CONNECTED"
    assert status["worker_session_id"] == 3
    assert status["worker_protocol_version"] == "1"
    assert status["last_successful_mt5_operation"] == "initialize"
    assert "terminal_path" not in status and "terminal_pid" not in status


def test_management_allowlist_is_explicit_and_validated():
    config = EnvironmentConfigurationProvider({"MT5_AGENT_MANAGEMENT_ALLOWED_SIDS": " S-1-5-21-1-2-3-4, S-1-5-21-1-2-3-5 "}).load()
    assert config.management.allowed_user_sids == ("S-1-5-21-1-2-3-4", "S-1-5-21-1-2-3-5")
    assert ManagementPipeConfig().allowed_user_sids == ()
    with pytest.raises(ConfigurationError):
        ManagementPipeConfig(allowed_user_sids=("S-1-5-21-1-2-3-4", "S-1-5-21-1-2-3-4"))


def test_token_close_failure_still_restores_impersonation(monkeypatch):
    events = []

    class Api:
        @staticmethod
        def GetCurrentThread():
            return object()

        @staticmethod
        def CloseHandle(_token):
            events.append("close")
            raise OSError("injected token close failure")

    class Security:
        TokenUser = 1

        @staticmethod
        def ImpersonateNamedPipeClient(_handle):
            events.append("impersonate")

        @staticmethod
        def OpenThreadToken(*_args):
            return object()

        @staticmethod
        def GetTokenInformation(_token, _kind):
            return ("sid",)

        @staticmethod
        def ConvertSidToStringSid(_sid):
            return "S-1-5-21-1-2-3-4"

        @staticmethod
        def RevertToSelf():
            events.append("revert")

    server = ManagementNamedPipeServer(lambda: {}, ())
    monkeypatch.setattr(server, "_modules", lambda: (Api, type("Con", (), {"TOKEN_QUERY": 1}), None, None, Security))
    with pytest.raises(CallerIdentityError, match="CLIENT_TOKEN_CLOSE_FAILED"):
        server._caller_sid(object())
    assert events == ["impersonate", "close", "revert"]


@pytest.mark.skipif(__import__("os").name != "nt", reason="Windows Named Pipe integration")
def test_windows_named_pipe_derives_actual_caller_sid_and_stops_cleanly():
    import os
    import io
    import logging
    import threading
    import time
    import win32api
    import win32con
    import win32file
    import win32pipe
    import win32security

    from agent.infrastructure.management_named_pipe import ManagementNamedPipeServer

    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        caller_sid = win32security.ConvertSidToStringSid(
            win32security.GetTokenInformation(token, win32security.TokenUser)[0]
        )
    finally:
        win32api.CloseHandle(token)
    captured = []

    class CapturingServer(ManagementNamedPipeServer):
        def _handle(self, raw, actual_sid):
            captured.append(actual_sid)
            return super()._handle(raw, actual_sid)

    log_output = io.StringIO()
    test_logger = logging.getLogger("management-ipc-windows-test")
    test_logger.setLevel(logging.DEBUG)
    test_logger.handlers = [logging.StreamHandler(log_output)]
    host = CapturingServer(lambda: {"observed_at_utc": "2026-10-08T00:00:00Z"}, (caller_sid,), logger=test_logger)
    thread = threading.Thread(target=host.serve, daemon=True)
    thread.start()
    handle = None
    try:
        deadline = time.monotonic() + 3
        while handle is None and time.monotonic() < deadline:
            try:
                handle = win32file.CreateFile(PIPE_NAME, win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                                              0, None, win32con.OPEN_EXISTING, 0, None)
            except Exception:
                time.sleep(0.025)
        assert handle is not None
        win32pipe.SetNamedPipeHandleState(handle, 0x00000002, None, None)
        body = json.dumps(request(), separators=(",", ":")).encode()
        win32file.WriteFile(handle, body)
        deadline = time.monotonic() + 3
        response = None
        while response is None and time.monotonic() < deadline:
            try:
                _, raw = win32file.ReadFile(handle, MAX_MESSAGE_BYTES)
                response = json.loads(raw.decode())
            except Exception as exc:
                if getattr(exc, "winerror", None) == 233:
                    break
                raise
        assert response is not None and response["code"] == "OK", log_output.getvalue()
        win32file.WriteFile(handle, json.dumps({"ack": response["request_id"]}, separators=(",", ":")).encode())
        assert captured == [caller_sid]
    finally:
        if handle is not None:
            win32file.CloseHandle(handle)
        host.shutdown()
        thread.join(3)
        assert not thread.is_alive()


@pytest.mark.skipif(__import__("os").name != "nt", reason="Windows Named Pipe timeout integration")
def test_windows_named_pipe_read_timeout_does_not_block_the_listener():
    import threading
    import time
    import win32api
    import win32con
    import win32file
    import win32pipe
    import win32security

    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        caller_sid = win32security.ConvertSidToStringSid(
            win32security.GetTokenInformation(token, win32security.TokenUser)[0]
        )
    finally:
        win32api.CloseHandle(token)
    host = ManagementNamedPipeServer(lambda: {}, (caller_sid,))
    thread = threading.Thread(target=host.serve, daemon=True)
    thread.start()
    handle = None
    try:
        deadline = time.monotonic() + 3
        while handle is None and time.monotonic() < deadline:
            try:
                handle = win32file.CreateFile(PIPE_NAME, win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                                              0, None, win32con.OPEN_EXISTING, 0, None)
            except Exception:
                time.sleep(0.025)
        assert handle is not None
        win32pipe.SetNamedPipeHandleState(handle, 0x00000002, None, None)
        _, raw = win32file.ReadFile(handle, 4096)
        response = json.loads(raw.decode())
        assert response["code"] == "TIMEOUT"
        win32file.WriteFile(handle, json.dumps({"ack": str(uuid.uuid4())}).encode())
        assert thread.is_alive()
    finally:
        if handle is not None:
            win32file.CloseHandle(handle)
        host.shutdown()
        thread.join(3)
        assert not thread.is_alive()
