import sqlite3
from pathlib import Path
import pytest
from services.desktop_agent_factory_lifecycle import record_factory_plan, read_factory_plan
from services.desktop_agent_factory_plan import FactoryAssignment


def database(tmp_path: Path):
    db = tmp_path / 'coordinator.sqlite'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE execution_requests ('
            'request_id TEXT PRIMARY KEY, principal_id TEXT, tenant_id TEXT)')
        conn.execute('INSERT INTO execution_requests VALUES (?,?,?)',
                     ('request-1', 'owner-1', 'tenant-1'))
    return db


def plan():
    return (FactoryAssignment('video', 'agent-video', 'adapter-video'),
            FactoryAssignment('web', 'agent-web', 'adapter-web'))


def test_atomic_plan_round_trip_and_no_duplicate(tmp_path):
    db = database(tmp_path)
    record_factory_plan(db, request_id='request-1', principal_id='owner-1',
                        tenant_id='tenant-1', assignments=plan())
    assert read_factory_plan(db, request_id='request-1', principal_id='owner-1',
                             tenant_id='tenant-1') == plan()
    with pytest.raises(PermissionError):
        record_factory_plan(db, request_id='request-1', principal_id='owner-1',
                            tenant_id='tenant-1', assignments=plan())
    assert read_factory_plan(db, request_id='request-1', principal_id='owner-1',
                             tenant_id='tenant-1') == plan()


def test_wrong_owner_denied_without_partial_write(tmp_path):
    db = database(tmp_path)
    with pytest.raises(PermissionError):
        record_factory_plan(db, request_id='request-1', principal_id='other',
                            tenant_id='tenant-1', assignments=plan())
    with pytest.raises(PermissionError):
        read_factory_plan(db, request_id='request-1', principal_id='owner-1',
                          tenant_id='other')
    with pytest.raises(ValueError):
        record_factory_plan(db, request_id='request-1', principal_id='owner-1',
                            tenant_id='tenant-1', assignments=(plan()[0], plan()[0]))
    record_factory_plan(db, request_id='request-1', principal_id='owner-1',
                        tenant_id='tenant-1', assignments=plan())
    assert len(read_factory_plan(db, request_id='request-1', principal_id='owner-1',
                                 tenant_id='tenant-1')) == 2
