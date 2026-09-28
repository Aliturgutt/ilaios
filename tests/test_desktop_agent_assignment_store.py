"""Persisted provenance survives restart and rejects owner mismatch."""
import sqlite3
import pytest
from datetime import datetime, timezone
from services.desktop_agent_assignment_store import record_agent_assignment, is_agent_assignment
from tests.test_execution_coordinator import _coordinator


def test_real_coordinator_persistent_agent_provenance_and_restart(tmp_path):
    coordinator, *_ = _coordinator(tmp_path)
    db = coordinator._database_path
    coordinator.prepare('legacy-agent-1', 'Create a video about our product',
        token='token', principal_id='user-a', tenant_id='tenant-a',
        now=datetime.now(timezone.utc))
    assert not is_agent_assignment(db, 'legacy-agent-1')
    with pytest.raises(ValueError, match='ownership'):
        record_agent_assignment(db, request_id='legacy-agent-1', agent_id='agent-a',
            principal_id='user-b', tenant_id='tenant-b')
    record_agent_assignment(db, request_id='legacy-agent-1', agent_id='agent-a',
        principal_id='user-a', tenant_id='tenant-a')
    assert is_agent_assignment(db, 'legacy-agent-1')
    with sqlite3.connect(db) as reopened:
        assert reopened.execute('SELECT agent_id, principal_id, tenant_id FROM desktop_agent_assignments '
            'WHERE request_id=?', ('legacy-agent-1',)).fetchone() == ('agent-a', 'user-a', 'tenant-a')
    assert is_agent_assignment(db, 'legacy-agent-1')
