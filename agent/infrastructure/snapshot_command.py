"""Bounded in-process admission for authorized account snapshot commands.

This component is not connected to the WSS transport by itself.
"""
import math
import threading
import time
from uuid import UUID

from agent.infrastructure.account_snapshot import payload


class SnapshotCommandGate:
    def __init__(self, reader, permitted, *, clock=time.time, limit=128):
        self.reader = reader
        self.permitted = permitted
        self.clock = clock
        self.limit = limit
        self.lock = threading.Lock()
        self.entries = {}
        self.busy = False

    def execute(self, request, agent_id):
        if not isinstance(request, dict) or set(request) != {
                'version', 'command_id', 'correlation_id', 'agent_id', 'expires_at'}:
            raise ValueError('invalid request')
        if request['version'] != '1.0' or request['agent_id'] != agent_id:
            raise ValueError('identity mismatch')
        for name in ('command_id', 'correlation_id'):
            value = request[name]
            if not isinstance(value, str) or str(UUID(value)) != value:
                raise ValueError('invalid identifier')
        expiry = request['expires_at']
        if type(expiry) not in (int, float) or not math.isfinite(expiry):
            raise ValueError('invalid expiry')
        key = request['command_id']
        fingerprint = (request['correlation_id'], agent_id, expiry)
        def response(status, snapshot=None):
            return dict(version='1.0', command_id=key, correlation_id=request['correlation_id'],
                        agent_id=agent_id, expires_at=expiry, status=status, snapshot=snapshot)
        with self.lock:
            now = self.clock()
            self.entries = {k: v for k, v in self.entries.items() if v[1] > now}
            old = self.entries.get(key)
            if old:
                if old[0] != fingerprint:
                    raise ValueError('command identifier conflict')
                return response('duplicate')
            if expiry <= now:
                return response('expired')
            if expiry > now + 30:
                raise ValueError('excessive deadline')
            if len(self.entries) >= self.limit or self.busy:
                return response('unavailable')
            self.entries[key] = (fingerprint, expiry)
            if not self.permitted():
                return response('denied')
            self.busy = True
        try:
            value = self.reader.read()
            if self.clock() >= expiry:
                return response('timeout')
            if not self.permitted():
                return response('denied')
            if type(value.get('trade_mode')) is not int or value['trade_mode'] != 0:
                return response('denied')
            sample = payload(value, self.clock())
            return response('success' if sample['mt5_connected'] else 'unavailable', sample)
        except Exception:
            return response('unavailable')
        finally:
            with self.lock:
                self.busy = False
