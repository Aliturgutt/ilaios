from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
import pytest
from services.desktop_agent_heartbeat import AgentHeartbeatStore
from services.desktop_agent_task_lifecycle import inspect_task

NOW = datetime(2026, 9, 28, tzinfo=timezone.utc)

def test_running_disconnect_and_reconnect_never_resume():
    coordinator = Mock()
    coordinator.get.return_value = {'execution_status': 'RUNNING', 'terminal': False}
    heartbeat = AgentHeartbeatStore({'agent-a': 'secret'})
    assert heartbeat.record('agent-a', 'secret', 'idle', now=NOW)
    args = dict(request_id='exec-1', agent_id='agent-a', principal_id='user-a', tenant_id='tenant-a')
    assert inspect_task(coordinator, heartbeat, **args, now=NOW).connected
    assert not inspect_task(coordinator, heartbeat, **args, now=NOW + timedelta(seconds=31)).connected
    assert heartbeat.record('agent-a', 'secret', 'idle', now=NOW + timedelta(seconds=32))
    assert inspect_task(coordinator, heartbeat, **args, now=NOW + timedelta(seconds=33)).connected
    coordinator.resume.assert_not_called()
    coordinator.get.assert_called_with('exec-1', principal_id='user-a', tenant_id='tenant-a')

@pytest.mark.parametrize('status,terminal', [('ADMITTED', False), ('RUNNING', False),
    ('ACCEPTED', True), ('FAILED_TERMINAL', True), ('CANCELLED', True)])
def test_authoritative_states(status, terminal):
    coordinator = Mock()
    coordinator.get.return_value = {'execution_status': status, 'terminal': terminal}
    heartbeat = AgentHeartbeatStore({'agent-a': 'secret'})
    state = inspect_task(coordinator, heartbeat, request_id='exec-1', agent_id='agent-a',
        principal_id='user-a', tenant_id='tenant-a', now=NOW)
    assert state.execution_status == status and state.terminal is terminal


def test_cross_tenant_denial_propagates():
    coordinator = Mock()
    coordinator.get.side_effect = PermissionError('not owner')
    with pytest.raises(PermissionError):
        inspect_task(coordinator, AgentHeartbeatStore({'agent-a': 'secret'}),
            request_id='exec-1', agent_id='agent-a', principal_id='user-b', tenant_id='tenant-b', now=NOW)
