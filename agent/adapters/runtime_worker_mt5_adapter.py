"""Application-facing adapter for the authenticated interactive MT5 Worker."""
from __future__ import annotations

import logging
import os
import threading
import time
from uuid import uuid4

from agent.application.runtime_worker import PROTOCOL_VERSION
from agent.contracts.mt5 import MT5ReadError


PIPE_NAME = r"\\.\pipe\MT5Agent.Runtime.v1"


class RuntimeWorkerMT5Adapter:
    """Keep the existing MT5 lifecycle port while moving calls across local IPC.

    This adapter never imports the MetaTrader5 package.  The Worker remains the
    sole owner of that package and of the persistent API connection.
    """

    supports_degraded_startup = True

    def __init__(
        self,
        client=None,
        *,
        pipe_name: str = PIPE_NAME,
        connect_timeout_ms: int = 2_000,
        request_timeout_ms: int = 5_000,
        initialize_timeout_ms: int = 120_000,
        retry_backoff_seconds: float = 2.0,
        expected_worker_principal: str | None = None,
        configuration_error: str | None = None,
        require_session_zero: bool = False,
        logger: logging.Logger | None = None,
        clock=time.monotonic,
    ) -> None:
        if not 1 <= connect_timeout_ms <= 120_000:
            raise ValueError("RUNTIME_WORKER_CONNECT_TIMEOUT_OUT_OF_RANGE")
        if not 1 <= request_timeout_ms <= 120_000:
            raise ValueError("RUNTIME_WORKER_REQUEST_TIMEOUT_OUT_OF_RANGE")
        if not 1 <= initialize_timeout_ms <= 120_000:
            raise ValueError("RUNTIME_WORKER_INITIALIZE_TIMEOUT_OUT_OF_RANGE")
        if retry_backoff_seconds < 0:
            raise ValueError("RUNTIME_WORKER_RETRY_BACKOFF_INVALID")
        self._client = client
        self._pipe_name = pipe_name
        self._connect_timeout_ms = connect_timeout_ms
        self._request_timeout_ms = request_timeout_ms
        self._initialize_timeout_ms = initialize_timeout_ms
        self._retry_backoff_seconds = retry_backoff_seconds
        self._expected_worker_principal = expected_worker_principal
        self._configuration_error = configuration_error
        self._require_session_zero = require_session_zero
        self._logger = logger or logging.getLogger(__name__)
        self._clock = clock
        self._lock = threading.RLock()
        self._runtime_state = "RUNTIME_UNAVAILABLE"
        self._health: dict[str, object] = {}
        self._last_error: str | None = None
        self._next_retry_at = 0.0

    @property
    def runtime_state(self) -> str:
        return self._runtime_state

    @property
    def health_details(self) -> dict[str, object]:
        # Return only the Worker health contract's non-secret fields.
        return dict(self._health)

    def _pipe_client(self):
        if self._client is None:
            from agent.infrastructure.windows_named_pipe import WindowsNamedPipe

            self._client = WindowsNamedPipe(self._pipe_name)
        return self._client

    def _request(self, operation: str, *, timeout_ms: int | None = None) -> dict[str, object]:
        request_id = str(uuid4())
        envelope = {"version": PROTOCOL_VERSION, "request_id": request_id, "operation": operation}
        try:
            response = self._pipe_client().request(
                envelope,
                timeout_ms=timeout_ms or self._request_timeout_ms,
            )
        except TimeoutError:
            raise RuntimeWorkerError("RUNTIME_REQUEST_TIMEOUT") from None
        except OSError as exc:
            code = getattr(exc, "winerror", None)
            if code == 5:
                raise RuntimeWorkerError("RUNTIME_AUTHENTICATION_FAILED") from None
            raise RuntimeWorkerError("RUNTIME_UNAVAILABLE") from None
        except Exception as exc:
            raise RuntimeWorkerError("RUNTIME_IPC_FAILED") from None

        if not isinstance(response, dict):
            raise RuntimeWorkerError("RUNTIME_INVALID_RESPONSE")
        if response.get("ok") is not True:
            code = response.get("code")
            if not isinstance(code, str) or not code or len(code) > 96:
                code = "RUNTIME_REQUEST_REJECTED"
            details = response.get("details")
            if not isinstance(details, dict):
                details = {}
            # Worker errors carry only bounded diagnostic metadata, never the
            # value returned by an account-information operation.
            raise RuntimeWorkerError(code, details)
        if not all(key in response for key in ("version", "request_id", "worker", "result")):
            raise RuntimeWorkerError("RUNTIME_INVALID_RESPONSE")
        if response.get("version") != PROTOCOL_VERSION:
            raise RuntimeWorkerError("RUNTIME_PROTOCOL_MISMATCH")
        if response.get("request_id") != request_id:
            raise RuntimeWorkerError("RUNTIME_RESPONSE_CORRELATION_MISMATCH")
        worker = response.get("worker")
        result = response.get("result")
        if not isinstance(worker, dict) or not isinstance(result, dict):
            raise RuntimeWorkerError("RUNTIME_INVALID_RESPONSE")
        if worker.get("protocol_version") != PROTOCOL_VERSION:
            raise RuntimeWorkerError("RUNTIME_PROTOCOL_MISMATCH")
        session_id = worker.get("session_id")
        pid = worker.get("pid")
        account = worker.get("account")
        if (not isinstance(pid, int) or pid <= 0 or not isinstance(session_id, int)
                or session_id <= 0 or not isinstance(account, str) or not account):
            raise RuntimeWorkerError("RUNTIME_WORKER_IDENTITY_INVALID")
        if (self._expected_worker_principal is not None
                and account.casefold() != self._expected_worker_principal.casefold()):
            raise RuntimeWorkerError("RUNTIME_WRONG_WORKER_PRINCIPAL")
        return {"worker": worker, "result": result, "state": response.get("state")}

    @staticmethod
    def _safe_health(worker: dict[str, object], result: dict[str, object]) -> dict[str, object]:
        identity = {
            key: worker.get(key)
            for key in ("account", "pid", "session_id", "sid", "protocol_version")
            if worker.get(key) is not None
        }
        allowed = (
            "worker_state", "runtime_state", "mt5_initialized", "mt5_connected",
            "terminal_pid", "terminal_owner", "terminal_session_id", "terminal_path",
            "terminal_data_path", "terminal_build", "last_successful_mt5_operation",
            "last_mt5_error", "last_error_code", "protocol_version",
        )
        health = {key: result[key] for key in allowed if key in result}
        health["worker_identity"] = identity
        return health

    def _health_request(self) -> dict[str, object]:
        message = self._request("health")
        health = self._safe_health(message["worker"], message["result"])
        # A valid health response was received from the authenticated Worker.
        # This is distinct from MT5 connectivity, which the Worker reports.
        health["worker_available"] = True
        if self._require_session_zero:
            health["control_session_id"] = self._control_session_id()
        self._health = health
        state = health.get("runtime_state")
        self._runtime_state = state if isinstance(state, str) else "WORKER_READY"
        return health

    def inspect_runtime(self) -> dict[str, object]:
        """Read Worker/runtime status without initializing or reconnecting MT5."""
        with self._lock:
            if self._configuration_error:
                return {
                    "worker_available": False,
                    "runtime_state": "RUNTIME_CONFIGURATION_UNAVAILABLE",
                    "last_error_code": "RUNTIME_CONFIGURATION_UNAVAILABLE",
                    "protocol_version": PROTOCOL_VERSION,
                }
            control_session = self._control_session_id() if self._require_session_zero else None
            if self._require_session_zero and control_session != 0:
                return {
                    "worker_available": False,
                    "runtime_state": "RUNTIME_CONTROL_NOT_SESSION_ZERO",
                    "last_error_code": "RUNTIME_CONTROL_NOT_SESSION_ZERO",
                    "control_session_id": control_session,
                    "protocol_version": PROTOCOL_VERSION,
                }
            try:
                self._request("handshake", timeout_ms=self._connect_timeout_ms)
                health = self._health_request()
                health["worker_available"] = True
                health["protocol_version"] = PROTOCOL_VERSION
                if control_session is not None:
                    health["control_session_id"] = control_session
                return health
            except RuntimeWorkerError as exc:
                state = "RUNTIME_UNAVAILABLE"
                if exc.code == "RUNTIME_PROTOCOL_MISMATCH":
                    state = "RUNTIME_PROTOCOL_MISMATCH"
                elif exc.code not in (
                    "RUNTIME_UNAVAILABLE", "RUNTIME_AUTHENTICATION_FAILED", "RUNTIME_REQUEST_TIMEOUT",
                    "RUNTIME_IPC_FAILED",
                ):
                    state = "MT5_ERROR"
                return {
                    "worker_available": False,
                    "runtime_state": state,
                    "last_error_code": exc.code,
                    "protocol_version": PROTOCOL_VERSION,
                    **({"control_session_id": control_session} if control_session is not None else {}),
                }

    def _connect_once(self) -> bool:
        if self._configuration_error:
            raise RuntimeWorkerError("RUNTIME_CONFIGURATION_UNAVAILABLE")
        if self._require_session_zero and self._control_session_id() != 0:
            raise RuntimeWorkerError("RUNTIME_CONTROL_NOT_SESSION_ZERO")
        self._request("handshake", timeout_ms=self._connect_timeout_ms)
        health = self._health_request()
        if health.get("mt5_connected") is not True:
            operation = "reconnect" if health.get("runtime_state") in (
                "MT5_DISCONNECTED", "MT5_RECONNECTING", "MT5_ERROR"
            ) else "initialize_readonly"
            self._request(
                operation,
                timeout_ms=self._initialize_timeout_ms,
            )
            health = self._health_request()
        connected = health.get("runtime_state") == "MT5_CONNECTED" and health.get("mt5_connected") is True
        if connected:
            self._last_error = None
            self._next_retry_at = 0.0
        else:
            self._last_error = str(health.get("last_error_code") or "MT5_NOT_CONNECTED")
            self._runtime_state = str(health.get("runtime_state") or "MT5_DISCONNECTED")
            self._next_retry_at = self._clock() + self._retry_backoff_seconds
        return connected

    def _attempt_connect(self, *, respect_backoff: bool) -> bool:
        if respect_backoff and self._clock() < self._next_retry_at:
            return False
        try:
            connected = self._connect_once()
            if not connected:
                self._next_retry_at = self._clock() + self._retry_backoff_seconds
            return connected
        except RuntimeWorkerError as exc:
            self._last_error = exc.code
            self._runtime_state = "RUNTIME_UNAVAILABLE" if exc.code in (
                "RUNTIME_UNAVAILABLE", "RUNTIME_AUTHENTICATION_FAILED", "RUNTIME_REQUEST_TIMEOUT",
                "RUNTIME_CONFIGURATION_UNAVAILABLE",
            ) else "MT5_ERROR"
            self._health = {
                "worker_available": False,
                "runtime_state": self._runtime_state,
                "mt5_initialized": False,
                "mt5_connected": False,
                "last_error_code": exc.code,
                "protocol_version": PROTOCOL_VERSION,
            }
            if self._require_session_zero:
                self._health["control_session_id"] = self._control_session_id()
            self._next_retry_at = self._clock() + self._retry_backoff_seconds
            return False

    @staticmethod
    def _control_session_id() -> int:
        if os.name != "nt":
            return -1
        import ctypes

        session_id = ctypes.c_uint32()
        if not ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(session_id)):
            return -1
        return int(session_id.value)

    def connect(self) -> bool:
        with self._lock:
            return self._attempt_connect(respect_backoff=False)

    def is_connected(self) -> bool:
        with self._lock:
            if self._runtime_state == "MT5_CONNECTED":
                try:
                    health = self._health_request()
                    connected = health.get("runtime_state") == "MT5_CONNECTED" and health.get("mt5_connected") is True
                    if connected:
                        return True
                    self._next_retry_at = self._clock() + self._retry_backoff_seconds
                    return False
                except RuntimeWorkerError as exc:
                    self._last_error = exc.code
                    self._runtime_state = "RUNTIME_UNAVAILABLE"
                    self._health.update({"worker_available": False, "runtime_state": self._runtime_state, "mt5_connected": False,
                                         "last_error_code": exc.code})
                    self._next_retry_at = self._clock() + self._retry_backoff_seconds
                    return False
            return self._attempt_connect(respect_backoff=True)

    def disconnect(self) -> bool:
        """Detach this control-plane client without stopping the persistent Worker."""
        return True

    def reconnect(self) -> bool:
        with self._lock:
            self._next_retry_at = 0.0
            return self._attempt_connect(respect_backoff=False)

    def runtime_shutdown(self) -> bool:
        """Explicitly release the Worker's API connection without killing its terminal."""
        with self._lock:
            try:
                message = self._request("runtime_shutdown")
                result = message["result"]
                succeeded = result.get("mt5_shutdown_succeeded") is True
                self._runtime_state = str(result.get("runtime_state") or "MT5_NOT_INITIALIZED")
                self._health.update({"runtime_state": self._runtime_state,
                                     "mt5_initialized": result.get("mt5_initialized", False),
                                     "mt5_connected": False})
                return succeeded
            except RuntimeWorkerError as exc:
                self._last_error = exc.code
                return False

    def terminal_information(self) -> dict[str, object]:
        with self._lock:
            if not self.is_connected():
                raise MT5ReadError(self._last_error or "MT5_RUNTIME_UNAVAILABLE", self.health_details)
            return dict(self._health)

    def symbols_total(self) -> int:
        with self._lock:
            if not self.is_connected():
                raise MT5ReadError(self._last_error or "MT5_RUNTIME_UNAVAILABLE", self.health_details)
            try:
                message = self._request("symbols_total")
                value = message["result"].get("value")
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise RuntimeWorkerError("RUNTIME_INVALID_RESPONSE")
                self._health.update({
                    "runtime_state": message["result"].get("runtime_state", "MT5_CONNECTED"),
                    "mt5_connected": True,
                    "last_successful_mt5_operation": "symbols_total",
                    "terminal_pid": message["result"].get("terminal_pid"),
                    "terminal_session_id": message["result"].get("terminal_session_id"),
                })
                return value
            except RuntimeWorkerError as exc:
                self._last_error = exc.code
                self._runtime_state = "MT5_DISCONNECTED" if exc.code.startswith("MT5_") else "RUNTIME_UNAVAILABLE"
                self._health.update({"runtime_state": self._runtime_state,
                                     "mt5_connected": False, "last_error_code": exc.code})
                raise MT5ReadError(exc.code, self.health_details) from None

    def _read_value(self, operation: str, expected_type):
        with self._lock:
            if not self.is_connected():
                raise MT5ReadError(self._last_error or "MT5_RUNTIME_UNAVAILABLE", self.health_details)
            try:
                message = self._request(operation)
                result = message["result"]
                value = result.get("value")
                if not isinstance(value, expected_type) or (expected_type is int and isinstance(value, bool)):
                    raise RuntimeWorkerError("RUNTIME_INVALID_RESPONSE")
                if (result.get("operation") != operation
                        or result.get("runtime_state") != "MT5_CONNECTED"
                        or not isinstance(result.get("terminal_pid"), int)
                        or not isinstance(result.get("terminal_session_id"), int)
                        or result["terminal_pid"] <= 0
                        or result["terminal_session_id"] <= 0):
                    raise RuntimeWorkerError("RUNTIME_INVALID_RESPONSE")
                self._health.update({
                    "runtime_state": result.get("runtime_state", "MT5_CONNECTED"),
                    "mt5_connected": True,
                    "last_successful_mt5_operation": operation,
                    "terminal_pid": result.get("terminal_pid"),
                    "terminal_session_id": result.get("terminal_session_id"),
                })
                return value
            except RuntimeWorkerError as exc:
                self._last_error = exc.code
                if exc.code.startswith(("MT5_", "WORKER_")):
                    self._runtime_state = "MT5_DISCONNECTED" if exc.code != "MT5_NOT_INITIALIZED" else "MT5_NOT_INITIALIZED"
                else:
                    self._runtime_state = "RUNTIME_UNAVAILABLE"
                self._health.update({"runtime_state": self._runtime_state,
                                     "mt5_connected": self._runtime_state == "MT5_CONNECTED",
                                     "last_error_code": exc.code})
                raise MT5ReadError(exc.code, {**self.health_details, **exc.details}) from None

    def terminal_version(self):
        """Return the legacy normalized MetaTrader5.version() payload."""
        return self._read_value("terminal_version", list)

    def account_information(self) -> dict[str, object]:
        """Return the normalized account_info mapping without logging it."""
        return self._read_value("account_information", dict)


class RuntimeWorkerError(RuntimeError):
    def __init__(self, code: str, details: dict[str, object] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.details = details or {}
