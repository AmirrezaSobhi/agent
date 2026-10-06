"""Per-user interactive MT5 runtime worker.

The worker is intended to start from a logon-triggered InteractiveToken task.
It never accepts terminal paths or arbitrary commands from IPC callers. The
Worker owns one persistent MetaTrader5 API connection and exposes only bounded,
read-only runtime operations. It never sends or modifies an order.
"""
from __future__ import annotations

import importlib.metadata
import os
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from agent.application.runtime_worker import (
    PROTOCOL_VERSION,
    RuntimeWorkerProtocol,
    WorkerIdentity,
    WorkerState,
)
from agent.contracts.mt5 import MT5ReadError


RUNTIME_REGISTRY_KEY = r"SOFTWARE\MT5Agent\Runtime"
PIPE_NAME = r"\\.\pipe\MT5Agent.Runtime.v1"


@dataclass(frozen=True)
class RuntimeSettings:
    worker_principal: str
    control_principal: str
    terminal_path: Path | None = None
    profile_path: Path | None = None
    pipe_name: str = PIPE_NAME
    reconnect_attempts: int = 3
    reconnect_backoff_seconds: float = 1.0
    worker_install_path: Path | None = None
    worker_data_path: str | None = None


def _registry_settings() -> RuntimeSettings:
    if os.name != "nt":
        raise OSError("INTERACTIVE_MT5_WORKER_REQUIRES_WINDOWS")
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, RUNTIME_REGISTRY_KEY) as key:
            runtime: dict[str, str] = {}
            for name in (
                "RuntimePrincipal",
                "ControlPrincipal",
                "TerminalPath",
                "ProfilePath",
                "WorkerInstallPath",
                "WorkerDataPath",
                "PipeName",
            ):
                try:
                    runtime[name] = str(winreg.QueryValueEx(key, name)[0]).strip()
                except FileNotFoundError:
                    pass
    except FileNotFoundError:
        raise RuntimeError("WORKER_RUNTIME_CONFIGURATION_REQUIRED") from None
    required = (
        "RuntimePrincipal",
        "ControlPrincipal",
        "TerminalPath",
        "ProfilePath",
        "WorkerInstallPath",
        "WorkerDataPath",
    )
    missing = [name for name in required if not runtime.get(name)]
    if missing:
        raise RuntimeError("WORKER_RUNTIME_CONFIGURATION_INCOMPLETE:" + ",".join(missing))
    return RuntimeSettings(
        worker_principal=runtime["RuntimePrincipal"],
        control_principal=runtime["ControlPrincipal"],
        terminal_path=Path(runtime["TerminalPath"]),
        profile_path=Path(runtime["ProfilePath"]),
        pipe_name=runtime.get("PipeName") or PIPE_NAME,
        worker_install_path=Path(runtime["WorkerInstallPath"]),
        worker_data_path=runtime["WorkerDataPath"],
    )


def prepare_worker_data_directory(settings: RuntimeSettings) -> Path:
    """Resolve mutable state under this user's profile, never beside code."""
    if not settings.worker_data_path:
        raise RuntimeError("WORKER_DATA_PATH_NOT_CONFIGURED")
    expanded = Path(os.path.expandvars(os.path.expanduser(settings.worker_data_path)))
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("WORKER_LOCAL_APPDATA_UNAVAILABLE")
    base = os.path.normcase(os.path.abspath(local_app_data))
    target = os.path.normcase(os.path.abspath(expanded))
    try:
        if os.path.commonpath((base, target)) != base or target == base:
            raise RuntimeError("WORKER_DATA_PATH_OUTSIDE_USER_PROFILE")
    except ValueError:
        raise RuntimeError("WORKER_DATA_PATH_OUTSIDE_USER_PROFILE") from None
    expanded.mkdir(parents=True, exist_ok=True)
    return expanded


def validate_worker_install_path(settings: RuntimeSettings) -> None:
    """Ensure the scheduled task launched the staged, trusted Worker copy."""
    if settings.worker_install_path is None:
        raise RuntimeError("WORKER_INSTALL_PATH_NOT_CONFIGURED")
    module_path = Path(__file__).resolve()
    install_path = settings.worker_install_path.resolve()
    try:
        module_path.relative_to(install_path)
    except ValueError:
        raise RuntimeError("WORKER_INSTALL_PATH_MISMATCH") from None


def _current_identity() -> tuple[int, int, str, str]:
    import ctypes
    import win32api
    import win32con
    import win32security

    session = ctypes.c_uint32()
    pid = os.getpid()
    if not ctypes.windll.kernel32.ProcessIdToSessionId(pid, ctypes.byref(session)):
        raise RuntimeError("WORKER_SESSION_UNAVAILABLE")
    process = win32api.GetCurrentProcess()
    token = win32security.OpenProcessToken(process, win32con.TOKEN_QUERY)
    try:
        sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
        username, domain, _ = win32security.LookupAccountSid(None, sid)
        sid_text = win32security.ConvertSidToStringSid(sid)
    finally:
        token.Close()
    return pid, int(session.value), f"{domain}\\{username}", sid_text


def _principal_sid(principal: str):
    import win32security

    return win32security.LookupAccountName(None, principal)[0]


def validate_identity_values(expected_sid: str, actual_sid: str, session_id: int) -> None:
    if session_id == 0:
        raise RuntimeError("WORKER_SESSION_ZERO")
    if expected_sid.casefold() != actual_sid.casefold():
        raise RuntimeError("WORKER_WRONG_PRINCIPAL")


def validate_worker_identity(settings: RuntimeSettings, identity=None) -> WorkerIdentity:
    """Fail closed unless this process is the configured user's real session."""
    pid, session_id, account, sid_text = identity or _current_identity()
    try:
        expected_sid = _principal_sid(settings.worker_principal)
    except Exception:
        raise RuntimeError("WORKER_POLICY_PRINCIPAL_INVALID") from None
    import win32security

    actual_sid = win32security.ConvertStringSidToSid(sid_text)
    expected_sid_text = win32security.ConvertSidToStringSid(expected_sid)
    validate_identity_values(expected_sid_text, sid_text, session_id)
    return WorkerIdentity(
        instance_id=str(uuid.uuid4()),
        pid=int(pid),
        session_id=int(session_id),
        account=account,
        started_at=datetime.now(timezone.utc).isoformat(),
        sid=sid_text,
    )


def validate_terminal_profile(settings: RuntimeSettings) -> None:
    terminal = settings.terminal_path
    profile = settings.profile_path
    if terminal is None or profile is None:
        raise RuntimeError("MT5_TERMINAL_OR_PROFILE_PATH_NOT_CONFIGURED")
    if not terminal.is_file():
        raise RuntimeError("MT5_NOT_INSTALLED")
    if not profile.is_dir():
        raise RuntimeError("MT5_PROFILE_NOT_FOUND")
    origin = profile / "origin.txt"
    if not origin.is_file():
        raise RuntimeError("MT5_PROFILE_ORIGIN_MISSING")
    try:
        raw_origin = origin.read_bytes()
        encoding = "utf-16" if raw_origin.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        origin_path = Path(raw_origin.decode(encoding).strip())
        matches = os.path.normcase(os.path.abspath(origin_path)) == os.path.normcase(
            os.path.abspath(terminal.parent)
        )
    except (OSError, UnicodeError):
        matches = False
    if not matches:
        raise RuntimeError("MT5_PROFILE_ORIGIN_MISMATCH")


def terminal_processes(expected_path: Path) -> list[dict[str, object]]:
    """Return exact-path MT5 process identity evidence without changing processes."""
    import ctypes
    import win32api
    import win32con
    import win32security
    import win32process

    kernel = ctypes.windll.kernel32
    result: list[dict[str, object]] = []
    target = os.path.normcase(os.path.abspath(expected_path))
    for pid in win32process.EnumProcesses():
        if not pid:
            continue
        try:
            process = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        except Exception:
            continue
        try:
            size = ctypes.c_uint32(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not kernel.QueryFullProcessImageNameW(int(process), 0, buffer, ctypes.byref(size)):
                continue
            image = buffer.value
            if os.path.normcase(os.path.abspath(image)) != target:
                continue
            session = ctypes.c_uint32()
            if not kernel.ProcessIdToSessionId(pid, ctypes.byref(session)):
                continue
            token = win32security.OpenProcessToken(process, win32con.TOKEN_QUERY)
            try:
                sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
                username, domain, _ = win32security.LookupAccountSid(None, sid)
                sid_text = win32security.ConvertSidToStringSid(sid)
            finally:
                token.Close()
            created = None
            try:
                created_filetime, _, _, _ = win32process.GetProcessTimes(process)
                created = str(created_filetime)
            except Exception:
                pass
            result.append({
                "pid": int(pid),
                "session_id": int(session.value),
                "principal": f"{domain}\\{username}",
                "sid": sid_text,
                "executable": image,
                "created_filetime": created,
            })
        finally:
            process.Close()
    return result


class MTRuntimeState(str, Enum):
    NOT_INITIALIZED = "MT5_NOT_INITIALIZED"
    INITIALIZING = "MT5_INITIALIZING"
    CONNECTED = "MT5_CONNECTED"
    DISCONNECTED = "MT5_DISCONNECTED"
    RECONNECTING = "MT5_RECONNECTING"
    ERROR = "MT5_ERROR"


class ReadOnlyMTRuntime:
    """Persistent, serialized owner of the Worker process's MetaTrader5 API."""

    def __init__(self, settings: RuntimeSettings, identity: WorkerIdentity, *, mt5_module=None):
        self.settings = settings
        self.identity = identity
        self._mt5 = mt5_module
        self._initialized = False
        self._init_attempted = False
        self._runtime_state = MTRuntimeState.NOT_INITIALIZED
        self._last_error_code: str | None = None
        self._last_mt5_error: object | None = None
        self._last_successful_mt5_operation: str | None = None
        self._terminal_process: dict[str, object] | None = None
        self._terminal_info: dict[str, object] | None = None
        self._runtime_lock = threading.RLock()
        self._last_reconnect_at = 0.0

    def _api(self):
        if self._mt5 is None:
            try:
                import MetaTrader5 as mt5
            except ImportError as exc:
                raise RuntimeError("MT5_PYTHON_PACKAGE_UNAVAILABLE") from exc
            self._mt5 = mt5
        return self._mt5

    @staticmethod
    def _fields(value) -> dict[str, object]:
        return value._asdict() if hasattr(value, "_asdict") else vars(value)

    @staticmethod
    def _wire_value(value):
        """Convert only known MT5 result containers to bounded JSON values."""
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if hasattr(value, "_asdict"):
            return {str(key): ReadOnlyMTRuntime._wire_value(item)
                    for key, item in value._asdict().items()}
        if isinstance(value, (tuple, list)):
            return [ReadOnlyMTRuntime._wire_value(item) for item in value]
        if isinstance(value, dict):
            return {str(key): ReadOnlyMTRuntime._wire_value(item) for key, item in value.items()}
        raise RuntimeError("MT5_RESPONSE_UNSUPPORTED_TYPE")

    def _verified_terminal_process(self, *, required: bool = True) -> dict[str, object] | None:
        processes = terminal_processes(self.settings.terminal_path)
        if not processes:
            if required:
                raise RuntimeError("MT5_TERMINAL_PROCESS_MISSING")
            return None
        if len(processes) != 1:
            raise RuntimeError("MT5_TERMINAL_OWNERSHIP_AMBIGUOUS")
        process = processes[0]
        if os.path.normcase(os.path.abspath(str(process.get("executable", "")))) != os.path.normcase(
            os.path.abspath(self.settings.terminal_path)
        ):
            raise RuntimeError("MT5_TERMINAL_PATH_MISMATCH")
        if process.get("session_id") != self.identity.session_id:
            raise RuntimeError("MT5_TERMINAL_SESSION_MISMATCH")
        if str(process.get("sid", "")).casefold() != self.identity.sid.casefold():
            raise RuntimeError("MT5_TERMINAL_OWNER_MISMATCH")
        if str(process.get("principal", "")).casefold() != self.identity.account.casefold():
            raise RuntimeError("MT5_TERMINAL_PRINCIPAL_MISMATCH")
        return process

    def _observe_live_runtime(self) -> tuple[dict[str, object], dict[str, object]]:
        mt5 = self._api()
        terminal = mt5.terminal_info()
        if terminal is None:
            raise RuntimeError("MT5_TERMINAL_INFO_UNAVAILABLE")
        fields = self._fields(terminal)
        terminal_path = str(fields.get("path", ""))
        data_path = str(fields.get("data_path", ""))
        expected_path = os.path.normcase(os.path.abspath(self.settings.terminal_path.parent))
        if os.path.normcase(os.path.abspath(terminal_path)) != expected_path:
            raise RuntimeError("MT5_TERMINAL_PATH_MISMATCH")
        if not data_path:
            raise RuntimeError("MT5_PROFILE_PATH_UNAVAILABLE")
        if os.path.normcase(os.path.abspath(data_path)) != os.path.normcase(
            os.path.abspath(self.settings.profile_path)
        ):
            raise RuntimeError("MT5_PROFILE_PATH_MISMATCH")
        process = self._verified_terminal_process()
        terminal_fields = {
            "terminal_path": terminal_path,
            "terminal_data_path": data_path,
            "terminal_build": fields.get("build"),
            "connected": bool(fields.get("connected", False)),
        }
        if not terminal_fields["connected"]:
            raise ConnectionError("MT5_NOT_CONNECTED")
        return terminal_fields, process

    def _capture_last_error(self) -> object | None:
        try:
            error = self._api().last_error()
            return list(error) if isinstance(error, tuple) else error
        except Exception:
            return None

    def _initialize_once(self, *, reconnecting: bool = False) -> dict[str, object]:
        if self.identity.session_id == 0:
            raise RuntimeError("WORKER_SESSION_ZERO")
        validate_terminal_profile(self.settings)
        mt5 = self._api()
        # Reuse a terminal only when its path, owner SID and interactive session
        # already match this Worker. Never attach to a Session 0 or foreign MT5.
        preexisting = self._verified_terminal_process(required=False)
        self._runtime_state = MTRuntimeState.RECONNECTING if reconnecting else MTRuntimeState.INITIALIZING
        if self._initialized:
            mt5.shutdown()
            self._initialized = False
        self._init_attempted = True
        initialized = bool(mt5.initialize(path=str(self.settings.terminal_path)))
        self._last_mt5_error = self._capture_last_error()
        if not initialized:
            raise RuntimeError("MT5_NOT_INITIALIZED")
        self._initialized = True
        self._init_attempted = False
        terminal_fields, process = self._observe_live_runtime()
        package_version = importlib.metadata.version("MetaTrader5")
        self._terminal_process = process
        self._terminal_info = terminal_fields
        self._runtime_state = MTRuntimeState.CONNECTED
        self._last_error_code = None
        self._last_successful_mt5_operation = "initialize"
        return {
            "worker_identity": self.identity.to_dict(),
            "worker_pid": self.identity.pid,
            "worker_session_id": self.identity.session_id,
            "initialize_succeeded": True,
            "mt5_initialized": True,
            "mt5_connected": True,
            "last_error": self._last_mt5_error,
            "package_version": package_version,
            "terminal_process": process,
            "terminal_pid": process["pid"],
            "terminal_owner": process["principal"],
            "terminal_session_id": process["session_id"],
            "terminal_path": terminal_fields["terminal_path"],
            "terminal_data_path": terminal_fields["terminal_data_path"],
            "terminal_build": terminal_fields["terminal_build"],
            "terminal_present_before_initialize": preexisting is not None,
            "runtime_state": self._runtime_state.value,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

    def initialize_readonly(self, _operation: str = "initialize_readonly") -> dict[str, object]:
        """Initialize once and keep the API connection for subsequent requests."""
        with self._runtime_lock:
            if self._initialized:
                return self._health_locked()
            try:
                return self._initialize_once()
            except Exception as exc:
                self._last_mt5_error = self._capture_last_error()
                if self._initialized or self._init_attempted:
                    self._shutdown_api_locked(force=True)
                self._runtime_state = MTRuntimeState.ERROR
                self._last_error_code = str(exc.args[0]) if exc.args else "MT5_INITIALIZATION_FAILED"
                raise

    def _health_locked(self) -> dict[str, object]:
        if self._initialized:
            try:
                self._terminal_info, self._terminal_process = self._observe_live_runtime()
                self._runtime_state = MTRuntimeState.CONNECTED
                self._last_mt5_error = self._capture_last_error()
                self._last_error_code = None
            except ConnectionError as exc:
                self._runtime_state = MTRuntimeState.DISCONNECTED
                self._last_error_code = str(exc)
                self._last_mt5_error = self._capture_last_error()
            except Exception as exc:
                self._runtime_state = MTRuntimeState.DISCONNECTED
                self._last_error_code = str(exc.args[0]) if exc.args else "MT5_HEALTH_CHECK_FAILED"
                self._last_mt5_error = self._capture_last_error()
                try:
                    self._terminal_process = self._verified_terminal_process(required=False)
                except Exception:
                    self._terminal_process = None
        return {
            "worker_state": WorkerState.READY.value,
            "worker_identity": self.identity.to_dict(),
            "worker_pid": self.identity.pid,
            "worker_session_id": self.identity.session_id,
            "runtime_state": self._runtime_state.value,
            "mt5_initialized": self._initialized,
            "mt5_connected": self._runtime_state == MTRuntimeState.CONNECTED,
            "terminal_pid": self._terminal_process.get("pid") if self._terminal_process else None,
            "terminal_owner": self._terminal_process.get("principal") if self._terminal_process else None,
            "terminal_session_id": self._terminal_process.get("session_id") if self._terminal_process else None,
            "terminal_path": self._terminal_info.get("terminal_path") if self._terminal_info else str(self.settings.terminal_path),
            "terminal_data_path": self._terminal_info.get("terminal_data_path") if self._terminal_info else None,
            "terminal_build": self._terminal_info.get("terminal_build") if self._terminal_info else None,
            "last_successful_mt5_operation": self._last_successful_mt5_operation,
            "last_mt5_error": self._last_mt5_error,
            "last_error_code": self._last_error_code,
            "protocol_version": PROTOCOL_VERSION,
        }

    def health(self) -> dict[str, object]:
        with self._runtime_lock:
            return self._health_locked()

    def symbols_total(self) -> dict[str, object]:
        with self._runtime_lock:
            if not self._initialized:
                raise RuntimeError("MT5_NOT_INITIALIZED")
            try:
                self._terminal_info, self._terminal_process = self._observe_live_runtime()
                result = int(self._api().symbols_total())
                self._runtime_state = MTRuntimeState.CONNECTED
                self._last_successful_mt5_operation = "symbols_total"
                self._last_mt5_error = self._capture_last_error()
                self._last_error_code = None
                return {
                    "operation": "symbols_total",
                    "value": result,
                    "read_test_succeeded": True,
                    "runtime_state": self._runtime_state.value,
                    "terminal_pid": self._terminal_process["pid"],
                    "terminal_session_id": self._terminal_process["session_id"],
                }
            except Exception as exc:
                self._last_mt5_error = self._capture_last_error()
                self._runtime_state = MTRuntimeState.DISCONNECTED
                self._last_error_code = str(exc.args[0]) if exc.args else "MT5_READ_FAILED"
                raise

    def _read_operation(self, operation: str, api_name: str) -> dict[str, object]:
        """Run one explicitly allowlisted read against the persistent API."""
        with self._runtime_lock:
            if not self._initialized:
                raise RuntimeError("MT5_NOT_INITIALIZED")
            try:
                self._terminal_info, self._terminal_process = self._observe_live_runtime()
                value = getattr(self._api(), api_name)()
                self._last_mt5_error = self._capture_last_error()
                if value is None:
                    self._runtime_state = MTRuntimeState.CONNECTED
                    self._last_error_code = "MT5_READ_FAILED"
                    raise MT5ReadError("MT5_READ_FAILED", {
                        "operation": operation,
                        "last_error": self._last_mt5_error,
                    })
                wire_value = self._wire_value(value)
                self._runtime_state = MTRuntimeState.CONNECTED
                self._last_successful_mt5_operation = operation
                self._last_error_code = None
                return {
                    "operation": operation,
                    "value": wire_value,
                    "runtime_state": self._runtime_state.value,
                    "terminal_pid": self._terminal_process["pid"],
                    "terminal_session_id": self._terminal_process["session_id"],
                }
            except Exception as exc:
                self._last_mt5_error = self._capture_last_error()
                if str(exc.args[0] if exc.args else "") != "MT5_READ_FAILED":
                    self._runtime_state = MTRuntimeState.DISCONNECTED
                    self._last_error_code = str(exc.args[0]) if exc.args else "MT5_READ_FAILED"
                raise

    def terminal_version(self) -> dict[str, object]:
        return self._read_operation("terminal_version", "version")

    def account_information(self) -> dict[str, object]:
        return self._read_operation("account_information", "account_info")

    def reconnect(self) -> dict[str, object]:
        """Make at most the configured number of spaced initialization attempts."""
        with self._runtime_lock:
            if self._initialized:
                health = self._health_locked()
                if health["mt5_connected"]:
                    return health
            self._runtime_state = MTRuntimeState.RECONNECTING
            if self._initialized or self._init_attempted:
                self._shutdown_api_locked(force=True)
            attempts = max(1, min(int(self.settings.reconnect_attempts), 5))
            last_exception: Exception | None = None
            for attempt in range(attempts):
                now = time.monotonic()
                delay = max(0.0, float(self.settings.reconnect_backoff_seconds)) * (2**attempt)
                wait = self._last_reconnect_at + delay - now
                if wait > 0:
                    time.sleep(wait)
                self._last_reconnect_at = time.monotonic()
                try:
                    return self._initialize_once(reconnecting=True)
                except Exception as exc:
                    last_exception = exc
                    self._last_mt5_error = self._capture_last_error()
                    if self._initialized or self._init_attempted:
                        self._shutdown_api_locked(force=True)
                    self._last_error_code = str(exc.args[0]) if exc.args else "MT5_RECONNECT_FAILED"
            self._runtime_state = MTRuntimeState.ERROR
            raise RuntimeError(
                f"MT5_RECONNECT_EXHAUSTED:{attempts}:{self._last_error_code or 'unknown'}"
            ) from last_exception

    def _shutdown_api_locked(self, *, force: bool = False) -> bool:
        if not self._initialized and not force:
            self._runtime_state = MTRuntimeState.NOT_INITIALIZED
            return True
        try:
            self._api().shutdown()
            self._initialized = False
            self._init_attempted = False
            self._runtime_state = MTRuntimeState.NOT_INITIALIZED
            self._last_error_code = None
            return True
        except Exception:
            self._runtime_state = MTRuntimeState.ERROR
            self._last_error_code = "MT5_SHUTDOWN_FAILED"
            self._last_mt5_error = self._capture_last_error()
            return False

    def shutdown(self) -> dict[str, object]:
        """Explicitly release the Python API connection; never kill terminal64."""
        with self._runtime_lock:
            succeeded = self._shutdown_api_locked()
            return {
                "mt5_shutdown_succeeded": succeeded,
                "mt5_initialized": self._initialized,
                "runtime_state": self._runtime_state.value,
                "terminal_process_left_running": True,
            }


def dispatch_factory(settings: RuntimeSettings, *, mt5_module=None):
    identity = validate_worker_identity(settings)
    runtime = ReadOnlyMTRuntime(settings, identity, mt5_module=mt5_module)
    stop = threading.Event()

    def handle(operation: str) -> dict[str, object]:
        if operation == "health":
            return runtime.health()
        if operation == "initialize_readonly":
            return runtime.initialize_readonly()
        if operation == "reconnect":
            return runtime.reconnect()
        if operation == "symbols_total":
            return runtime.symbols_total()
        if operation == "terminal_version":
            return runtime.terminal_version()
        if operation == "account_information":
            return runtime.account_information()
        if operation == "runtime_shutdown":
            return runtime.shutdown()
        if operation == "shutdown":
            result = runtime.shutdown()
            stop.set()
            return {**result, "worker_state": WorkerState.STOPPING.value}
        if operation == "handshake":
            return {"worker_state": WorkerState.READY.value}
        raise RuntimeError("IPC_UNSUPPORTED_OPERATION")

    protocol = RuntimeWorkerProtocol(None, identity, handle)
    import win32security
    expected_control_sid = win32security.ConvertSidToStringSid(_principal_sid(settings.control_principal))

    def dispatch(request: dict[str, object], peer) -> dict[str, object]:
        if getattr(peer, "authentication_method", None) != "exclusive_pipe_dacl":
            return {"ok": False, "code": "IPC_AUTHENTICATION_FAILED"}
        response = protocol.handle(
            request,
            client_principal=peer.principal,
            client_sid=peer.sid,
            client_session_id=peer.session_id,
            expected_client_principal=settings.control_principal,
            expected_client_sid=expected_control_sid,
        )
        if stop.is_set():
            response["stop_worker"] = True
        return response

    return identity, runtime, dispatch


def run_worker(settings: RuntimeSettings | None = None) -> None:
    from agent.infrastructure.windows_named_pipe import WindowsNamedPipe

    settings = settings or _registry_settings()
    validate_worker_install_path(settings)
    prepare_worker_data_directory(settings)
    _, _, dispatch = dispatch_factory(settings)
    pipe = WindowsNamedPipe(settings.pipe_name, allowed_principals=(settings.control_principal,))
    pipe.serve_forever(dispatch)


if __name__ == "__main__":
    run_worker()
