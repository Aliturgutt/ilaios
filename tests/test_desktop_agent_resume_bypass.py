"""Agent execution IDs cannot bypass assignment admission through generic resume."""
import requests
from tests.test_desktop_agent_assignment_http import server, post


def test_agent_assignment_cannot_resume_through_generic_endpoint():
    with server() as (url, identity, coordinator, preflight, start):
        assigned = post(url)
        assert assigned.status_code == 201
        request_id = assigned.json()['request_id']
        assert request_id.startswith('agentexec-')
        base = url.split('/v1/desktop/agents/assignments')[0]
        response = requests.post(base + '/v1/execution/resume', json={'request_id': request_id},
            headers={'Authorization': 'Bearer transport', 'X-ILAIOS-Session': 'valid'}, timeout=3)
        assert response.status_code == 403
        coordinator.get.assert_not_called()
        start.assert_not_called()


def test_legacy_execution_resume_path_remains_unchanged():
    with server() as (url, identity, coordinator, preflight, start):
        coordinator.get.return_value = {'terminal': False}
        base = url.split('/v1/desktop/agents/assignments')[0]
        response = requests.post(base + '/v1/execution/resume', json={'request_id': 'legacy-1'},
            headers={'Authorization': 'Bearer transport', 'X-ILAIOS-Session': 'valid'}, timeout=3)
        assert response.status_code == 202
        start.assert_called_once_with('legacy-1')

def test_disconnected_agent_cannot_reenter_through_general_resume():
    with server() as (url, identity, coordinator, preflight, start):
        assigned = post(url)
        assert assigned.status_code == 201
        request_id = assigned.json()['request_id']
        preflight.check.return_value = type('Denied', (), {'eligible': False})()
        base = url.split('/v1/desktop/agents/assignments')[0]
        response = requests.post(base + '/v1/execution/resume', json={'request_id': request_id},
            headers={'Authorization': 'Bearer transport', 'X-ILAIOS-Session': 'valid'}, timeout=3)
        assert response.status_code == 403
        start.assert_not_called()
        assert post(url).status_code == 403

def test_persisted_legacy_agent_request_denied_generic_resume(tmp_path):
    import sqlite3
    from services.desktop_agent_assignment_store import record_agent_assignment
    db = tmp_path / 'execution.sqlite3'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE execution_requests (request_id TEXT PRIMARY KEY, principal_id TEXT, tenant_id TEXT)')
        conn.execute('INSERT INTO execution_requests VALUES (?, ?, ?)', ('old-agent-1', 'user-a', 'tenant-a'))
    record_agent_assignment(db, request_id='old-agent-1', agent_id='agent-a',
        principal_id='user-a', tenant_id='tenant-a')
    with server() as (url, identity, coordinator, preflight, start):
        coordinator._database_path = db
        base = url.split('/v1/desktop/agents/assignments')[0]
        response = requests.post(base + '/v1/execution/resume', json={'request_id': 'old-agent-1'},
            headers={'Authorization': 'Bearer transport', 'X-ILAIOS-Session': 'valid'}, timeout=3)
        assert response.status_code == 403
        start.assert_not_called()
