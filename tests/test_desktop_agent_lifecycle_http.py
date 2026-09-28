"""Existing authenticated execution lifecycle HTTP endpoint regression."""
import requests
from types import SimpleNamespace
from tests.test_desktop_agent_assignment_http import server


def test_http_owner_status_cancel_and_cross_tenant_denial():
    with server() as (url, identity, coordinator, preflight, start):
        base = url.split('/v1/desktop/agents/assignments')[0]
        headers = {'Authorization': 'Bearer transport', 'X-ILAIOS-Session': 'valid'}
        coordinator.get.return_value = {'request_id': 'exec-1', 'execution_status': 'RUNNING', 'terminal': False}
        status = requests.get(base + '/v1/execution/status', params={'request_id': 'exec-1'}, headers=headers, timeout=3)
        assert status.status_code == 200 and status.json()['execution_status'] == 'RUNNING'
        coordinator.get.assert_called_with('exec-1', principal_id='user-a', tenant_id='tenant-a')
        coordinator._adapters = {}
        cancel = requests.post(base + '/v1/execution/cancel', json={'request_id': 'exec-1'}, headers=headers, timeout=3)
        assert cancel.status_code == 200
        assert coordinator.cancel.call_args.kwargs['tenant_id'] == 'tenant-a'
        identity.validate_session.return_value = SimpleNamespace(principal_id='user-b', tenant_id='tenant-b')
        from services.execution_coordinator import ExecutionCoordinatorError
        coordinator.get.side_effect = ExecutionCoordinatorError('not owner')
        denied = requests.get(base + '/v1/execution/status', params={'request_id': 'exec-1'}, headers=headers, timeout=3)
        assert denied.status_code == 409
