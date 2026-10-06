"""Authenticated, versioned request contract for the local MT5 Worker."""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from enum import Enum
from hmac import compare_digest
from threading import Lock


PROTOCOL_VERSION = "1"
MAX_REQUEST_ID_LENGTH = 128


class WorkerState(str, Enum):
    NOT_PRESENT = "WORKER_MISSING"
    STARTING = "WORKER_STARTING"
    READY = "WORKER_READY"
    DEGRADED = "MT5_RUNTIME_UNHEALTHY"
    STOPPING = "WORKER_STOPPING"
    STOPPED = "WORKER_STOPPED"
    FAILED = "WORKER_FAILED"


@dataclass(frozen=True)
class WorkerIdentity:
    instance_id: str
    pid: int
    session_id: int
    account: str
    started_at: str
    sid: str = ""
    protocol_version: str = PROTOCOL_VERSION

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class RuntimeWorkerProtocol:
    """Accept only bounded read-only Worker operations from an OS-verified client."""

    OPERATIONS = frozenset({
        "handshake",
        "health",
        "initialize_readonly",
        "reconnect",
        "symbols_total",
        "terminal_version",
        "account_information",
        "runtime_shutdown",
        "shutdown",
    })

    def __init__(self, token, identity: WorkerIdentity, handler=None, *, max_request_bytes: int = 65_536, max_seen: int = 4096):
        if max_request_bytes < 1 or max_seen < 1:
            raise ValueError("IPC_LIMITS_MUST_BE_POSITIVE")
        # ``token`` retains source compatibility for the original protocol tests.
        # Production uses OS-authenticated pipe ACLs and passes token=None.
        self._token = token
        self.identity = identity
        self.state = WorkerState.STARTING
        self._handler = handler or (lambda operation: {"operation": operation})
        self._max_request_bytes = max_request_bytes
        self._max_seen = max_seen
        self._seen: set[str] = set()
        self._seen_order: deque[str] = deque()
        self._seen_lock = Lock()

    def handle(
        self,
        envelope: object,
        *,
        client_principal: str | None = None,
        client_sid: str | None = None,
        client_session_id: int | None = None,
        expected_client_principal: str | None = None,
        expected_client_sid: str | None = None,
    ) -> dict[str, object]:
        if expected_client_sid is not None:
            if client_sid is None or not compare_digest(client_sid.casefold(), expected_client_sid.casefold()):
                return {"ok": False, "code": "IPC_AUTHENTICATION_FAILED"}
        if expected_client_principal is not None:
            if client_principal is None or client_principal.casefold() != expected_client_principal.casefold():
                return {"ok": False, "code": "IPC_AUTHENTICATION_FAILED"}
            if client_session_id != 0:
                return {"ok": False, "code": "IPC_CALLER_NOT_SESSION_ZERO"}
        if not isinstance(envelope, dict):
            return {"ok": False, "code": "IPC_INVALID_REQUEST"}
        expected_fields = {"version", "request_id", "operation"}
        if self._token is not None:
            expected_fields.add("token")
        if set(envelope) != expected_fields:
            return {"ok": False, "code": "IPC_INVALID_REQUEST_FIELDS"}
        if self._token is not None and not compare_digest(str(envelope.get("token", "")), self._token):
            return {"ok": False, "code": "IPC_AUTHENTICATION_FAILED"}
        if len(str(envelope).encode("utf-8")) > self._max_request_bytes:
            return {"ok": False, "code": "IPC_REQUEST_TOO_LARGE"}
        if envelope.get("version") != PROTOCOL_VERSION:
            return {"ok": False, "code": "IPC_UNSUPPORTED_VERSION"}
        request_id = envelope.get("request_id")
        if not isinstance(request_id, str) or not request_id or len(request_id) > MAX_REQUEST_ID_LENGTH:
            return {"ok": False, "code": "IPC_INVALID_REQUEST_ID"}
        operation = envelope.get("operation")
        if not isinstance(operation, str) or operation not in self.OPERATIONS:
            return {"ok": False, "code": "IPC_UNSUPPORTED_OPERATION"}
        with self._seen_lock:
            if request_id in self._seen:
                return {"ok": False, "code": "IPC_DUPLICATE_REQUEST"}
            # Keep a bounded sliding replay window so the long-running Worker
            # remains usable beyond max_seen lifetime requests.
            if len(self._seen_order) >= self._max_seen:
                expired = self._seen_order.popleft()
                self._seen.discard(expired)
            # Mark before dispatch: the same request cannot replay after losing
            # a response while it remains inside the bounded window.
            self._seen_order.append(request_id)
            self._seen.add(request_id)
        try:
            result = self._handler(operation)
        except Exception as exc:
            error_code = str(exc.args[0]) if isinstance(exc, RuntimeError) and exc.args else "WORKER_OPERATION_FAILED"
            response = {"ok": False, "code": error_code, "error_type": type(exc).__name__}
            details = getattr(exc, "details", None)
            if isinstance(details, dict):
                # Error diagnostics are separate from operation values; account
                # information is never copied into an error response.
                response["details"] = details
            return response
        if operation == "handshake":
            self.state = WorkerState.READY
        elif operation == "shutdown":
            self.state = WorkerState.STOPPING
        elif self.state == WorkerState.STARTING:
            # A successful authenticated request proves the pipe server is
            # accepting work even if the caller did not send a handshake first.
            self.state = WorkerState.READY
        return {
            "ok": True,
            "version": PROTOCOL_VERSION,
            "request_id": request_id,
            "worker": self.identity.to_dict(),
            "state": self.state.value,
            "result": result,
        }


def valid_message(raw: bytes, *, max_bytes: int = 65_536) -> dict[str, object]:
    """Decode one bounded UTF-8 JSON object without accepting duplicate keys."""
    import json

    if not raw or len(raw) > max_bytes:
        raise ValueError("IPC_REQUEST_TOO_LARGE")

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("IPC_DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("IPC_INVALID_JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("IPC_INVALID_REQUEST")
    return value


class SingleWorkerLease:
    """Compatibility lease retained for callers of the original worker contract."""

    def __init__(self):
        self._identity = None

    def acquire(self, identity: WorkerIdentity) -> None:
        if self._identity is not None:
            raise RuntimeError("WORKER_ALREADY_LEASED")
        self._identity = identity

    def release(self, identity: WorkerIdentity) -> None:
        if self._identity != identity:
            raise RuntimeError("WORKER_OWNERSHIP_MISMATCH")
        self._identity = None
