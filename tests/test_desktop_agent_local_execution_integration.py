"""Actual coordinator execution with persisted Desktop agent provenance.

This tests the local installed adapter, NOT a remotely authenticated agent worker.
"""
from datetime import datetime, timedelta, timezone
import pytest
from services.desktop_agent_assignment_store import record_agent_assignment, is_agent_assignment
from services.desktop_agent_legacy_provenance import requires_agent_resume_guard
from services.desktop_agent_heartbeat import AgentHeartbeatStore
from services.desktop_agent_task_lifecycle import inspect_task
from tests.test_execution_coordinator import _coordinator

NOW = datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc)


def _assigned(tmp_path, request_id):
    coordinator, governance, scheduler, grants, product = _coordinator(tmp_path)
    prepared = coordinator.prepare(request_id, 'Create a launch video and final MP4',
        token='token', principal_id='owner', tenant_id='tenant-a', now=NOW)
    record_agent_assignment(coordinator._database_path, request_id=request_id,
        agent_id='agent-a', principal_id='owner', tenant_id='tenant-a')
    assert is_agent_assignment(coordinator._database_path, request_id)
    assert requires_agent_resume_guard(coordinator._database_path, request_id)
    return coordinator, scheduler, grants, prepared


def test_real_coordinator_completes_persisted_agent_labeled_task(tmp_path):
    coordinator, scheduler, grants, prepared = _assigned(tmp_path, 'agentexec-real-success')
    manifest = coordinator.resume('agentexec-real-success', token='token', now=NOW + timedelta(seconds=1))
    assert manifest['accepted'] is True and manifest['tenant_id'] == 'tenant-a'
    state = coordinator.get('agentexec-real-success', principal_id='owner', tenant_id='tenant-a')
    assert state['execution_status'] == 'ACCEPTED' and state['terminal']
    assert scheduler.state()['leases'] == []
    reopened, *_ = _coordinator(tmp_path)
    assert reopened.get('agentexec-real-success', principal_id='owner', tenant_id='tenant-a')['terminal']
    assert requires_agent_resume_guard(reopened._database_path, 'agentexec-real-success')


def test_real_coordinator_failure_and_disconnected_heartbeat(tmp_path):
    from tests.test_execution_coordinator import GrantError
    coordinator, scheduler, grants, _ = _assigned(tmp_path, 'agentexec-real-fail')
    heartbeat = AgentHeartbeatStore({'agent-a': 'secret'})
    assert heartbeat.record('agent-a', 'secret', 'idle', now=NOW)
    args = dict(request_id='agentexec-real-fail', agent_id='agent-a',
                principal_id='owner', tenant_id='tenant-a')
    assert inspect_task(coordinator, heartbeat, **args, now=NOW).connected
    offline = inspect_task(coordinator, heartbeat, **args, now=NOW + timedelta(seconds=31))
    assert not offline.connected
    grants.kill('worker-video', now=NOW)
    with pytest.raises(GrantError):
        coordinator.resume('agentexec-real-fail', token='token', now=NOW + timedelta(seconds=32))
    failed = inspect_task(coordinator, heartbeat, **args, now=NOW + timedelta(seconds=33))
    assert failed.terminal and failed.execution_status == 'FAILED_TERMINAL'
    assert heartbeat.record('agent-a', 'secret', 'idle', now=NOW + timedelta(seconds=34))
    restored = inspect_task(coordinator, heartbeat, **args, now=NOW + timedelta(seconds=35))
    assert restored.connected and restored.execution_status == 'FAILED_TERMINAL'
    assert scheduler.state()['leases'] == []


def test_real_coordinator_cancel_persisted_agent_task(tmp_path):
    coordinator, scheduler, grants, _ = _assigned(tmp_path, 'agentexec-real-cancel')
    assert coordinator.cancel('agentexec-real-cancel', token='token', actor_id='owner',
                              tenant_id='tenant-a', now=NOW) == 'CANCELLED'
    state = coordinator.get('agentexec-real-cancel', principal_id='owner', tenant_id='tenant-a')
    assert state['terminal'] and state['execution_status'] == 'CANCELLED'
    assert requires_agent_resume_guard(coordinator._database_path, 'agentexec-real-cancel')
