"""Explicitly granted, bounded read-only telemetry through ApplicationBoundary."""
import math
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from agent.application.boundary import ApplicationBoundary
from agent.application.identity import IdentityAuthority
from agent.contracts.models import Command
from agent.contracts.security import AuthorizationDecision
from agent.contracts.transport import ExecutionContext, TransportRequest


@dataclass(frozen=True)
class ReadRequest(TransportRequest):
    credential: str = field(repr=False)


def grant(settings):
    value = settings.get('account_read')
    if not isinstance(value, dict) or set(value) - {'permission', 'expires_at', 'interval_seconds'}:
        return None
    expiry = value.get('expires_at')
    interval = value.get('interval_seconds', 15)
    if (value.get('permission') != 'account-read' or type(expiry) not in (int, float)
            or not math.isfinite(expiry) or not time.time() < expiry <= settings['expires_at']
            or type(interval) not in (int, float) or not math.isfinite(interval)
            or not 5 <= interval <= 300):
        return None
    return interval


class AccountReadAuthority(IdentityAuthority):
    def __init__(self, permitted):
        super().__init__()
        self.permitted = permitted

    def authorize(self, context, command):
        if not self.permitted():
            return AuthorizationDecision(False, 'authorization_denied')
        return super().authorize(context, command)


class AuthorizedAccountReader:
    def __init__(self, dispatcher, permitted):
        self.authority = AccountReadAuthority(permitted)
        self._token = secrets.token_urlsafe(32)
        self.authority.enroll('local-wss-account-reader', self._token, {'account-read'})
        self.boundary = ApplicationBoundary(dispatcher, self.authority, self.authority)

    def read(self):
        correlation = str(uuid4())
        command = Command(str(uuid4()), 'mt5.get_account_information', '1', correlation,
                          datetime.now(timezone.utc).isoformat(), {})
        response = self.boundary.handle(ReadRequest(
            ExecutionContext(str(uuid4()), correlation, {}), command, self._token))
        if not response.success or not isinstance(response.data, dict):
            raise ValueError('account read denied')
        result = response.data.get('result')
        if not isinstance(result, dict):
            raise ValueError('account unavailable')
        return result


def payload(value, sampled_at):
    names = ('balance', 'equity', 'margin', 'free_margin', 'profit')
    result = {name: None for name in names}
    result.update(schema_version='1.0', currency=None, sampled_at=sampled_at, mt5_connected=False)
    if value is None:
        return result
    selected = {name: value.get('margin_free' if name == 'free_margin' else name) for name in names}
    if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1e12
           for v in selected.values()) or selected['margin'] < 0:
        return result
    currency = value.get('currency')
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isascii() or not currency.isupper() or not currency.isalpha():
        return result
    result.update(selected, currency=currency, mt5_connected=True)
    return result


class SnapshotSampler:
    """One daemon read at a time across reconnects; no queued work or wire writes."""
    def __init__(self, read):
        self.read = read
        self.lock = threading.Lock()
        self.worker = None
        self.result = None
        self.generation = None
        self.started = 0
        self.sampled = 0
        self.reported_timeout = False

    def start(self, generation, permitted):
        with self.lock:
            if self.worker is not None and self.worker.is_alive():
                return
            self.result = None
            self.generation = generation
            self.started, self.sampled = time.monotonic(), time.time()
            self.reported_timeout = False
            def work():
                value = None
                try:
                    if permitted():
                        value = self.read()
                except Exception:
                    pass  # Never log account values or exception text.
                with self.lock:
                    self.result = payload(value, self.sampled)
            self.worker = threading.Thread(target=work, name='account-snapshot-read', daemon=True)
            self.worker.start()

    def take(self, generation):
        with self.lock:
            if self.generation != generation or self.worker is None:
                return None
            if time.monotonic() - self.started > 4:
                self.result = None
                if not self.reported_timeout:
                    self.reported_timeout = True
                    return payload(None, time.time())
                return None
            result, self.result = self.result, None
            return result
