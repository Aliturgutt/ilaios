"""Historical ambiguous provenance and coordinator restart safety."""
from datetime import datetime, timedelta, timezone
from services.desktop_agent_legacy_provenance import requires_agent_resume_guard
from services.desktop_agent_assignment_store import record_agent_assignment
from services.desktop_agent_heartbeat import AgentHeartbeatStore
from services.desktop_agent_task_lifecycle import inspect_task
from tests.test_execution_coordinator import _coordinator

NOW = datetime.now(timezone.utc)


def test_ambiguous_historical_factory_job_fails_closed_after_restart(tmp_path):
    coordinator, *_ = _coordinator(tmp_path)
    coordinator.prepare('historical-video', 'Create a video about our product',
        token='token', principal_id='owner', tenant_id='tenant-a', now=NOW)
    db = coordinator._database_path
    assert requires_agent_resume_guard(db, 'historical-video')
    reopened, *_ = _coordinator(tmp_path)
    assert requires_agent_resume_guard(reopened._database_path, 'historical-video')
    assert not requires_agent_resume_guard(db, 'unknown-request')
    assert requires_agent_resume_guard(db, 'agentexec-missing')


def test_provenance_survives_coordinator_restart_and_disconnect(tmp_path):
    coordinator, *_ = _coordinator(tmp_path)
    coordinator.prepare('old-assignment', 'Create a video about our product',
        token='token', principal_id='owner', tenant_id='tenant-a', now=NOW)
    record_agent_assignment(coordinator._database_path, request_id='old-assignment',
        agent_id='agent-a', principal_id='owner', tenant_id='tenant-a')
    heartbeat = AgentHeartbeatStore({'agent-a': 'secret'})
    assert heartbeat.record('agent-a', 'secret', 'idle', now=NOW)
    reopened, *_ = _coordinator(tmp_path)
    assert requires_agent_resume_guard(reopened._database_path, 'old-assignment')
    args = dict(request_id='old-assignment', agent_id='agent-a',
                principal_id='owner', tenant_id='tenant-a')
    initial = inspect_task(reopened, heartbeat, **args, now=NOW)
    offline = inspect_task(reopened, heartbeat, **args, now=NOW + timedelta(seconds=31))
    assert initial.connected and not offline.connected
    assert initial.execution_status == offline.execution_status
    assert heartbeat.record('agent-a', 'secret', 'idle', now=NOW + timedelta(seconds=32))
    restored = inspect_task(reopened, heartbeat, **args, now=NOW + timedelta(seconds=33))
    assert restored.connected and restored.execution_status == initial.execution_status
