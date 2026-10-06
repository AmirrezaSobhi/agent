import pytest
from agent.application.runtime_worker import RuntimeWorkerProtocol,WorkerIdentity,WorkerState,SingleWorkerLease
def worker(): return RuntimeWorkerProtocol('session-token',WorkerIdentity('w',1,1,'user','now'))
def msg(operation,id='r',token='session-token',version='1'):return {'token':token,'version':version,'request_id':id,'operation':operation}
def test_ipc_auth_version_allowlist_duplicate_and_shutdown():
 w=worker(); assert w.handle(msg('handshake'))['state']=='WORKER_READY'; assert w.handle(msg('health','h'))['ok']
 assert w.handle(msg('anything','x'))['code']=='IPC_UNSUPPORTED_OPERATION'; assert w.handle(msg('health','bad',token='no'))['code']=='IPC_AUTHENTICATION_FAILED'
 assert w.handle(msg('health','h'))['code']=='IPC_DUPLICATE_REQUEST'; assert w.handle(msg('shutdown','s'))['state']=='WORKER_STOPPING'
def test_single_worker_lease_requires_exact_owner():
 lease=SingleWorkerLease(); identity=worker().identity; lease.acquire(identity)
 with pytest.raises(RuntimeError): lease.acquire(identity)
 with pytest.raises(RuntimeError): lease.release(WorkerIdentity('other',1,1,'u','n'))
 lease.release(identity)


def test_protocol_rejects_wrong_service_identity_session_and_extra_fields():
 w=RuntimeWorkerProtocol(None,WorkerIdentity('w',1,2,'user','now'))
 request={'version':'1','request_id':'a','operation':'health'}
 assert w.handle(request,client_principal='other',client_session_id=0,expected_client_principal='service')['code']=='IPC_AUTHENTICATION_FAILED'
 assert w.handle(request,client_principal='service',client_session_id=2,expected_client_principal='service')['code']=='IPC_CALLER_NOT_SESSION_ZERO'
 assert w.handle({**request,'command':'order_send'},client_principal='service',client_session_id=0,expected_client_principal='service')['code']=='IPC_INVALID_REQUEST_FIELDS'


def test_protocol_authenticates_configured_control_sid_and_session_zero():
 w=RuntimeWorkerProtocol(None,WorkerIdentity('w',1,2,'user','now'))
 request={'version':'1','request_id':'sid-check','operation':'health'}
 accepted=w.handle(request,client_principal='HOST\\Agent',client_sid='S-1-5-21-control',client_session_id=0,expected_client_principal='host\\agent',expected_client_sid='s-1-5-21-control')
 assert accepted['ok'] is True
 wrong_sid=w.handle({**request,'request_id':'wrong-sid'},client_principal='HOST\\Agent',client_sid='S-1-5-21-other',client_session_id=0,expected_client_principal='HOST\\Agent',expected_client_sid='S-1-5-21-control')
 assert wrong_sid['code']=='IPC_AUTHENTICATION_FAILED'
 wrong_session=w.handle({**request,'request_id':'wrong-session'},client_principal='HOST\\Agent',client_sid='S-1-5-21-control',client_session_id=2,expected_client_principal='HOST\\Agent',expected_client_sid='S-1-5-21-control')
 assert wrong_session['code']=='IPC_CALLER_NOT_SESSION_ZERO'


def test_protocol_rejects_wrong_version_and_keeps_a_bounded_sliding_replay_window():
 w=RuntimeWorkerProtocol(None,WorkerIdentity('w',1,2,'user','now'),max_seen=2)
 assert w.handle({'version':'2','request_id':'a','operation':'health'})['code']=='IPC_UNSUPPORTED_VERSION'
 assert w.handle({'version':'1','request_id':'a','operation':'health'})['ok']
 assert w.handle({'version':'1','request_id':'b','operation':'health'})['ok']
 assert w.handle({'version':'1','request_id':'a','operation':'health'})['code']=='IPC_DUPLICATE_REQUEST'
 assert w.handle({'version':'1','request_id':'c','operation':'health'})['ok']
 assert w.handle({'version':'1','request_id':'a','operation':'health'})['ok']
