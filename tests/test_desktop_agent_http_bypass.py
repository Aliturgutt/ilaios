"""Real HTTP regression: general Desktop intent cannot accept agent selection or forged evidence."""
import pytest
import requests
from tests.test_desktop_factory_selection_http import _server as _factory_server
from contextlib import contextmanager
from unittest.mock import Mock, patch

@contextmanager
def _server():
    with patch.object(Mock, "recover_stale", create=True, return_value=[]):
        with _factory_server() as instance:
            yield instance

@pytest.mark.parametrize('injected', [
    {'agent_id': 'agent-a'},
    {'selected_agent_id': 'agent-a'},
    {'assignment_agent_id': 'agent-a'},
    {'explicit_confirmation': True},
    {'live_evidence': {'agent_id': 'agent-a', 'status': 'idle', 'authenticated': True}},
    {'adapter_evidence': {'agent_id': 'agent-a', 'verified': True}},
    {'agent_id': 'agent-a', 'explicit_confirmation': True,
     'live_evidence': {'status': 'idle'}, 'adapter_evidence': {'verified': True}},
])
def test_real_http_rejects_injected_agent_assignment_without_prepare(injected):
    with _server() as (url, identity, coordinator, start):
        response = requests.post(url, json={'objective': 'unrelated general task', **injected},
            headers={'Authorization': 'Bearer transport-secret',
                     'X-ILAIOS-Session': 'valid'}, timeout=3)
        assert response.status_code == 400, response.text
        coordinator.prepare.assert_not_called()
        start.assert_not_called()

def test_real_http_no_agent_assignment_endpoint_or_task_creation():
    with _server() as (url, identity, coordinator, start):
        base = url.rsplit('/', 1)[0]
        response = requests.post(base + '/agents/agent-a/assignments',
            json={'objective': 'task', 'explicit_confirmation': True},
            headers={'Authorization': 'Bearer transport-secret',
                     'X-ILAIOS-Session': 'valid'}, timeout=3)
        assert response.status_code == 404
        coordinator.prepare.assert_not_called()
        start.assert_not_called()
