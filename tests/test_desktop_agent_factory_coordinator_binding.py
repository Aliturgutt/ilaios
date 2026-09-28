import sqlite3
import pytest
from services.desktop_agent_factory_coordinator_binding import inspect_factory_execution
from services.desktop_agent_factory_lifecycle import record_factory_plan
from services.desktop_agent_factory_plan import FactoryAssignment


def setup(tmp_path):
    db = tmp_path / 'coordinator.sqlite'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE execution_requests ('
            'request_id TEXT PRIMARY KEY, principal_id TEXT, tenant_id TEXT, status TEXT)')
        conn.execute('INSERT INTO execution_requests VALUES (?,?,?,?)',
                     ('parent', 'owner', 'tenant', 'ADMITTED'))
        conn.execute('CREATE TABLE execution_steps ('
            'request_id TEXT, step_index INTEGER, capability_id TEXT, '
            'adapter_id TEXT, child_request_id TEXT, status TEXT)')
        conn.executemany('INSERT INTO execution_steps VALUES (?,?,?,?,?,?)', [
            ('parent', 0, 'web', 'web-adapter', 'child-web', 'ADMITTED'),
            ('parent', 1, 'video', 'video-adapter', 'child-video', 'ADMITTED')])
    record_factory_plan(db, request_id='parent', principal_id='owner',
        tenant_id='tenant', assignments=(FactoryAssignment('web', 'web-agent', 'web-adapter'),
                                        FactoryAssignment('video', 'video-agent', 'video-adapter')))
    return db


def inspect(db):
    return inspect_factory_execution(db, request_id='parent', principal_id='owner',
                                     tenant_id='tenant')


def test_matching_coordinator_steps_are_bound_without_dispatch(tmp_path):
    db = setup(tmp_path)
    result = inspect(db)
    assert result['ready'] is True
    assert [step['child_request_id'] for step in result['steps']] == ['child-web', 'child-video']
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT status FROM execution_steps ORDER BY step_index').fetchall() == [('ADMITTED',), ('ADMITTED',)]


def test_step_or_parent_not_admitted_fails_closed(tmp_path):
    db = setup(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE execution_steps SET status='PLANNED' WHERE step_index=1")
    assert inspect(db)['ready'] is False
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE execution_steps SET status='ADMITTED'")
        conn.execute("UPDATE execution_requests SET status='PENDING_APPROVAL'")
    assert inspect(db)['ready'] is False


def test_adapter_mismatch_and_cross_tenant_access_denied(tmp_path):
    db = setup(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE execution_steps SET adapter_id='unverified' WHERE step_index=1")
    assert inspect(db)['reason'] == 'coordinator_plan_mismatch'
    with pytest.raises(PermissionError):
        inspect_factory_execution(db, request_id='parent', principal_id='owner', tenant_id='other')
