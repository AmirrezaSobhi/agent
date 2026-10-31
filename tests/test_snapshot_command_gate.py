import threading
import time
from uuid import uuid4

import pytest

from agent.infrastructure.snapshot_command import SnapshotCommandGate
from test_gateway_wss import settings  # noqa: F401


def request():
    return dict(version='1.0', command_id=str(uuid4()), correlation_id=str(uuid4()),
                agent_id='demo-agent', expires_at=time.time() + 20)


class Reader:
    def __init__(self):
        self.calls = 0

    def read(self):
        self.calls += 1
        return dict(trade_mode=0, balance=5, equity=5, margin=0, margin_free=5,
                    profit=0, currency='USD', login='PRIVATE')


def test_authorized_read_and_duplicate_no_second_read():
    reader = Reader()
    gate = SnapshotCommandGate(reader, lambda: True)
    req = request()
    result = gate.execute(req, 'demo-agent')
    assert result['status'] == 'success' and 'login' not in result['snapshot']
    assert gate.execute(req, 'demo-agent')['status'] == 'duplicate'
    assert reader.calls == 1
    with pytest.raises(ValueError):
        gate.execute(dict(req, correlation_id=str(uuid4())), 'demo-agent')


def test_denied_expired_wrong_identity_and_late_response():
    reader = Reader()
    gate = SnapshotCommandGate(reader, lambda: False)
    assert gate.execute(request(), 'demo-agent')['status'] == 'denied'
    assert reader.calls == 0
    req = request()
    req['expires_at'] = time.time() - 1
    assert gate.execute(req, 'demo-agent')['status'] == 'expired'
    with pytest.raises(ValueError):
        gate.execute(request(), 'other-agent')
    now = [100.0]
    class Slow(Reader):
        def read(self):
            now[0] += 10
            return super().read()
    req = request()
    req['expires_at'] = 105.0
    assert SnapshotCommandGate(Slow(), lambda: True, clock=lambda: now[0]).execute(req, 'demo-agent')['status'] == 'timeout'


def test_simultaneous_commands_do_not_queue_reads():
    entered, release = threading.Event(), threading.Event()
    class Slow(Reader):
        def read(self):
            entered.set()
            release.wait(2)
            return super().read()
    reader = Slow()
    gate = SnapshotCommandGate(reader, lambda: True)
    thread = threading.Thread(target=lambda: gate.execute(request(), 'demo-agent'))
    thread.start()
    assert entered.wait(1)
    assert gate.execute(request(), 'demo-agent')['status'] == 'unavailable'
    release.set()
    thread.join(2)
    assert reader.calls == 1


def test_non_demo_and_expired_permission_never_return_values():
    class Real(Reader):
        def read(self):
            return dict(super().read(), trade_mode=2)
    result = SnapshotCommandGate(Real(), lambda: True).execute(request(), 'demo-agent')
    assert result['status'] == 'denied' and result['snapshot'] is None
    permission = [True]
    class Revoke(Reader):
        def read(self):
            value = super().read()
            permission[0] = False
            return value
    result = SnapshotCommandGate(Revoke(), lambda: permission[0]).execute(request(), 'demo-agent')
    assert result['status'] == 'denied' and result['snapshot'] is None


def test_wss_session_routes_snapshot_request_through_authorized_reader(settings, caplog):
    import json
    from agent.infrastructure.gateway_wss import GatewayHostingPort
    from test_gateway_wss import Primary, Peer, IDENTITY, frame
    path, config = settings
    config['account_read'] = {'permission': 'account-read', 'expires_at': time.time()+30}
    path.write_text(json.dumps(config))
    reader = Reader()
    host = GatewayHostingPort(Primary(), path, account_reader=reader)
    # Keep this test focused on the command path; periodic sampling has separate tests.
    host.sampler = None
    command = request()
    command['agent_id'] = IDENTITY
    class CommandPeer(Peer):
        def __init__(self, host):
            super().__init__(host)
            self.responses = []
            self.started = False
            self.deadline = time.monotonic() + 4
        def send(self, text):
            value = json.loads(text)
            super().send(text)
            if value['type'] == 'ping' and not self.started:
                self.started = True
                self.queue.append(frame('snapshot_request', command['correlation_id'], payload=command))
            if value['type'] == 'snapshot_response':
                self.responses.append(value)
                self.host.stop_event.set()
        def recv(self, timeout):
            if self.queue:
                return json.dumps(self.queue.pop(0))
            if time.monotonic() > self.deadline:
                self.host.stop_event.set()
            time.sleep(.01)
            raise TimeoutError()
    peer = CommandPeer(host)
    host.session(peer, config)
    assert len(peer.responses) == 1
    result = peer.responses[0]
    assert result['payload']['status'] == 'success'
    assert result['payload']['command_id'] == command['command_id']
    assert result['payload']['correlation_id'] == command['correlation_id']
    assert result['agent_id'] == IDENTITY
    assert reader.calls == 1
    assert 'PRIVATE' not in caplog.text
