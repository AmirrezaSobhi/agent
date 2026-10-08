"""Versioned, read-only management Named Pipe; separate from the MT5 Worker pipe."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
import ctypes
from datetime import datetime, timezone
from ctypes import wintypes
from typing import Callable

from agent.infrastructure.logging_observability import safe_log

PIPE_NAME = r"\\.\pipe\MT5Agent.Management.v1"
PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 65_536
REQUEST_TIMEOUT_MS = 2_000
ERROR_ACCESS_DENIED = 5
ERROR_BROKEN_PIPE = 109
ERROR_NO_DATA = 232
ERROR_MORE_DATA = 234
ERROR_PIPE_CONNECTED = 535


class ManagementProtocolError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class CallerIdentityError(PermissionError):
    pass


def _required_uuid(value: object) -> str:
    if not isinstance(value, str) or len(value) > 64:
        raise ManagementProtocolError("INVALID_REQUEST")
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise ManagementProtocolError("INVALID_REQUEST") from None


def parse_request(raw: bytes, *, max_bytes: int = MAX_MESSAGE_BYTES) -> dict[str, object]:
    if not isinstance(raw, bytes) or not raw or len(raw) > max_bytes:
        code = "MESSAGE_TOO_LARGE" if isinstance(raw, bytes) and len(raw) > max_bytes else "INVALID_REQUEST"
        raise ManagementProtocolError(code)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ManagementProtocolError("INVALID_REQUEST") from None
    if not isinstance(value, dict):
        raise ManagementProtocolError("INVALID_REQUEST")
    if value.get("protocol_version") != PROTOCOL_VERSION:
        raise ManagementProtocolError("PROTOCOL_MISMATCH")
    operation = value.get("operation")
    if operation not in ("protocol.negotiate", "status.get"):
        raise ManagementProtocolError("UNSUPPORTED_OPERATION")
    request_id = _required_uuid(value.get("request_id"))
    correlation_id = _required_uuid(value.get("correlation_id"))
    payload = value.get("payload", {})
    if not isinstance(payload, dict):
        raise ManagementProtocolError("INVALID_REQUEST")
    return {"protocol_version": PROTOCOL_VERSION, "request_id": request_id,
            "correlation_id": correlation_id, "operation": operation, "payload": payload}


def encode_message(value: dict[str, object], *, max_bytes: int = MAX_MESSAGE_BYTES) -> bytes:
    try:
        raw = json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError):
        raise ManagementProtocolError("SERIALIZATION_FAILED") from None
    if not raw or len(raw) > max_bytes:
        raise ManagementProtocolError("MESSAGE_TOO_LARGE")
    return raw


_ERROR_MESSAGES = {
    "INVALID_REQUEST": "The request is invalid.",
    "PROTOCOL_MISMATCH": "The management protocol version is not supported.",
    "UNSUPPORTED_OPERATION": "The requested operation is not available.",
    "UNAUTHORIZED": "This Windows user is not authorized for management status.",
    "MESSAGE_TOO_LARGE": "The request exceeds the 64 KiB limit.",
    "BUSY": "The management channel is busy. Retry shortly.",
    "TIMEOUT": "The management request timed out.",
    "INTERNAL_ERROR": "The management request failed.",
}


def error_response(request_id: str = "", correlation_id: str = "", code: str = "INTERNAL_ERROR") -> dict[str, object]:
    return {"protocol_version": PROTOCOL_VERSION, "request_id": request_id,
            "correlation_id": correlation_id, "result": "error", "code": code,
            "message": _ERROR_MESSAGES.get(code, "Management request failed."),
            "observed_at_utc": None, "data": {}}


def build_status(agent) -> dict[str, object]:
    """Project only health fields observed by the Agent and its Worker adapter.

    The Agent cannot independently query the Windows Service Control Manager,
    so service state is deliberately UNKNOWN. A successful response proves the
    Agent process is responsive, but does not prove the service registration
    or the caller's trading authorization.
    """
    health = agent.health()
    runtime = health.runtime if isinstance(health.runtime, dict) else {}
    lifecycle = getattr(health.state, "value", str(health.state)).upper()
    runtime_state = health.runtime_state if isinstance(health.runtime_state, str) else "UNKNOWN"
    worker_available = runtime.get("worker_available")
    if worker_available is True:
        worker_state = runtime.get("worker_state") if isinstance(runtime.get("worker_state"), str) else "READY"
    elif worker_available is False:
        worker_state = "DISCONNECTED"
    else:
        worker_state = "UNKNOWN"
    mt5_connected = runtime.get("mt5_connected")
    if mt5_connected is True:
        mt5_state = "CONNECTED"
    elif runtime_state in ("MT5_INITIALIZING", "MT5_RECONNECTING", "INITIALIZING", "RECONNECTING"):
        mt5_state = "INITIALIZING"
    elif runtime_state in ("MT5_ERROR", "RUNTIME_CONFIGURATION_UNAVAILABLE", "RUNTIME_PROTOCOL_MISMATCH"):
        mt5_state = "ERROR"
    elif mt5_connected is False:
        mt5_state = "DISCONNECTED"
    else:
        mt5_state = "UNKNOWN"
    last_error = runtime.get("last_error_code")
    if not isinstance(last_error, str) or len(last_error) > 96:
        last_error = None
    return {
        "service_state": "UNKNOWN",
        "agent_state": "AGENT_RUNNING" if lifecycle == "RUNNING" else "AGENT_" + lifecycle,
        "agent_lifecycle_state": lifecycle,
        "worker_available": worker_available if isinstance(worker_available, bool) else None,
        "worker_state": worker_state,
        "runtime_state": runtime_state,
        "mt5_state": mt5_state,
        "mt5_connected": mt5_connected if isinstance(mt5_connected, bool) else None,
        "central_state": "NOT_CONFIGURED",
        "trading_capability": "UNSUPPORTED",
        "trading_authorized": "UNKNOWN",
        "trading_readiness": "UNAVAILABLE",
        "source_identity": "MT5Agent.AgentCore",
        "freshness": "FRESH",
        "error_code": last_error,
        "observed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def redact_sid(sid: str) -> str:
    return "SID_REDACTED"


class ManagementNamedPipeServer:
    """Bounded single-request server with OS-token identity and default-deny authorization."""

    def __init__(self, status_provider: Callable[[], dict[str, object]], allowed_user_sids: tuple[str, ...],
                 logger: logging.Logger | None = None) -> None:
        self._status_provider = status_provider
        self._allowed_sids = frozenset(allowed_user_sids)
        self._logger = logger or logging.getLogger(__name__)
        self._stopping = threading.Event()
        self._fatal_identity_failure = False
        if os.name == "nt" and self._allowed_sids:
            self._validate_sids()

    @property
    def enabled(self) -> bool:
        return os.name == "nt" and bool(self._allowed_sids)

    def _modules(self):
        import win32api
        import win32con
        import win32file
        import win32pipe
        import win32security
        return win32api, win32con, win32file, win32pipe, win32security

    def _validate_sids(self) -> None:
        *_, security = self._modules()
        try:
            for sid in self._allowed_sids:
                security.ConvertStringSidToSid(sid)
        except Exception:
            raise ValueError("MANAGEMENT_ALLOWLIST_CONTAINS_INVALID_SID") from None

    def _security_attributes(self):
        win32api, con, _, _, security = self._modules()
        process_token = security.OpenProcessToken(win32api.GetCurrentProcess(), con.TOKEN_QUERY)
        try:
            service_sid = security.GetTokenInformation(process_token, security.TokenUser)[0]
        finally:
            win32api.CloseHandle(process_token)
        acl = security.ACL()
        acl.AddAccessAllowedAce(security.ACL_REVISION, con.GENERIC_ALL, service_sid)
        # Client gets data/attribute access only; it cannot create pipe instances.
        file_generic_read = 0x00120089
        file_generic_write_without_create_instance = 0x00120116 & ~0x00000004
        client_rights = file_generic_read | file_generic_write_without_create_instance
        for sid_text in sorted(self._allowed_sids):
            acl.AddAccessAllowedAce(security.ACL_REVISION, client_rights,
                                    security.ConvertStringSidToSid(sid_text))
        descriptor = security.SECURITY_DESCRIPTOR()
        descriptor.SetSecurityDescriptorDacl(1, acl, 0)
        attributes = security.SECURITY_ATTRIBUTES()
        attributes.SECURITY_DESCRIPTOR = descriptor
        self._security_objects = (acl, descriptor, attributes)
        return attributes

    def _create_pipe(self, first: bool):
        _, _, _, pipe, _ = self._modules()
        access = pipe.PIPE_ACCESS_DUPLEX | (0x00080000 if first else 0)
        mode = pipe.PIPE_TYPE_MESSAGE | pipe.PIPE_READMODE_MESSAGE | pipe.PIPE_WAIT | 0x00000008
        return pipe.CreateNamedPipe(PIPE_NAME, access, mode, 1, MAX_MESSAGE_BYTES,
                                    MAX_MESSAGE_BYTES, 1000, self._security_attributes())

    @staticmethod
    def _available_bytes(handle) -> int:
        available = wintypes.DWORD()
        peek = ctypes.windll.kernel32.PeekNamedPipe
        peek.argtypes = (wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                         wintypes.LPDWORD, wintypes.LPDWORD, wintypes.LPDWORD)
        peek.restype = wintypes.BOOL
        if not peek(wintypes.HANDLE(int(handle)), None, 0, None, ctypes.byref(available), None):
            error = ctypes.get_last_error()
            if error in (ERROR_NO_DATA, ERROR_BROKEN_PIPE):
                return 0
            raise OSError(error, "PeekNamedPipe failed")
        return int(available.value)

    def _read_request(self, handle) -> bytes:
        _, _, file, pipe, _ = self._modules()
        pipe.SetNamedPipeHandleState(handle, 0x00000002 | 0x00000001, None, None)
        deadline = time.monotonic() + REQUEST_TIMEOUT_MS / 1000
        while time.monotonic() < deadline and not self._stopping.is_set():
            if self._available_bytes(handle) == 0:
                self._stopping.wait(0.025)
                continue
            try:
                _, raw = file.ReadFile(handle, MAX_MESSAGE_BYTES + 1)
                return raw
            except Exception as exc:
                code = getattr(exc, "winerror", None)
                if code == ERROR_MORE_DATA:
                    raise ManagementProtocolError("MESSAGE_TOO_LARGE") from None
                if code != ERROR_NO_DATA:
                    raise
                self._stopping.wait(0.025)
        if self._stopping.is_set():
            raise ManagementProtocolError("SERVICE_STOPPING")
        raise ManagementProtocolError("TIMEOUT")

    def _read_ack(self, handle, request_id: str) -> None:
        _, _, file, _, _ = self._modules()
        deadline = time.monotonic() + REQUEST_TIMEOUT_MS / 1000
        while time.monotonic() < deadline and not self._stopping.is_set():
            if self._available_bytes(handle) == 0:
                self._stopping.wait(0.025)
                continue
            try:
                _, raw = file.ReadFile(handle, 512)
                value = json.loads(raw.decode("utf-8"))
                ack = value.get("ack") if isinstance(value, dict) else None
                if not isinstance(ack, str) or (request_id and ack != request_id):
                    raise ManagementProtocolError("ACK_MISMATCH")
                if not request_id:
                    uuid.UUID(ack)
                return
            except ManagementProtocolError:
                raise
            except Exception as exc:
                if getattr(exc, "winerror", None) != ERROR_NO_DATA:
                    raise
                self._stopping.wait(0.025)
        if self._stopping.is_set():
            raise ManagementProtocolError("SERVICE_STOPPING")
        raise ManagementProtocolError("ACK_TIMEOUT")

    def _caller_sid(self, handle) -> str:
        win32api, con, _, _, security = self._modules()
        impersonated = False
        token = None
        try:
            security.ImpersonateNamedPipeClient(handle)
            impersonated = True
            token = security.OpenThreadToken(win32api.GetCurrentThread(), con.TOKEN_QUERY, True)
            sid = security.GetTokenInformation(token, security.TokenUser)[0]
            return security.ConvertSidToStringSid(sid)
        except Exception:
            raise CallerIdentityError("CALLER_IDENTITY_UNAVAILABLE") from None
        finally:
            token_close_failed = False
            if token is not None:
                try:
                    win32api.CloseHandle(token)
                except Exception:
                    token_close_failed = True
            if impersonated:
                try:
                    security.RevertToSelf()
                except Exception:
                    self._fatal_identity_failure = True
                    raise CallerIdentityError("IMPERSONATION_REVERT_FAILED") from None
            if token_close_failed:
                raise CallerIdentityError("CLIENT_TOKEN_CLOSE_FAILED") from None

    @staticmethod
    def _correlation_ids(raw: bytes) -> tuple[str, str]:
        try:
            value = json.loads(raw.decode("utf-8"))
            return _required_uuid(value.get("request_id")), _required_uuid(value.get("correlation_id"))
        except Exception:
            return str(uuid.uuid4()), str(uuid.uuid4())

    def _handle(self, raw: bytes, caller_sid: str) -> tuple[dict[str, object], str]:
        request_id, correlation_id = self._correlation_ids(raw)
        try:
            request = parse_request(raw)
            request_id, correlation_id = request["request_id"], request["correlation_id"]
            operation = request["operation"]
            if caller_sid not in self._allowed_sids:
                return error_response(request_id, correlation_id, "UNAUTHORIZED"), operation
            if operation == "protocol.negotiate":
                data = {"supported_versions": [PROTOCOL_VERSION], "pipe": PIPE_NAME}
            else:
                data = self._status_provider()
            response = {"protocol_version": PROTOCOL_VERSION, "request_id": request_id,
                        "correlation_id": correlation_id, "result": "ok", "code": "OK",
                        "message": "Status observed.", "observed_at_utc": data.get("observed_at_utc"), "data": data}
            return response, operation
        except ManagementProtocolError as exc:
            return error_response(request_id, correlation_id, exc.code), "invalid"
        except Exception:
            return error_response(request_id, correlation_id, "INTERNAL_ERROR"), "status.get"

    def _write_response(self, handle, response: dict[str, object]) -> None:
        _, _, file, _, _ = self._modules()
        file.WriteFile(handle, encode_message(response))

    def serve(self) -> None:
        if not self.enabled:
            safe_log(self._logger, logging.WARNING,
                     "Management pipe disabled: explicit local SID allowlist is not configured")
            return
        first = True
        while not self._stopping.is_set() and not self._fatal_identity_failure:
            server = self._create_pipe(first)
            first = False
            _, _, file, pipe, _ = self._modules()
            try:
                try:
                    pipe.ConnectNamedPipe(server, None)
                except Exception as exc:
                    if getattr(exc, "winerror", None) != ERROR_PIPE_CONNECTED:
                        raise
                if self._stopping.is_set():
                    continue
                raw = self._read_request(server)
                caller_sid = self._caller_sid(server)
                response, operation = self._handle(raw, caller_sid)
                self._write_response(server, response)
                self._read_ack(server, response["request_id"])
                safe_log(self._logger, logging.INFO,
                         "Management request correlation=%s actor=%s operation=%s code=%s",
                         response.get("correlation_id", "unknown"), redact_sid(caller_sid), operation,
                         response.get("code", "unknown"))
            except ManagementProtocolError as exc:
                if exc.code not in ("SERVICE_STOPPING",):
                    try:
                        response = error_response(code=exc.code)
                        self._write_response(server, response)
                        self._read_ack(server, "")
                    except Exception:
                        pass
            except CallerIdentityError:
                safe_log(self._logger, logging.ERROR, "Management client identity verification failed closed")
            except Exception as exc:
                safe_log(self._logger, logging.WARNING, "Management pipe request failed type=%s", type(exc).__name__)
            finally:
                try:
                    pipe.DisconnectNamedPipe(server)
                except Exception:
                    pass
                file.CloseHandle(server)
        if self._fatal_identity_failure:
            safe_log(self._logger, logging.CRITICAL,
                     "Management pipe stopped after impersonation restoration failure")

    def shutdown(self) -> None:
        self._stopping.set()
        if not self.enabled:
            return
        _, con, file, _, _ = self._modules()
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:
            try:
                handle = file.CreateFile(PIPE_NAME, con.GENERIC_READ | con.GENERIC_WRITE, 0, None,
                                         con.OPEN_EXISTING, 0, None)
                file.CloseHandle(handle)
                return
            except Exception:
                time.sleep(0.025)
