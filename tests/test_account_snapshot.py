import json
import threading
import time

import pytest

from agent.application.dispatcher import CommandDispatcher
from agent.infrastructure.account_snapshot import AuthorizedAccountReader, SnapshotSampler, grant, payload
from agent.infrastructure.gateway_wss import GatewayHostingPort
from test_gateway_wss import Primary, Peer, IDENTITY, settings


def reader(permitted, calls):
    dispatcher = CommandDispatcher()
    dispatcher.register('mt5.get_account_information', lambda c: (calls.append(1) or {'result': dict(balance=100, equity=99, margin=10, margin_free=89, profit=-1, currency='USD', login='DO-NOT-LOG')}))
    return AuthorizedAccountReader(dispatcher, permitted)


def test_account_authorization_and_expiry():
    enabled = [False]
    calls = []
    r = reader(lambda: enabled[0], calls)
    with pytest.raises(ValueError): r.read()
    assert calls == []
    enabled[0] = True
    assert payload(r.read(), time.time())['free_margin'] == 89
    enabled[0] = False
    with pytest.raises(ValueError): r.read()
    assert calls == [1]
    assert grant({'expires_at': time.time()+30, 'account_read': {'permission':'account-read','expires_at':time.time()-1}}) is None
    assert grant({'expires_at':time.time()+30}) is None


def test_unknown_and_projection():
    result = payload(None, time.time())
    assert result['mt5_connected'] is False
    assert all(result[k] is None for k in ('balance','equity','margin','free_margin','profit','currency'))
    calls=[]
    projected=payload(reader(lambda:True,calls).read(),time.time())
    assert 'login' not in projected
    assert payload({'balance':True},time.time())['balance'] is None


def test_single_read_and_reconnect_discards_old_result():
    done=threading.Event()
    calls=[]
    sampler=SnapshotSampler(lambda:(calls.append(1),done.wait(2),None)[-1])
    sampler.start('old',lambda:True)
    sampler.start('new',lambda:True)
    assert sampler.take('new') is None
    done.set()
    sampler.worker.join(2)
    assert calls == [1]
    sampler.start('new',lambda:False)
    sampler.worker.join(2)
    assert calls == [1]
    assert sampler.take('new')['mt5_connected'] is False


def test_authenticated_session_sampling(settings,caplog):
    path,data=settings
    data['account_read']={'permission':'account-read','expires_at':time.time()+30}
    path.write_text(json.dumps(data))
    calls=[]
    h=GatewayHostingPort(Primary(),path,account_reader=reader(lambda:True,calls))
    class SamplingPeer(Peer):
        def __init__(self,host):
            super().__init__(host)
            self.samples=[]
            self.deadline=time.monotonic()+2
        def send(self,text):
            m=json.loads(text)
            super().send(text)
            if m['type']=='account_snapshot':
                self.samples.append(m)
                self.host.stop_event.set()
        def recv(self,timeout):
            if self.queue: return json.dumps(self.queue.pop(0))
            if time.monotonic()>self.deadline: self.host.stop_event.set()
            time.sleep(.01)
            raise TimeoutError()
    p=SamplingPeer(h)
    h.session(p,data)
    assert calls == [1] and len(p.samples)==1
    sample=p.samples[0]
    assert sample['agent_id']==IDENTITY
    assert sample['payload']['schema_version']=='1.0'
    assert 'DO-NOT-LOG' not in caplog.text and 'login' not in sample['payload']
    h.stop_event.clear()
    bad=Peer(h,True)
    with pytest.raises(ValueError): h.session(bad,data)
    assert calls == [1]


def test_no_opt_in_never_reads(settings):
    path,data=settings
    calls=[]
    h=GatewayHostingPort(Primary(),path,account_reader=reader(lambda:True,calls))
    h.session(Peer(h),data)
    assert calls == []


def test_account_permission_never_authorizes_trade():
    from agent.contracts.models import Command
    from agent.contracts.security import SecurityContext
    r=reader(lambda:True,[])
    context=SecurityContext('reader','local',frozenset({'account-read'}),{})
    command=Command('id','mt5.order_send','1','correlation','2026-10-30T00:00:00+00:00',{})
    assert not r.authority.authorize(context,command).allowed


def test_slow_read_reports_unknown_without_queue():
    done=threading.Event()
    calls=[]
    s=SnapshotSampler(lambda:(calls.append(1),done.wait(2),None)[-1])
    s.start('one',lambda:True)
    s.started -= 5
    result=s.take('one')
    assert result['balance'] is None and result['mt5_connected'] is False
    assert s.take('one') is None
    s.start('one',lambda:True)
    done.set()
    s.worker.join(2)
    assert calls == [1]
