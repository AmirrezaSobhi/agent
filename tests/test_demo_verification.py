import json
from uuid import uuid4

import pytest

from agent.infrastructure.demo_verification import DemoVerifier
from agent.infrastructure.management_named_pipe import ManagementNamedPipeServer


@pytest.mark.parametrize('mode,expected', [(0, True), (1, False), (2, False),
                                         (None, 'unknown'), (True, 'unknown'),
                                         ('0', 'unknown'), (9, 'unknown')])
def test_authorized_demo_projection(mode, expected, caplog):
    class Adapter:
        def account_information(self):
            return {'trade_mode': mode, 'login': 'PRIVATE-LOGIN', 'balance': 876543.21}
    verifier = DemoVerifier(Adapter())
    assert verifier.observe() == {'demo_verified': expected}
    assert 'PRIVATE-LOGIN' not in caplog.text and '876543.21' not in caplog.text


def test_management_denies_before_read_and_projects_only_boolean(caplog):
    calls = []
    server = ManagementNamedPipeServer(lambda: {}, ('S-1-5-18',), demo_provider=lambda:
                                      (calls.append(1) or {'demo_verified': True, 'login': 'PRIVATE'}))
    request = dict(protocol_version=1, request_id=str(uuid4()), correlation_id=str(uuid4()),
                   operation='account.demo_status', payload={})
    raw = json.dumps(request).encode()
    denied, _ = server._handle(raw, 'other')
    assert denied['code'] == 'UNAUTHORIZED' and calls == []
    response, _ = server._handle(raw, 'S-1-5-18')
    assert response['data'] == {'demo_verified': True} and calls == [1]
    assert 'PRIVATE' not in json.dumps(response) + caplog.text
    request['payload'] = {'anything': 'PRIVATE'}
    rejected, _ = server._handle(json.dumps(request).encode(), 'S-1-5-18')
    assert rejected['code'] == 'INVALID_REQUEST' and calls == [1]


def test_boundary_rejects_revoked_probe_and_runtime_errors_are_unknown(caplog):
    class Adapter:
        def account_information(self):
            raise RuntimeError('PRIVATE-ACCOUNT')
    verifier = DemoVerifier(Adapter())
    assert verifier.observe() == {'demo_verified': 'unknown'}
    verifier._token = 'unauthorized'
    assert verifier.observe() == {'demo_verified': 'unknown'}
    assert 'PRIVATE-ACCOUNT' not in caplog.text


def test_boundary_requires_specific_permission_before_adapter_read():
    calls = []
    class Adapter:
        def account_information(self):
            calls.append(1)
            return {'trade_mode': 0}
    verifier = DemoVerifier(Adapter())
    authority = verifier.boundary._authorizer
    authority.enroll('wrong-scope', verifier._token, {'account-read'})
    assert verifier.observe() == {'demo_verified': 'unknown'}
    assert calls == []
    authority.enroll('correct-scope', verifier._token, {'command:mt5.get_account_demo_status'})
    assert verifier.observe() == {'demo_verified': True}
    assert calls == [1]
    authority.revoke(verifier._token)
    assert verifier.observe() == {'demo_verified': 'unknown'} and calls == [1]
