"""Authenticated local Windows Named Pipe transport for the MT5 Worker."""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Callable


PIPE_NAME = r"\\.\pipe\MT5Agent.Runtime.v1"
MAX_MESSAGE_BYTES = 65_536
PIPE_REJECT_REMOTE_CLIENTS = 0x00000008
PIPE_NOWAIT = 0x00000001
PIPE_READMODE_MESSAGE = 0x00000002

_WIN32_ERROR_NAMES = {
    2: "ERROR_FILE_NOT_FOUND",
    5: "ERROR_ACCESS_DENIED",
    6: "ERROR_INVALID_HANDLE",
    109: "ERROR_BROKEN_PIPE",
    1008: "ERROR_NO_TOKEN",
    1314: "ERROR_PRIVILEGE_NOT_HELD",
    1368: "ERROR_CANNOT_IMPERSONATE",
    233: "ERROR_PIPE_NOT_CONNECTED",
    234: "ERROR_MORE_DATA",
    536: "ERROR_PIPE_CONNECTED",
}


def win32_error_details(exc: BaseException) -> dict[str, object]:
    """Expose only the numeric Win32 failure and its stable symbolic name."""
    code = getattr(exc, "winerror", None)
    if not isinstance(code, int) or code <= 0:
        args = getattr(exc, "args", ())
        code = args[0] if args and isinstance(args[0], int) and args[0] > 0 else None
    if code is None:
        return {}
    details: dict[str, object] = {
        "win32_error_code": code,
        "win32_error_name": _WIN32_ERROR_NAMES.get(code, "WIN32_ERROR_UNKNOWN"),
    }
    stage = getattr(exc, "auth_stage", None)
    if isinstance(stage, str):
        details["auth_stage"] = stage
    return details


def _win32_code(exc: BaseException) -> int | None:
    code = getattr(exc, "winerror", None)
    if isinstance(code, int) and code > 0:
        return code
    args = getattr(exc, "args", ())
    return args[0] if args and isinstance(args[0], int) and args[0] > 0 else None


def _single_control_principal(principals: tuple[str, ...]) -> str:
    if len(principals) != 1 or not principals[0].strip():
        raise ValueError("PIPE_SERVER_REQUIRES_EXACTLY_ONE_CONTROL_PRINCIPAL")
    return principals[0]


class PipePeerAuthenticationError(Exception):
    """A sanitized failure from one kernel-backed peer-authentication step."""

    def __init__(self, stage: str, code: int | None):
        self.auth_stage = stage
        self.winerror = code
        super().__init__(code if code is not None else 0)


@dataclass(frozen=True)
class PipePeer:
    process_id: int
    session_id: int
    principal: str
    sid: str
    authentication_method: str = "exclusive_pipe_dacl"


class WindowsNamedPipe:
    """A local message pipe authenticated by its exclusive configured-client DACL."""

    def __init__(self, name: str = PIPE_NAME, *, allowed_principals: tuple[str, ...] = ()):
        if os.name != "nt":
            raise OSError("Windows named pipes are available only on Windows")
        if not name.startswith("\\\\.\\pipe\\") or ".." in name:
            raise ValueError("pipe must use a local named-pipe path")
        # Client-only instances need no ACL policy.  Server creation still
        # requires exactly one configured principal before creating the pipe.
        self.path = name
        self.allowed_principals = tuple(allowed_principals)

    @staticmethod
    def _modules():
        import ctypes
        import win32api
        import win32con
        import win32file
        import win32pipe
        import win32security

        return ctypes, win32api, win32con, win32file, win32pipe, win32security

    def _security_attributes(self):
        _, _, win32con, _, _, security = self._modules()
        acl = security.ACL()
        access = win32con.GENERIC_READ | win32con.GENERIC_WRITE
        for principal in self.allowed_principals:
            sid, _, _ = security.LookupAccountName(None, principal)
            acl.AddAccessAllowedAce(security.ACL_REVISION, access, sid)
        descriptor = security.SECURITY_DESCRIPTOR()
        descriptor.SetSecurityDescriptorDacl(1, acl, 0)
        attributes = security.SECURITY_ATTRIBUTES()
        attributes.SECURITY_DESCRIPTOR = descriptor
        # Keep these alive for the complete CreateNamedPipe call.
        self._security_objects = (acl, descriptor, attributes)
        return attributes

    def create_server(self, *, first_instance: bool = False):
        _single_control_principal(self.allowed_principals)
        _, _, con, _, pipe, _ = self._modules()
        access = pipe.PIPE_ACCESS_DUPLEX
        if first_instance:
            access |= getattr(con, "FILE_FLAG_FIRST_PIPE_INSTANCE", 0x00080000)
        mode = (
            pipe.PIPE_TYPE_MESSAGE
            | pipe.PIPE_READMODE_MESSAGE
            | pipe.PIPE_WAIT
            | PIPE_REJECT_REMOTE_CLIENTS
        )
        return pipe.CreateNamedPipe(
            self.path,
            access,
            mode,
            1,
            MAX_MESSAGE_BYTES,
            MAX_MESSAGE_BYTES,
            5_000,
            self._security_attributes(),
        )

    @staticmethod
    def _client_session(handle) -> int:
        ctypes, *_ = WindowsNamedPipe._modules()
        session = ctypes.c_uint32()
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        get_client_session = kernel.GetNamedPipeClientSessionId
        get_client_session.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        get_client_session.restype = ctypes.c_int
        if not get_client_session(ctypes.c_void_p(int(handle)), ctypes.byref(session)):
            raise PipePeerAuthenticationError("get_named_pipe_client_session_id", ctypes.get_last_error())
        return int(session.value)

    def peer(self, handle) -> PipePeer:
        _, _, _, _, pipe, security = self._modules()
        principal = _single_control_principal(self.allowed_principals)
        try:
            pid = int(pipe.GetNamedPipeClientProcessId(handle))
        except Exception as exc:
            raise PipePeerAuthenticationError("get_named_pipe_client_pid", _win32_code(exc)) from None
        session_id = self._client_session(handle)
        # The server DACL contains exactly one ACE: the configured ControlPrincipal
        # SID. Windows performs the client's token SID access check when it opens
        # the pipe. The name/SID below identify that ACL policy, not a protocol claim.
        sid, _, _ = security.LookupAccountName(None, principal)
        sid_text = security.ConvertSidToStringSid(sid)
        return PipePeer(
            process_id=pid,
            session_id=session_id,
            principal=principal,
            sid=sid_text,
        )

    @staticmethod
    def _write(handle, value: dict[str, object]) -> None:
        _, _, _, file, _, _ = WindowsNamedPipe._modules()
        raw = json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        if not raw or len(raw) > MAX_MESSAGE_BYTES:
            raise ValueError("IPC_RESPONSE_TOO_LARGE")
        file.WriteFile(handle, raw)

    @staticmethod
    def _read(handle, *, timeout_ms: int = 5_000, set_nowait: bool = True) -> dict[str, object]:
        _, _, _, file, pipe, _ = WindowsNamedPipe._modules()
        from agent.application.runtime_worker import valid_message
        if set_nowait:
            pipe.SetNamedPipeHandleState(handle, PIPE_READMODE_MESSAGE | PIPE_NOWAIT, None, None)
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            try:
                _, raw = file.ReadFile(handle, MAX_MESSAGE_BYTES)
                return valid_message(raw, max_bytes=MAX_MESSAGE_BYTES)
            except Exception as exc:
                code = getattr(exc, "winerror", None)
                if code == 234:
                    raise ValueError("IPC_REQUEST_TOO_LARGE") from None
                if code != 232:  # ERROR_NO_DATA while a message is incomplete/not sent yet.
                    raise
                time.sleep(0.025)
        raise TimeoutError("IPC_REQUEST_TIMEOUT")

    def serve_forever(self, dispatch: Callable[[dict[str, object], PipePeer], dict[str, object]]) -> None:
        _, _, _, file, pipe, _ = self._modules()
        first = True
        while True:
            server = self.create_server(first_instance=first)
            first = False
            try:
                try:
                    pipe.ConnectNamedPipe(server, None)
                except Exception as exc:
                    if getattr(exc, "winerror", None) != 535:  # client raced ConnectNamedPipe
                        raise
                request = self._read(server)
                # Consume the bounded request before evaluating kernel pipe
                # metadata and dispatching under the exclusive DACL policy.
                peer = self.peer(server)
                try:
                    response = dispatch(request, peer)
                except Exception as exc:
                    response = {"ok": False, "code": "IPC_DISPATCH_FAILED", "error_type": type(exc).__name__}
                self._write(server, response)
                request_id = request.get("request_id")
                if isinstance(request_id, str):
                    acknowledgement = self._read(server, timeout_ms=5_000)
                    if acknowledgement != {"ack": request_id}:
                        raise ValueError("IPC_RESPONSE_ACK_MISMATCH")
                if response.get("stop_worker") is True:
                    break
            except Exception as exc:
                # A malformed/unauthorized local client cannot terminate the Worker.
                try:
                    self._write(server, {
                        "ok": False,
                        "code": "IPC_REQUEST_REJECTED",
                        "error_type": type(exc).__name__,
                        **win32_error_details(exc),
                    })
                except Exception:
                    pass
                time.sleep(0.025)
            finally:
                try:
                    pipe.DisconnectNamedPipe(server)
                except Exception:
                    pass
                file.CloseHandle(server)

    def request(self, envelope: dict[str, object], *, timeout_ms: int = 3_000) -> dict[str, object]:
        _, _, con, file, pipe, _ = self._modules()
        if not 1 <= timeout_ms <= 120_000:
            raise ValueError("IPC_TIMEOUT_OUT_OF_RANGE")
        deadline = time.monotonic() + timeout_ms / 1000
        last_error = None
        while time.monotonic() < deadline:
            try:
                handle = file.CreateFile(
                    self.path,
                    con.GENERIC_READ | con.GENERIC_WRITE,
                    0,
                    None,
                    con.OPEN_EXISTING,
                    0,
                    None,
                )
                break
            except Exception as exc:
                last_error = exc
                if getattr(exc, "winerror", None) not in (2, 231):  # missing or busy
                    raise
                time.sleep(0.05)
        else:
            raise TimeoutError("WORKER_UNAVAILABLE") from last_error
        request_id = envelope.get("request_id") or str(uuid.uuid4())
        try:
            pipe.SetNamedPipeHandleState(handle, PIPE_READMODE_MESSAGE | PIPE_NOWAIT, None, None)
            self._write(handle, {**envelope, "request_id": request_id})
            response = self._read(handle, timeout_ms=timeout_ms, set_nowait=False)
            self._write(handle, {"ack": request_id})
            return response
        finally:
            file.CloseHandle(handle)
