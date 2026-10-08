from agent.adapters.runtime_worker_mt5_adapter import RuntimeWorkerMT5Adapter
from agent.application.app import GET_HEALTH
from agent.composition import compose_agent
from agent.contracts.configuration import AgentConfig
from agent.contracts.models import Command
from agent.core.agent import Agent


class FakeRuntimeClient:
    def __init__(self):
        self.available = True
        self.initialized = False
        self.runtime_state = "MT5_NOT_INITIALIZED"
        self.operations = []
        self.bad_version = False
        self.bad_correlation = False
        self.malformed_read = False
        self.read_none = False
        self.disconnected = False
        self.fail_next = None

    def request(self, envelope, *, timeout_ms):
        assert 1 <= timeout_ms <= 120_000
        operation = envelope["operation"]
        self.operations.append(operation)
        if not self.available:
            raise TimeoutError("unavailable")
        if self.fail_next:
            error, self.fail_next = self.fail_next, None
            raise error
        if operation == "initialize_readonly":
            self.initialized = True
            self.runtime_state = "MT5_CONNECTED"
        elif operation == "reconnect":
            self.initialized = True
            self.runtime_state = "MT5_CONNECTED"
        elif operation == "runtime_shutdown":
            self.initialized = False
            self.runtime_state = "MT5_NOT_INITIALIZED"
        if operation == "health":
            result = {
                "worker_state": "WORKER_READY",
                "runtime_state": "MT5_DISCONNECTED" if self.disconnected else self.runtime_state,
                "mt5_initialized": self.initialized,
                "mt5_connected": self.runtime_state == "MT5_CONNECTED" and not self.disconnected,
                "terminal_pid": 401,
                "terminal_owner": "HOST\\MT5RuntimeUser",
                "terminal_session_id": 1,
                "terminal_path": r"C:\Program Files\MetaTrader 5",
                "last_successful_mt5_operation": "initialize" if self.initialized else None,
                "last_mt5_error": [1, "Success"],
                "protocol_version": "1",
            }
        elif operation == "symbols_total":
            result = {"operation": operation, "value": 12335, "runtime_state": self.runtime_state,
                      "terminal_pid": 401, "terminal_session_id": 1}
        elif operation == "terminal_version":
            value = None if self.read_none else [5, 0, 6235]
            result = {"operation": operation, "value": value,
                      "runtime_state": self.runtime_state, "terminal_pid": 401,
                      "terminal_session_id": 1}
        elif operation == "account_information":
            value = None if self.read_none else {"login": 123, "currency": "USD"}
            result = {"operation": operation, "value": value,
                      "runtime_state": self.runtime_state, "terminal_pid": 401,
                      "terminal_session_id": 1}
        elif operation == "runtime_shutdown":
            result = {"mt5_shutdown_succeeded": True, "mt5_initialized": False,
                      "runtime_state": self.runtime_state, "terminal_process_left_running": True}
        else:
            result = {"worker_state": "WORKER_READY"}
        if self.malformed_read and operation in ("terminal_version", "account_information"):
            result["terminal_session_id"] = 0
        response = {
            "ok": True,
            "version": "2" if self.bad_version else "1",
            "request_id": "wrong" if self.bad_correlation else envelope["request_id"],
            "worker": {"pid": 902, "session_id": 1, "account": "HOST\\MT5RuntimeUser",
                       "sid": "S-1-5-21-1001", "protocol_version": "1"},
            "result": result,
        }
        return response


def _command(command_type):
    return Command("id", command_type, "1", "correlation", "2026-10-06T00:00:00Z", {})


def test_adapter_initializes_once_and_reuses_persistent_runtime_for_safe_reads():
    client = FakeRuntimeClient()
    adapter = RuntimeWorkerMT5Adapter(client=client)

    assert adapter.connect()
    assert adapter.runtime_state == "MT5_CONNECTED"
    assert adapter.is_connected()
    assert adapter.symbols_total() == 12335
    assert adapter.is_connected()
    assert client.operations.count("initialize_readonly") == 1
    assert client.operations.count("symbols_total") == 1
    assert "runtime_shutdown" not in client.operations


def test_agent_stays_alive_degraded_when_worker_is_unavailable_and_recovers():
    client = FakeRuntimeClient()
    client.available = False
    clock = [10.0]
    adapter = RuntimeWorkerMT5Adapter(client=client, retry_backoff_seconds=2,
                                      clock=lambda: clock[0])
    agent = Agent(adapter)

    started = agent.start()
    assert started.ok and started.code == "started_degraded"
    assert agent.state.value == "running"
    unhealthy = agent.health()
    assert not unhealthy.ok
    assert unhealthy.runtime_state == "RUNTIME_UNAVAILABLE"
    assert unhealthy.runtime["worker_available"] is False

    client.available = True
    clock[0] += 2.1
    healthy = agent.health()
    assert healthy.ok
    assert healthy.runtime_state == "MT5_CONNECTED"
    assert healthy.runtime["worker_available"] is True
    assert healthy.runtime["worker_identity"]["session_id"] == 1
    assert client.operations.count("initialize_readonly") == 1


def test_inspect_runtime_reports_uninitialized_worker_without_initializing_mt5():
    client = FakeRuntimeClient()
    adapter = RuntimeWorkerMT5Adapter(client=client)

    result = adapter.inspect_runtime()

    assert result["worker_available"] is True
    assert result["runtime_state"] == "MT5_NOT_INITIALIZED"
    assert result["mt5_initialized"] is False
    assert result["mt5_connected"] is False
    assert adapter.health_details["worker_available"] is True
    assert client.operations == ["handshake", "health"]


def test_composed_application_read_command_uses_runtime_adapter_boundary():
    client = FakeRuntimeClient()
    adapter = RuntimeWorkerMT5Adapter(client=client)
    composition = compose_agent(AgentConfig(), mt5=adapter)
    assert composition.agent.start().ok

    result = composition.dispatcher.dispatch(_command("mt5.get_symbols_total"))
    assert result.success
    assert result.data == {"result": 12335}
    health = composition.dispatcher.dispatch(_command(GET_HEALTH))
    assert health.success
    assert health.data["runtime_state"] == "MT5_CONNECTED"
    assert health.data["runtime"]["terminal_session_id"] == 1
    assert client.operations.count("initialize_readonly") == 1


def test_read_capability_manifest_and_contracts_are_restored_through_worker_adapter():
    client = FakeRuntimeClient()
    adapter = RuntimeWorkerMT5Adapter(client=client)
    composition = compose_agent(AgentConfig(), mt5=adapter)
    assert composition.agent.start().ok

    version = composition.dispatcher.dispatch(_command("mt5.get_terminal_version"))
    account = composition.dispatcher.dispatch(_command("mt5.get_account_information"))

    assert version.success and version.data == {"result": [5, 0, 6235]}
    assert account.success and account.data == {"result": {"login": 123, "currency": "USD"}}
    commands = {item["identifier"] for item in
                composition.dispatcher.capability_manifest("0.1.0").commands}
    assert "mt5.get_terminal_version" in commands
    assert "mt5.get_account_information" in commands
    assert client.operations.count("initialize_readonly") == 1
    assert client.operations.count("terminal_version") == 1
    assert client.operations.count("account_information") == 1
    assert adapter.is_connected()


def test_read_failures_are_structured_and_do_not_mark_connected_when_runtime_is_disconnected():
    import pytest
    from agent.contracts.mt5 import MT5ReadError

    client = FakeRuntimeClient()
    adapter = RuntimeWorkerMT5Adapter(client=client, retry_backoff_seconds=0)
    assert adapter.connect()
    client.disconnected = True
    with pytest.raises(MT5ReadError) as caught:
        adapter.terminal_version()
    assert caught.value.code == "MT5_RUNTIME_UNAVAILABLE"
    assert adapter.runtime_state == "MT5_DISCONNECTED"


def test_none_and_malformed_read_results_fail_closed():
    import pytest
    from agent.contracts.mt5 import MT5ReadError

    client = FakeRuntimeClient()
    adapter = RuntimeWorkerMT5Adapter(client=client)
    assert adapter.connect()
    client.read_none = True
    with pytest.raises(MT5ReadError) as caught:
        adapter.account_information()
    assert caught.value.code == "RUNTIME_INVALID_RESPONSE"

    client.read_none = False
    client.malformed_read = True
    with pytest.raises(MT5ReadError) as caught:
        adapter.terminal_version()
    assert caught.value.code == "RUNTIME_INVALID_RESPONSE"


def test_repeated_new_reads_preserve_connected_runtime():
    client = FakeRuntimeClient()
    adapter = RuntimeWorkerMT5Adapter(client=client)
    assert adapter.connect()
    assert adapter.terminal_version() == [5, 0, 6235]
    assert adapter.account_information()["currency"] == "USD"
    assert adapter.is_connected()
    assert client.operations.count("initialize_readonly") == 1
    assert "runtime_shutdown" not in client.operations


def test_new_read_timeout_is_bounded_and_reported_as_mt5_read_error():
    import pytest
    from agent.contracts.mt5 import MT5ReadError

    client = FakeRuntimeClient()
    adapter = RuntimeWorkerMT5Adapter(client=client, request_timeout_ms=500)
    assert adapter.connect()
    client.fail_next = TimeoutError("bounded fake timeout")
    with pytest.raises(MT5ReadError) as caught:
        adapter.terminal_version()
    assert caught.value.code == "RUNTIME_REQUEST_TIMEOUT"


def test_protocol_mismatch_and_bad_correlation_fail_closed():
    client = FakeRuntimeClient()
    client.bad_version = True
    adapter = RuntimeWorkerMT5Adapter(client=client, retry_backoff_seconds=0)
    assert not adapter.connect()
    assert adapter.health_details["last_error_code"] == "RUNTIME_PROTOCOL_MISMATCH"

    client.bad_version = False
    client.bad_correlation = True
    assert not adapter.reconnect()
    assert adapter.health_details["last_error_code"] == "RUNTIME_RESPONSE_CORRELATION_MISMATCH"


def test_wrong_worker_principal_is_rejected_before_mt5_operations():
    client = FakeRuntimeClient()
    adapter = RuntimeWorkerMT5Adapter(client=client, expected_worker_principal="HOST\\ExpectedUser")
    assert not adapter.connect()
    assert adapter.health_details["last_error_code"] == "RUNTIME_WRONG_WORKER_PRINCIPAL"
    assert "initialize_readonly" not in client.operations


def test_timeout_and_malformed_response_are_bounded_failures():
    client = FakeRuntimeClient()
    client.available = False
    adapter = RuntimeWorkerMT5Adapter(client=client, connect_timeout_ms=250,
                                      request_timeout_ms=500, initialize_timeout_ms=1000)
    assert not adapter.connect()
    assert adapter.health_details["last_error_code"] == "RUNTIME_REQUEST_TIMEOUT"

    client.available = True
    client.request = lambda envelope, *, timeout_ms: {"ok": True, "version": "1"}
    assert not adapter.reconnect()
    assert adapter.health_details["last_error_code"] == "RUNTIME_INVALID_RESPONSE"


def test_explicit_runtime_shutdown_is_distinct_from_agent_disconnect():
    client = FakeRuntimeClient()
    adapter = RuntimeWorkerMT5Adapter(client=client)
    assert adapter.connect()
    before = len(client.operations)
    assert adapter.disconnect()
    assert client.operations[before:] == []
    assert adapter.runtime_shutdown()
    assert client.operations[-1] == "runtime_shutdown"


def test_named_pipe_client_needs_no_server_acl_but_server_still_requires_control_sid(monkeypatch):
    import pytest
    from agent.infrastructure import windows_named_pipe

    monkeypatch.setattr(windows_named_pipe.os, "name", "nt")
    pipe = windows_named_pipe.WindowsNamedPipe()
    assert pipe.allowed_principals == ()
    with pytest.raises(ValueError, match="PIPE_SERVER_REQUIRES_EXACTLY_ONE_CONTROL_PRINCIPAL"):
        pipe.create_server()


def test_windows_composition_selects_worker_adapter_without_importing_vendor_module(monkeypatch):
    import agent.composition as composition_module
    import sys

    monkeypatch.setattr(composition_module.os, "name", "nt")
    sys.modules.pop("agent.adapters.mt5_adapter", None)
    composition = compose_agent(AgentConfig())
    assert isinstance(composition.agent.mt5, RuntimeWorkerMT5Adapter)
    assert "MetaTrader5" not in sys.modules
    assert "agent.adapters.mt5_adapter" not in sys.modules
