"""Opt-in TEST-ONLY Gateway transport owned by the Agent Core host, never MT5."""
from __future__ import annotations

from collections import deque
import json
import logging
import os
from pathlib import Path
NativePath = type(Path())
import random
import re
import ssl
import threading
import time
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from agent.infrastructure.logging_observability import safe_log


def load_settings(path):
    path = NativePath(path)
    if path.stat().st_size > 4096:
        raise ValueError("configuration too large")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if set(data) - {"url", "agent_id", "token_file", "expires_at", "account_read"} or not {"url", "agent_id", "token_file", "expires_at"} <= set(data):
        raise ValueError("invalid configuration")
    uri = urlsplit(data["url"])
    identity = data["agent_id"]
    if (uri.scheme != "wss" or not uri.hostname or uri.username or uri.password
            or uri.query or uri.fragment or uri.path != f"/v1/agents/{identity}/ws"
            or not re.fullmatch(r"[a-z][a-z0-9-]{2,63}", identity)):
        raise ValueError("invalid endpoint or identity")
    if not isinstance(data["expires_at"], (int, float)) or data["expires_at"] <= time.time():
        raise ValueError("credential expired")
    token_path = NativePath(data["token_file"])
    if not token_path.is_absolute() or token_path.stat().st_size > 256:
        raise ValueError("invalid token file")
    token = token_path.read_text(encoding="utf-8-sig").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", token):
        raise ValueError("invalid credential")
    return data, token


def parse_message(text, identity):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate field")
            result[key] = value
        return result
    if not isinstance(text, str) or len(text.encode("utf-8")) > 16384:
        raise ValueError("invalid frame")
    m = json.loads(text, object_pairs_hook=unique)
    if not isinstance(m, dict) or set(m) != {"version", "type", "agent_id", "message_id", "correlation_id", "payload"}:
        raise ValueError("invalid envelope")
    if m["version"] != "1.0" or m["agent_id"] != identity or m["type"] not in {"hello_ack", "ping", "pong", "echo", "disconnect_ack"}:
        raise ValueError("message not authorized")
    for key in ("message_id", "correlation_id"):
        if m[key] is None and key == "correlation_id":
            continue
        if not isinstance(m[key], str) or str(UUID(m[key])) != m[key]:
            raise ValueError("invalid identifier")
    payload = m["payload"]
    if m["type"] == "echo":
        if not isinstance(payload, dict) or set(payload) != {"text"} or not isinstance(payload["text"], str) or len(payload["text"]) > 256:
            raise ValueError("invalid echo")
    elif payload != {}:
        raise ValueError("unexpected payload")
    if m["type"] == "ping" and m["correlation_id"] is not None:
        raise ValueError("unexpected correlation")
    return m


def backoff(attempt, jitter=random.random):
    return min(60.0, 2.0 ** min(attempt, 6)) * (0.75 + 0.25 * jitter())


class GatewayHostingPort:
    """One owned supervisor thread, bounded receive buffer, interruptible retry."""
    def __init__(self, primary, config_path, connector=None, logger=None, account_reader=None):
        self.sampler = None
        if account_reader is not None:
            from agent.infrastructure.account_snapshot import SnapshotSampler
            self.sampler = SnapshotSampler(account_reader.read)
        self.primary = primary
        self.config_path = config_path
        self.connector = connector
        self.logger = logger or logging.getLogger("agent")
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.thread = None
        self.connection = None

    def event(self, name, **fields):
        # Only fixed event names and locally validated IDs/numeric data enter logs.
        safe_log(self.logger, logging.INFO, "%s", json.dumps({
            "event": name, "pid": os.getpid(), **fields}, separators=(",", ":")))

    def serve(self):
        with self.lock:
            if self.thread is not None:
                raise RuntimeError("Gateway host already started")
            self.thread = threading.Thread(target=self.run, name="Agent Core Gateway WSS", daemon=True)
            self.thread.start()
        try:
            self.primary.serve()
        finally:
            self.shutdown()

    def shutdown(self):
        self.stop_event.set()
        with self.lock:
            connection = self.connection
        if connection is not None:
            try:
                connection.close(1000, "service stopping")
            except Exception:
                pass
        self.primary.shutdown()
        if self.thread is not None and self.thread is not threading.current_thread():
            self.thread.join(5)

    def run(self):
        attempt = 0
        while not self.stop_event.is_set():
            started = time.monotonic()
            try:
                settings, token = load_settings(self.config_path)
                connector = self.connector
                if connector is None:
                    from websockets.sync.client import connect
                    connector = connect
                # Library debug logging must never serialize handshake credentials.
                silent = logging.Logger("agent.gateway.wire", level=logging.CRITICAL + 1)
                silent.addHandler(logging.NullHandler())
                with connector(settings["url"], ssl=ssl.create_default_context(),
                               additional_headers={"Authorization": "Bearer " + token},
                               proxy=None, open_timeout=3, close_timeout=1,
                               ping_interval=10, ping_timeout=5, compression=None,
                               max_size=16384, max_queue=8, logger=silent) as ws:
                    del token
                    with self.lock:
                        self.connection = ws
                    if self.stop_event.is_set():
                        break
                    self.session(ws, settings)
            except Exception as exc:
                # No exception messages, URL, headers, token or payload in logs.
                self.event("gateway_connection_ended", error_type=type(exc).__name__)
            finally:
                with self.lock:
                    self.connection = None
            if time.monotonic() - started >= 30:
                attempt = 0
            delay = backoff(attempt)
            attempt += 1
            if not self.stop_event.is_set():
                self.event("gateway_retry", delay_seconds=round(delay, 3))
                self.stop_event.wait(delay)
        self.event("gateway_stopped")

    def session(self, ws, settings):
        identity = settings["agent_id"]
        seen = deque(maxlen=64)
        pending = {}
        def send(kind, correlation=None, payload=None):
            identifier = str(uuid4())
            ws.send(json.dumps({"version": "1.0", "type": kind, "agent_id": identity,
                                "message_id": identifier, "correlation_id": correlation,
                                "payload": payload or {}}))
            self.event("gateway_sent", agent_id=identity, message_type=kind,
                       message_id=identifier, correlation_id=correlation)
            return identifier
        def receive(timeout):
            m = parse_message(ws.recv(timeout=timeout), identity)
            if m["message_id"] in seen:
                raise ValueError("replayed message")
            seen.append(m["message_id"])
            self.event("gateway_received", agent_id=identity, message_type=m["type"],
                       message_id=m["message_id"], correlation_id=m["correlation_id"])
            return m
        hello = send("hello")
        ack = receive(5)
        if ack["type"] != "hello_ack" or ack["correlation_id"] != hello:
            raise ValueError("hello correlation failed")
        self.event("gateway_authenticated", agent_id=identity)
        echo = send("echo", payload={"text": "agent-core-connectivity-test"})
        pending[echo] = ("echo", time.monotonic() + 5)
        ping = send("ping")
        pending[ping] = ("pong", time.monotonic() + 5)
        from agent.infrastructure.account_snapshot import grant
        generation = str(uuid4())
        next_sample = time.monotonic()
        def permission():
            current, _token = load_settings(self.config_path)
            return current["agent_id"] == identity and current["url"] == settings["url"] and grant(current) is not None
        window, count = time.monotonic(), 0
        last = window
        while not self.stop_event.is_set():
            now = time.monotonic()
            if time.time() >= settings["expires_at"] or now - last >= 25 or any(now >= p[1] for p in pending.values()):
                raise TimeoutError("response or credential timeout")
            if self.sampler is not None:
                current, _token = load_settings(self.config_path)
                interval = grant(current) if permission() else None
                snapshot = self.sampler.take(generation)
                if interval is not None and snapshot is not None:
                    send("account_snapshot", payload=snapshot)
                if interval is not None and now >= next_sample:
                    self.sampler.start(generation, permission)
                    next_sample = now + interval
            try:
                m = receive(0.5)
            except TimeoutError:
                continue
            now = time.monotonic()
            if now - window >= 1:
                window, count = now, 0
            count += 1
            if count > 20:
                raise ValueError("rate exceeded")
            last = now
            if m["type"] == "ping":
                send("pong", m["message_id"])
            else:
                expected = pending.pop(m["correlation_id"], None)
                if expected is None or expected[0] != m["type"]:
                    raise ValueError("unsolicited response")
                if m["type"] == "echo" and m["payload"] != {"text": "agent-core-connectivity-test"}:
                    raise ValueError("echo mismatch")
                self.event("gateway_round_trip", agent_id=identity, message_type=m["type"],
                           correlation_id=m["correlation_id"])


def configured_gateway_host(primary, dispatcher=None):
    # Automatic machine configuration belongs only to the real Service-owned Core.
    # CLI/CI candidate processes must opt in explicitly, avoiding duplicate identities.
    if not os.environ.get("MT5_AGENT_GATEWAY_CONFIG") and not os.environ.get("MT5_AGENT_SHUTDOWN_EVENT"):
        return primary
    default = NativePath(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "MT5Agent/Gateway/config.json"
    path = NativePath(os.environ.get("MT5_AGENT_GATEWAY_CONFIG", str(default)))
    if not path.exists():
        return primary
    reader = None
    if dispatcher is not None:
        from agent.infrastructure.account_snapshot import AuthorizedAccountReader, grant
        reader = AuthorizedAccountReader(dispatcher, lambda: grant(load_settings(path)[0]) is not None)
    return GatewayHostingPort(primary, path, account_reader=reader)
