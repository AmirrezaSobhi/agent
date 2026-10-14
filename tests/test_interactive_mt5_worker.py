from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from agent.application.runtime_worker import WorkerIdentity
from agent.infrastructure import interactive_mt5_worker as worker


def test_worker_identity_requires_designated_sid_and_nonzero_session():
    worker.validate_identity_values("S-1-5-21-42", "s-1-5-21-42", 2)
    with pytest.raises(RuntimeError, match="WORKER_SESSION_ZERO"):
        worker.validate_identity_values("S-1-5-21-42", "S-1-5-21-42", 0)
    with pytest.raises(RuntimeError, match="WORKER_WRONG_PRINCIPAL"):
        worker.validate_identity_values("S-1-5-21-42", "S-1-5-21-99", 2)


def test_worker_refuses_session_zero_before_mt5_import_or_process_inspection(monkeypatch, tmp_path):
    settings = worker.RuntimeSettings("HOST\\Administrator", "HOST\\Administrator", tmp_path / "terminal64.exe", tmp_path)
    identity = WorkerIdentity("worker", 44, 0, "HOST\\Administrator", "now", "S-1-5-21-42")
    runtime = worker.ReadOnlyMTRuntime(settings, identity, mt5_module=object())
    monkeypatch.setattr(worker, "terminal_processes", lambda *_: pytest.fail("must reject before process access"))
    with pytest.raises(RuntimeError, match="WORKER_SESSION_ZERO"):
        runtime.initialize_readonly()


def runtime_fixture(monkeypatch, tmp_path, *, preexisting=True, connected=True, initialize_results=None):
    terminal = tmp_path / "mt5" / "terminal64.exe"
    terminal.parent.mkdir()
    terminal.write_bytes(b"candidate")
    profile = tmp_path / "profile"
    profile.mkdir()
    (profile / "origin.txt").write_text(str(terminal.parent), encoding="utf-8")
    settings = worker.RuntimeSettings("HOST\\Administrator", "HOST\\Administrator", terminal, profile)
    identity = WorkerIdentity("worker-1", 44, 2, "HOST\\Administrator", "now", "S-1-5-21-42")

    terminal_info = namedtuple("TerminalInfo", "path data_path build connected")(
        str(terminal.parent), str(profile), 6235, True
    )

    class FakeMT5:
        def __init__(self):
            self.calls = []
            self.process_present = preexisting
            self.connected = connected
            self.initialize_results = list(initialize_results or [True])
            self.account_result = namedtuple("AccountInfo", "login currency balance")(
                123, "USD", 100.0
            )
            self.version_result = (5, 0, 6235)
            self.read_result_none = set()
            self.active_reads = 0
            self.max_active_reads = 0
            self.read_lock = threading.Lock()

        def initialize(self, *, path):
            self.calls.append(("initialize", path))
            result = self.initialize_results.pop(0) if self.initialize_results else True
            if result:
                self.process_present = True
                self.connected = True
            return result

        def last_error(self):
            self.calls.append(("last_error",))
            return 1, "Success"

        def terminal_info(self):
            self.calls.append(("terminal_info",))
            return terminal_info._replace(connected=self.connected)

        def symbols_total(self):
            self.calls.append(("symbols_total",))
            with self.read_lock:
                self.active_reads += 1
                self.max_active_reads = max(self.max_active_reads, self.active_reads)
            time.sleep(0.02)
            with self.read_lock:
                self.active_reads -= 1
            return 42

        def version(self):
            self.calls.append(("version",))
            return None if "version" in self.read_result_none else self.version_result

        def account_info(self):
            self.calls.append(("account_info",))
            return None if "account_info" in self.read_result_none else self.account_result

        def shutdown(self):
            self.calls.append(("shutdown",))

    mt5 = FakeMT5()
    process = {
        "pid": 888,
        "session_id": 2,
        "principal": "HOST\\Administrator",
        "sid": "S-1-5-21-42",
        "executable": str(terminal),
        "created_filetime": "133000000000000000",
    }
    monkeypatch.setattr(worker, "terminal_processes", lambda _: [process] if mt5.process_present else [])
    monkeypatch.setattr(worker.importlib.metadata, "version", lambda _: "5.0.6231")
    runtime = worker.ReadOnlyMTRuntime(settings, identity, mt5_module=mt5)
    return runtime, mt5, process


def test_runtime_stays_initialized_across_health_and_repeated_safe_reads(monkeypatch, tmp_path):
    runtime, mt5, process = runtime_fixture(monkeypatch, tmp_path)
    evidence = runtime.initialize_readonly()

    assert evidence["initialize_succeeded"] is True
    assert evidence["mt5_initialized"] is True
    assert evidence["mt5_connected"] is True
    assert evidence["terminal_process"]["session_id"] == 2
    assert evidence["terminal_present_before_initialize"] is True
    assert runtime.health()["runtime_state"] == "MT5_CONNECTED"
    assert runtime.health()["mt5_initialized"] is True
    assert runtime.symbols_total()["value"] == 42
    assert runtime.health()["runtime_state"] == "MT5_CONNECTED"
    assert runtime.symbols_total()["value"] == 42
    assert runtime.health()["runtime_state"] == "MT5_CONNECTED"
    assert mt5.max_active_reads == 1
    assert [call for call in mt5.calls if call[0] == "initialize"] == [
        ("initialize", str(runtime.settings.terminal_path))
    ]
    assert not any(call[0] == "shutdown" for call in mt5.calls)
    assert runtime.health()["terminal_pid"] == process["pid"]
    assert runtime.health()["terminal_owner"] == process["principal"]
    assert runtime.health()["terminal_session_id"] == 2
    assert mt5.calls[0] == ("initialize", str(runtime.settings.terminal_path))
    assert not any("order" in call[0] for call in mt5.calls)


def test_health_detects_disconnect_and_reconnects_once(monkeypatch, tmp_path):
    runtime, mt5, _ = runtime_fixture(monkeypatch, tmp_path)
    runtime.initialize_readonly()
    mt5.connected = False
    assert runtime.health()["runtime_state"] == "MT5_DISCONNECTED"
    assert runtime.health()["mt5_connected"] is False
    assert runtime.reconnect()["runtime_state"] == "MT5_CONNECTED"
    assert mt5.calls.count(("initialize", str(runtime.settings.terminal_path))) == 2
    assert mt5.calls.count(("shutdown",)) == 1


def test_health_detects_terminal_process_loss_and_reconnects(monkeypatch, tmp_path):
    runtime, mt5, _ = runtime_fixture(monkeypatch, tmp_path)
    runtime.initialize_readonly()
    mt5.process_present = False
    health = runtime.health()
    assert health["runtime_state"] == "MT5_DISCONNECTED"
    assert health["mt5_initialized"] is True
    assert health["terminal_pid"] is None
    assert health["last_error_code"] == "MT5_TERMINAL_PROCESS_MISSING"
    assert runtime.reconnect()["runtime_state"] == "MT5_CONNECTED"


def test_mt5_operations_are_serialized_across_threads(monkeypatch, tmp_path):
    runtime, mt5, _ = runtime_fixture(monkeypatch, tmp_path)
    runtime.initialize_readonly()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: runtime.symbols_total()["value"], range(8)))
    assert results == [42] * 8
    assert mt5.max_active_reads == 1


def test_terminal_version_and_account_information_are_normalized_read_only_operations(monkeypatch, tmp_path):
    runtime, mt5, process = runtime_fixture(monkeypatch, tmp_path)
    runtime.initialize_readonly()

    version = runtime.terminal_version()
    account = runtime.account_information()

    assert version["operation"] == "terminal_version"
    assert version["value"] == [5, 0, 6235]
    assert account["operation"] == "account_information"
    assert account["value"] == {"login": 123, "currency": "USD", "balance": 100.0}
    assert version["terminal_pid"] == process["pid"]
    assert account["terminal_session_id"] == process["session_id"]
    assert runtime.health()["last_successful_mt5_operation"] == "account_information"
    assert runtime.health()["runtime_state"] == "MT5_CONNECTED"
    assert mt5.calls.count(("version",)) == 1
    assert mt5.calls.count(("account_info",)) == 1
    assert not any(call[0] == "shutdown" for call in mt5.calls)
    assert not any("order" in call[0] for call in mt5.calls)


def test_read_none_returns_mt5_error_without_stopping_worker_or_losing_runtime(monkeypatch, tmp_path):
    runtime, mt5, _ = runtime_fixture(monkeypatch, tmp_path)
    runtime.initialize_readonly()
    mt5.read_result_none.add("account_info")

    with pytest.raises(RuntimeError, match="MT5_READ_FAILED") as caught:
        runtime.account_information()

    assert caught.value.details["operation"] == "account_information"
    assert runtime.health()["runtime_state"] == "MT5_CONNECTED"
    assert runtime.health()["mt5_initialized"] is True


def test_protocol_allows_only_explicit_new_read_operations():
    from agent.application.runtime_worker import RuntimeWorkerProtocol

    protocol = RuntimeWorkerProtocol("secret", WorkerIdentity(
        "worker", 44, 2, "HOST\\Administrator", "now", "S-1-5-21-42"
    ))
    def request(operation, request_id):
        return protocol.handle({"version": "1", "request_id": request_id,
                                "operation": operation, "token": "secret"})

    assert request("terminal_version", "version") ["ok"] is True
    assert request("account_information", "account") ["ok"] is True
    assert request("execute_arbitrary_method", "arbitrary")["code"] == "IPC_UNSUPPORTED_OPERATION"


def test_failed_initialization_cleans_only_partial_api_and_reports_error(monkeypatch, tmp_path):
    runtime, mt5, _ = runtime_fixture(
        monkeypatch,
        tmp_path,
        preexisting=False,
        initialize_results=[False],
    )
    with pytest.raises(RuntimeError, match="MT5_NOT_INITIALIZED"):
        runtime.initialize_readonly()
    assert mt5.calls.count(("shutdown",)) == 1
    health = runtime.health()
    assert health["runtime_state"] == "MT5_ERROR"
    assert health["mt5_initialized"] is False
    assert health["last_error_code"] == "MT5_NOT_INITIALIZED"


def test_reconnect_failure_uses_bounded_attempts_and_cleans_partial_api(monkeypatch, tmp_path):
    runtime, mt5, _ = runtime_fixture(
        monkeypatch,
        tmp_path,
        preexisting=False,
        initialize_results=[False, False, False],
    )
    runtime.settings = worker.RuntimeSettings(
        runtime.settings.worker_principal,
        runtime.settings.control_principal,
        runtime.settings.terminal_path,
        runtime.settings.profile_path,
        reconnect_attempts=3,
        reconnect_backoff_seconds=1,
    )
    delays = []
    monkeypatch.setattr(worker.time, "sleep", lambda seconds: delays.append(seconds))
    with pytest.raises(RuntimeError, match="MT5_RECONNECT_EXHAUSTED:3"):
        runtime.reconnect()
    assert mt5.calls.count(("initialize", str(runtime.settings.terminal_path))) == 3
    assert mt5.calls.count(("shutdown",)) == 3
    assert runtime.health()["runtime_state"] == "MT5_ERROR"
    assert runtime.health()["mt5_initialized"] is False
    assert delays == pytest.approx([2, 4], abs=0.1)


def test_explicit_runtime_shutdown_releases_api_but_leaves_terminal(monkeypatch, tmp_path):
    runtime, mt5, _ = runtime_fixture(monkeypatch, tmp_path)
    runtime.initialize_readonly()
    result = runtime.shutdown()
    assert result["mt5_shutdown_succeeded"] is True
    assert result["terminal_process_left_running"] is True
    assert mt5.calls.count(("shutdown",)) == 1
    assert runtime.health()["runtime_state"] == "MT5_NOT_INITIALIZED"


def test_runtime_shutdown_keeps_worker_dispatch_available(monkeypatch, tmp_path):
    runtime, mt5, _ = runtime_fixture(monkeypatch, tmp_path)
    identity = runtime.identity
    monkeypatch.setattr(worker, "validate_worker_identity", lambda _settings: identity)
    class FakeSecurity:
        @staticmethod
        def LookupAccountName(_system, principal):
            return ("S-1-5-21-control", None, None)

        @staticmethod
        def ConvertSidToStringSid(sid):
            return str(sid)

    monkeypatch.setitem(sys.modules, "win32security", FakeSecurity)
    _, _, dispatch = worker.dispatch_factory(runtime.settings, mt5_module=mt5)
    peer = type("Peer", (), {
        "principal": "HOST\\Administrator",
        "sid": "S-1-5-21-control",
        "session_id": 0,
        "authentication_method": "exclusive_pipe_dacl",
    })()

    def send(operation, request_id):
        return dispatch({"version": "1", "request_id": request_id, "operation": operation}, peer)

    send("initialize_readonly", "init")
    shutdown = send("runtime_shutdown", "runtime-stop")
    assert shutdown["ok"] is True
    assert shutdown["result"]["mt5_shutdown_succeeded"] is True
    assert shutdown.get("stop_worker") is None
    health = send("health", "health-after-runtime-stop")
    assert health["ok"] is True
    assert health["result"]["runtime_state"] == "MT5_NOT_INITIALIZED"


def test_worker_rejects_preexisting_terminal_from_session_zero_without_attaching(monkeypatch, tmp_path):
    terminal = tmp_path / "terminal64.exe"
    terminal.write_bytes(b"test")
    (tmp_path / "origin.txt").write_text(str(tmp_path), encoding="utf-8")
    settings = worker.RuntimeSettings("HOST\\Administrator", "HOST\\Administrator", terminal, tmp_path)
    identity = WorkerIdentity("worker-1", 44, 2, "HOST\\Administrator", "now", "S-1-5-21-42")
    monkeypatch.setattr(worker, "terminal_processes", lambda _: [{
        "pid": 7188,
        "session_id": 0,
        "principal": "HOST\\Administrator",
        "sid": "S-1-5-21-42",
        "executable": str(terminal),
    }])
    runtime = worker.ReadOnlyMTRuntime(settings, identity, mt5_module=object())
    with pytest.raises(RuntimeError, match="MT5_TERMINAL_SESSION_MISMATCH"):
        runtime.initialize_readonly()
    assert runtime.health()["runtime_state"] == "MT5_ERROR"
    assert runtime.health()["last_error_code"] == "MT5_TERMINAL_SESSION_MISMATCH"


def test_profile_origin_must_match_explicit_terminal(tmp_path):
    terminal = tmp_path / "terminal64.exe"
    terminal.write_bytes(b"test")
    profile = tmp_path / "profile"
    profile.mkdir()
    (profile / "origin.txt").write_text(str(tmp_path / "different-install"), encoding="utf-8")
    settings = worker.RuntimeSettings("HOST\\Administrator", "HOST\\Administrator", terminal, profile)
    with pytest.raises(RuntimeError, match="MT5_PROFILE_ORIGIN_MISMATCH"):
        worker.validate_terminal_profile(settings)


def test_profile_origin_accepts_windows_utf16_bom(tmp_path):
    terminal = tmp_path / "terminal64.exe"
    terminal.write_bytes(b"test")
    profile = tmp_path / "profile"
    profile.mkdir()
    (profile / "origin.txt").write_text(str(tmp_path), encoding="utf-16")
    worker.validate_terminal_profile(
        worker.RuntimeSettings("HOST\\Administrator", "HOST\\Administrator", terminal, profile)
    )


def test_worker_data_directory_is_confined_to_current_users_local_profile(monkeypatch, tmp_path):
    local_app_data = tmp_path / "runtime-user" / "AppData" / "Local"
    local_app_data.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    target = local_app_data / "MT5Agent" / "RuntimeWorker"
    settings = worker.RuntimeSettings(
        "HOST\\MT5RuntimeUser",
        "HOST\\AgentService",
        worker_data_path=str(target),
    )
    assert worker.prepare_worker_data_directory(settings) == target
    assert target.is_dir()

    outside = worker.RuntimeSettings(
        "HOST\\MT5RuntimeUser",
        "HOST\\AgentService",
        worker_data_path=str(tmp_path / "shared-data"),
    )
    with pytest.raises(RuntimeError, match="WORKER_DATA_PATH_OUTSIDE_USER_PROFILE"):
        worker.prepare_worker_data_directory(outside)


def test_worker_install_path_must_contain_the_running_module(monkeypatch, tmp_path):
    install = tmp_path / "ProgramData" / "RuntimeWorker"
    module = install / "agent" / "infrastructure" / "interactive_mt5_worker.py"
    module.parent.mkdir(parents=True)
    module.touch()
    monkeypatch.setattr(worker, "__file__", str(module))
    worker.validate_worker_install_path(
        worker.RuntimeSettings(
            "HOST\\MT5RuntimeUser",
            "HOST\\AgentService",
            worker_install_path=install,
        )
    )
    with pytest.raises(RuntimeError, match="WORKER_INSTALL_PATH_MISMATCH"):
        worker.validate_worker_install_path(
            worker.RuntimeSettings(
                "HOST\\MT5RuntimeUser",
                "HOST\\AgentService",
                worker_install_path=tmp_path / "other-install",
            )
        )


def test_frozen_worker_validates_installed_executable_not_pyinstaller_temp(monkeypatch, tmp_path):
    install = tmp_path / "Program Files" / "MT5Agent" / "Worker"
    install.mkdir(parents=True)
    executable = install / "MT5AgentWorker-v0.1.3.exe"
    executable.touch()
    monkeypatch.setattr(worker.sys, "frozen", True, raising=False)
    monkeypatch.setattr(worker.sys, "executable", str(executable))
    worker.validate_worker_install_path(
        worker.RuntimeSettings(
            "HOST\\MT5RuntimeUser",
            "HOST\\AgentService",
            worker_install_path=install,
        )
    )
    with pytest.raises(RuntimeError, match="WORKER_INSTALL_PATH_MISMATCH"):
        worker.validate_worker_install_path(
            worker.RuntimeSettings(
                "HOST\\MT5RuntimeUser",
                "HOST\\AgentService",
                worker_install_path=tmp_path / "other",
            )
        )


def test_windows_worker_configuration_fails_closed_without_machine_key(monkeypatch):
    class MissingRegistryKey:
        HKEY_LOCAL_MACHINE = object()

        @staticmethod
        def OpenKey(*_args):
            raise FileNotFoundError

    monkeypatch.setattr(worker.os, "name", "nt")
    monkeypatch.setitem(sys.modules, "winreg", MissingRegistryKey)
    with pytest.raises(RuntimeError, match="WORKER_RUNTIME_CONFIGURATION_REQUIRED"):
        worker._registry_settings()


def test_windows_worker_configuration_requires_explicit_runtime_and_profile_values(monkeypatch):
    values = {
        "RuntimePrincipal": "HOST\\MT5RuntimeUser",
        "ControlPrincipal": "HOST\\AgentService",
        "TerminalPath": r"C:\\Program Files\\MetaTrader 5\\terminal64.exe",
        "WorkerInstallPath": r"C:\\ProgramData\\MT5Agent\\RuntimeWorker",
        "WorkerDataPath": r"%LOCALAPPDATA%\\MT5Agent\\RuntimeWorker",
    }

    class RegistryKey:
        def __enter__(self): return self
        def __exit__(self, *_args): return False

    class FakeRegistry:
        HKEY_LOCAL_MACHINE = object()

        @staticmethod
        def OpenKey(*_args): return RegistryKey()

        @staticmethod
        def QueryValueEx(_key, name):
            if name not in values:
                raise FileNotFoundError
            return values[name], 1

    monkeypatch.setattr(worker.os, "name", "nt")
    monkeypatch.setitem(sys.modules, "winreg", FakeRegistry)
    with pytest.raises(RuntimeError, match="WORKER_RUNTIME_CONFIGURATION_INCOMPLETE:ProfilePath"):
        worker._registry_settings()
