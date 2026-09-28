"""Loopback HTTP assignment admission, confirmation and tenant isolation."""
from contextlib import contextmanager
from threading import Thread
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
import requests
from services.desktop_identity_server import DesktopIdentityHTTPServer
from services.desktop_oidc import DesktopIdentityError
from services.execution_coordinator import classify_execution_plan

OBJECTIVE = 'Create a video about our product'
CAPABILITY = classify_execution_plan(OBJECTIVE).capability_ids[0]


@contextmanager
def server():
    identity = Mock()
    identity.validate_session.return_value = SimpleNamespace(principal_id='user-a', tenant_id='tenant-a')
    coordinator = Mock()
    coordinator.recover_stale.return_value = []
    coordinator.prepare.return_value = {'execution_status': 'BLOCKED',
        'plan': {'capabilities': [CAPABILITY]}, 'blocker_code': 'REVIEW_REQUIRED'}
    preflight = Mock()
    preflight.check.return_value = SimpleNamespace(eligible=True)
    config = {'bindings': {'agent-a': ('video.product-runtime.v1', CAPABILITY)},
        'preflight': preflight, 'runtime': object(), 'db': object()}
    http = DesktopIdentityHTTPServer(('127.0.0.1', 0), bearer_token='transport',
        identity=identity, coordinator=coordinator, agent_assignment=config)
    start = Mock()
    original = http.RequestHandlerClass._start_execution
    http.RequestHandlerClass._start_execution = start
    thread = Thread(target=http.serve_forever, daemon=True)
    thread.start()
    try:
        with patch('services.desktop_agent_assignment_store.record_agent_assignment'):
            yield f'http://127.0.0.1:{http.server_address[1]}/v1/desktop/agents/assignments', identity, coordinator, preflight, start
    finally:
        http.shutdown()
        thread.join(timeout=3)
        http.server_close()
        http.RequestHandlerClass._start_execution = original


def post(url, *, bearer='transport', session='valid', body=None):
    return requests.post(url, json=body if body is not None else
        {'agent_id': 'agent-a', 'objective': OBJECTIVE, 'explicit_confirmation': True},
        headers={'Authorization': 'Bearer '+bearer, 'X-ILAIOS-Session': session}, timeout=3)


def test_http_confirmed_assignment_forwards_only_authenticated_identity():
    with server() as (url, identity, coordinator, preflight, start):
        response = post(url)
        assert response.status_code == 201, response.text
        kwargs = coordinator.prepare.call_args.kwargs
        assert kwargs['principal_id'] == 'user-a' and kwargs['tenant_id'] == 'tenant-a'
        assert preflight.check.call_args.kwargs['tenant'] == 'tenant-a'
        start.assert_not_called()


@pytest.mark.parametrize('body', [
    {'agent_id': 'agent-a', 'objective': OBJECTIVE, 'explicit_confirmation': False},
    {'agent_id': 'agent-a', 'objective': OBJECTIVE},
    {'agent_id': 'agent-a', 'objective': OBJECTIVE, 'explicit_confirmation': True, 'tenant_id': 'tenant-b'},
    {'agent_id': 'agent-b', 'objective': OBJECTIVE, 'explicit_confirmation': True},
])
def test_http_rejects_unconfirmed_spoofed_or_unknown_assignment(body):
    with server() as (url, identity, coordinator, preflight, start):
        assert post(url, body=body).status_code in (400, 403)
        coordinator.prepare.assert_not_called()
        start.assert_not_called()


def test_http_invalid_transport_or_session_denied():
    with server() as (url, identity, coordinator, preflight, start):
        assert post(url, bearer='wrong').status_code == 401
        identity.validate_session.side_effect = DesktopIdentityError('expired')
        assert post(url).status_code == 401
        coordinator.prepare.assert_not_called()


def test_http_tenant_denial_never_calls_coordinator():
    with server() as (url, identity, coordinator, preflight, start):
        identity.validate_session.return_value = SimpleNamespace(principal_id='user-b', tenant_id='tenant-b')
        preflight.check.return_value = SimpleNamespace(eligible=False)
        assert post(url).status_code == 403
        assert preflight.check.call_args.kwargs['tenant'] == 'tenant-b'
        coordinator.prepare.assert_not_called()
        start.assert_not_called()


def test_http_admitted_request_starts_execution_only_after_route_check():
    with server() as (url, identity, coordinator, preflight, start):
        coordinator.prepare.return_value = {'execution_status': 'ADMITTED', 'plan': {'capabilities': [CAPABILITY]}}
        assert post(url).status_code == 201
        start.assert_called_once()

def test_http_real_coordinator_receives_authenticated_tenant(tmp_path):
    from tests.test_execution_coordinator import _coordinator
    from services.desktop_agent_assignment_http import submit_agent_assignment
    coordinator, *_ = _coordinator(tmp_path)
    identity = Mock()
    identity.validate_session.return_value = SimpleNamespace(principal_id='real-user', tenant_id='real-tenant')
    preflight = Mock()
    preflight.check.return_value = SimpleNamespace(eligible=True)
    config = {'bindings': {'agent-a': ('video.product-runtime.v1', CAPABILITY)},
              'preflight': preflight, 'runtime': object(), 'db': object()}
    http = DesktopIdentityHTTPServer(('127.0.0.1', 0), bearer_token='token',
        identity=identity, coordinator=coordinator, agent_assignment=config)
    thread = Thread(target=http.serve_forever, daemon=True)
    thread.start()
    try:
        url = f'http://127.0.0.1:{http.server_address[1]}/v1/desktop/agents/assignments'
        response = post(url, bearer='token')
        assert response.status_code in (201, 409), response.text
        if response.status_code == 201:
            assert response.json()['execution_status'] != 'ADMITTED' or response.json()['request_id']
        import sqlite3
        with sqlite3.connect(coordinator._database_path) as conn:
            rows = conn.execute('SELECT principal_id, tenant_id FROM execution_requests').fetchall()
        assert rows and all(row == ('real-user', 'real-tenant') for row in rows)
    finally:
        http.shutdown()
        thread.join(timeout=3)
        http.server_close()


def test_http_route_mismatch_never_starts_execution():
    with server() as (url, identity, coordinator, preflight, start):
        coordinator.prepare.return_value = {'execution_status': 'ADMITTED',
            'plan': {'capabilities': ['different-capability']}}
        assert post(url).status_code == 409
        start.assert_not_called()
