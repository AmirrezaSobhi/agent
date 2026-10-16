import json
import logging
import threading
import time
from uuid import uuid4

import pytest

from agent.infrastructure.gateway_wss import (GatewayHostingPort, backoff,
    configured_gateway_host, load_settings, parse_message)

IDENTITY = 'win10-native-agent-01'


def frame(kind='ping', correlation=None, **overrides):
    return {'version':'1.0','type':kind,'agent_id':IDENTITY,
            'message_id':str(uuid4()),'correlation_id':correlation,'payload':{}, **overrides}


@pytest.fixture
def settings(tmp_path):
    token = tmp_path / 'token'
    token.write_text('x' * 43)
    data = {'url':f'wss://example.invalid/v1/agents/{IDENTITY}/ws',
            'agent_id':IDENTITY,'token_file':str(token),'expires_at':time.time()+100}
    config = tmp_path / 'config.json'
    config.write_text(json.dumps(data))
    return config, data


def test_config(settings):
    path, data = settings
    assert load_settings(path) == (data, 'x'*43)


@pytest.mark.parametrize('field,value', [('expires_at',0),('agent_id','BAD'),
    ('url','ws://example.invalid/'),('url','wss://user:secret@example.invalid/'),
    ('url',f'wss://example.invalid/v1/agents/{IDENTITY}/ws?token=secret')])
def test_invalid_configuration(settings, field, value):
    path, data = settings
    data[field] = value
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError): load_settings(path)


@pytest.mark.parametrize('changes', [{'version':'2'}, {'agent_id':'other'},
    {'type':'trade'},{'message_id':'bad'}, {'payload':{'secret':'no'}},
    {'correlation_id':str(uuid4())}, {'extra':True}])
def test_message_rejected(changes):
    with pytest.raises(ValueError): parse_message(json.dumps(frame(**changes)), IDENTITY)


def test_duplicate_json_binary_and_size():
    for text in ['{"type":"ping","type":"ping"}', b'{}', 'x'*16385]:
        with pytest.raises(ValueError): parse_message(text, IDENTITY)


def test_backoff_is_bounded_and_increasing():
    assert [backoff(i, lambda:1) for i in range(8)] == [1,2,4,8,16,32,60,60]
    assert backoff(0, lambda:0) == .75


class Primary:
    def __init__(self): self.stopped = threading.Event()
    def serve(self): self.stopped.wait(3)
    def shutdown(self): self.stopped.set()


class Peer:
    def __init__(self, host, invalid=False):
        self.host=host; self.queue=[]; self.invalid=invalid; self.closed=False
    def send(self, text):
        m=json.loads(text)
        if m['type']=='hello':
            self.queue += [frame('hello_ack', str(uuid4()) if self.invalid else m['message_id']),frame()]
        if m['type'] in ('echo','ping'):
            self.queue.append(frame('echo' if m['type']=='echo' else 'pong', m['message_id'],payload=m['payload']))
    def recv(self, timeout):
        if self.queue: return json.dumps(self.queue.pop(0))
        self.host.stop_event.set()
        raise TimeoutError()
    def close(self,*args): self.closed=True


def test_hello_echo_ping_and_redaction(caplog):
    h=GatewayHostingPort(Primary(), 'unused', logger=logging.getLogger('gateway-test'))
    p=Peer(h)
    with caplog.at_level(logging.INFO): h.session(p, {'agent_id':IDENTITY,'expires_at':time.time()+10})
    events=[json.loads(r.message) for r in caplog.records]
    assert any(e['event']=='gateway_authenticated' for e in events)
    assert {e['message_type'] for e in events if e['event']=='gateway_round_trip'} == {'echo','pong'}
    assert 'agent-core-connectivity-test' not in caplog.text


def test_wrong_hello_correlation():
    h=GatewayHostingPort(Primary(),'unused')
    with pytest.raises(ValueError): h.session(Peer(h,True), {'agent_id':IDENTITY,'expires_at':time.time()+10})


def test_hello_timeout():
    h=GatewayHostingPort(Primary(),'unused')
    class TimeoutPeer:
        def send(self,*a): pass
        def recv(self,timeout): raise TimeoutError()
    with pytest.raises(TimeoutError): h.session(TimeoutPeer(), {'agent_id':IDENTITY,'expires_at':time.time()+10})


def test_reconnect_settings_reload_and_secret_redaction(settings,caplog):
    path,data=settings
    calls=[]
    h=None
    def connect(url, **kwargs):
        assert kwargs['ssl'].check_hostname and kwargs['ssl'].verify_mode == 2
        assert kwargs['max_size']==16384 and kwargs['max_queue']==8
        calls.append(url)
        if len(calls)==2: h.stop_event.set()
        raise RuntimeError('secret '+ 'x'*43)
    h=GatewayHostingPort(Primary(),path,connector=connect,logger=logging.getLogger('gateway-test'))
    # Interruptible backoff, no CPU spin; test waits for the second bounded attempt.
    with caplog.at_level(logging.INFO): h.run()
    assert len(calls)==2
    assert 'x'*43 not in caplog.text
    assert 'gateway_retry' in caplog.text


def test_host_stop_and_duplicate_prevention(settings):
    path,_=settings
    attempts=[]
    def fail(*args,**kwargs): attempts.append(1);raise OSError()
    h=GatewayHostingPort(Primary(),path,connector=fail)
    t=threading.Thread(target=h.serve);t.start()
    for _ in range(100):
        if h.thread: break
        time.sleep(.01)
    with pytest.raises(RuntimeError): h.serve()
    h.shutdown();t.join(5)
    assert not t.is_alive() and not h.thread.is_alive()
    assert len(attempts)<=1


def test_absent_configuration_preserves_existing_host(tmp_path,monkeypatch):
    monkeypatch.setenv('MT5_AGENT_GATEWAY_CONFIG',str(tmp_path/'absent'))
    p=Primary();assert configured_gateway_host(p) is p
