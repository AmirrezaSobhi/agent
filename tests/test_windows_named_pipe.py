import ctypes
import os
import threading
import pytest
pytestmark=pytest.mark.skipif(os.name!='nt',reason='Windows native transport')
from agent.infrastructure.windows_named_pipe import WindowsNamedPipe


def test_pipe_server_acl_contains_only_the_configured_control_principal():
 import win32api
 import win32con
 import win32security
 token=win32security.OpenProcessToken(win32api.GetCurrentProcess(),win32con.TOKEN_QUERY)
 try:
  sid=win32security.GetTokenInformation(token,win32security.TokenUser)[0]
  username,domain,_=win32security.LookupAccountSid(None,sid)
  principal=f'{domain}\\{username}'
 finally:
  token.Close()
 pipe=WindowsNamedPipe(rf'\\.\pipe\mt5-agent-acl-{os.getpid()}',allowed_principals=(principal,))
 attributes=pipe._security_attributes()
 dacl=attributes.SECURITY_DESCRIPTOR.GetSecurityDescriptorDacl()
 assert dacl.GetAceCount()==1
 ace=dacl.GetAce(0)
 assert win32security.EqualSid(ace[2],sid)


def test_local_named_pipe_authenticates_client_and_checks_its_session():
 import win32api
 import win32con
 import win32security
 token=win32security.OpenProcessToken(win32api.GetCurrentProcess(),win32con.TOKEN_QUERY)
 try:
  sid=win32security.GetTokenInformation(token,win32security.TokenUser)[0]
  username,domain,_=win32security.LookupAccountSid(None,sid)
  principal=f'{domain}\\{username}'
 finally:
  token.Close()
 name=rf'\\.\pipe\mt5-agent-test-{os.getpid()}'
 pipe=WindowsNamedPipe(name,allowed_principals=(principal,)); peers=[]
 def serve():
  pipe.serve_forever(lambda request,peer:(peers.append(peer) or {'ok':True,'stop_worker':True}))
 thread=threading.Thread(target=serve,daemon=True); thread.start()
 response=pipe.request({'version':'1','operation':'health','request_id':'request-1'},timeout_ms=3000)
 thread.join(timeout=3)
 current_session=ctypes.c_uint32()
 assert ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(),ctypes.byref(current_session))
 assert response['ok'] is True
 assert not thread.is_alive()
 assert peers[0].principal.casefold()==principal.casefold()
 assert peers[0].session_id==current_session.value


def test_client_disconnect_after_request_does_not_stop_worker():
 win32api=pytest.importorskip('win32api')
 import win32con
 import win32file
 import win32security
 import win32pipe
 token=win32security.OpenProcessToken(win32api.GetCurrentProcess(),win32con.TOKEN_QUERY)
 try:
  sid=win32security.GetTokenInformation(token,win32security.TokenUser)[0]
  username,domain,_=win32security.LookupAccountSid(None,sid)
  principal=f'{domain}\\{username}'
 finally:
  token.Close()
 name=rf'\\.\pipe\mt5-agent-disconnect-{os.getpid()}'
 pipe=WindowsNamedPipe(name,allowed_principals=(principal,))
 requests=[]
 def dispatch(request,peer):
  requests.append(request)
  return {'ok':True,'stop_worker':len(requests)==2}
 thread=threading.Thread(target=lambda:pipe.serve_forever(dispatch),daemon=True); thread.start()
 handle=win32file.CreateFile(name,win32con.GENERIC_READ|win32con.GENERIC_WRITE,0,None,win32con.OPEN_EXISTING,0,None)
 try:
  win32pipe.SetNamedPipeHandleState(handle,win32pipe.PIPE_READMODE_MESSAGE|win32pipe.PIPE_NOWAIT,None,None)
  pipe._write(handle,{'version':'1','operation':'health','request_id':'disconnect-1'})
  response=pipe._read(handle,timeout_ms=3000,set_nowait=False)
  assert response['ok'] is True
 finally:
  # Deliberately omit the acknowledgement to simulate a client that exits.
  win32file.CloseHandle(handle)
 assert pipe.request({'version':'1','operation':'health','request_id':'disconnect-2'},timeout_ms=12000)['ok'] is True
 thread.join(timeout=3)
 assert not thread.is_alive()
 assert len(requests)==2
