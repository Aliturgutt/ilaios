"""Authenticated automatic route rejects spoofing and unavailable delivery."""
from tests.test_desktop_agent_assignment_http import server, OBJECTIVE
import requests


def test_auto_assignment_fails_closed_without_worker_runtime():
    with server() as (url, identity, coordinator, preflight, start):
        endpoint = url.replace('/assignments', '/auto-assignments')
        headers = {'Authorization': 'Bearer transport', 'X-ILAIOS-Session': 'valid'}
        body = {'objective': OBJECTIVE, 'explicit_confirmation': True}
        response = requests.post(endpoint, json=body, headers=headers, timeout=3)
        assert response.status_code == 503
        coordinator.prepare.assert_not_called()
        assert requests.post(endpoint, json=dict(body, agent_id='agent-a'),
            headers=headers, timeout=3).status_code == 400
        assert requests.post(endpoint, json=body, timeout=3).status_code == 401
        start.assert_not_called()
