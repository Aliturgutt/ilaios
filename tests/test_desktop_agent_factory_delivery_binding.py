import sqlite3
import pytest
from services.desktop_agent_factory_delivery_binding import bind_admitted_factory_children
from services.desktop_agent_factory_lifecycle import record_factory_plan
from services.desktop_agent_factory_plan import FactoryAssignment
from services.desktop_agent_delivery import AgentDelivery
from datetime import datetime, timezone


def database(tmp_path, *, bad_child=False):
    db = tmp_path / 'coordinator.sqlite'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE execution_requests (request_id TEXT PRIMARY KEY, '
            'principal_id TEXT, tenant_id TEXT, status TEXT, capability_id TEXT, adapter_id TEXT)')
        conn.executemany('INSERT INTO execution_requests VALUES (?,?,?,?,?,?)', [
            ('parent', 'owner', 'tenant', 'ADMITTED', 'multi', 'multi'),
            ('child-web', 'owner', 'tenant', 'ADMITTED', 'web', 'web-adapter'),
            ('child-video', 'owner', 'other' if bad_child else 'tenant',
             'ADMITTED', 'video', 'video-adapter')])
        conn.execute('CREATE TABLE execution_steps (request_id TEXT, step_index INTEGER, '
            'capability_id TEXT, adapter_id TEXT, child_request_id TEXT, status TEXT)')
        conn.executemany('INSERT INTO execution_steps VALUES (?,?,?,?,?,?)', [
            ('parent', 0, 'web', 'web-adapter', 'child-web', 'ADMITTED'),
            ('parent', 1, 'video', 'video-adapter', 'child-video', 'ADMITTED')])
    record_factory_plan(db, request_id='parent', principal_id='owner',
        tenant_id='tenant', assignments=(FactoryAssignment('web','agent-web','web-adapter'),
                                        FactoryAssignment('video','agent-video','video-adapter')))
    return db


def test_two_factory_children_bind_and_lease_independently(tmp_path):
    db = database(tmp_path)
    assert bind_admitted_factory_children(db, request_id='parent',
        principal_id='owner', tenant_id='tenant') == (
        ('child-web', 'agent-web'), ('child-video', 'agent-video'))
    delivery = AgentDelivery(db, {'agent-web':'web-secret','agent-video':'video-secret'})
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    web_lease = delivery.claim(request_id='child-web', agent_id='agent-web',
                               secret='web-secret', now=now)
    video_lease = delivery.claim(request_id='child-video', agent_id='agent-video',
                                 secret='video-secret', now=now)
    assert web_lease != video_lease
    with pytest.raises(PermissionError):
        delivery.claim(request_id='child-web', agent_id='agent-video',
                       secret='video-secret', now=now)
    with pytest.raises(PermissionError):
        bind_admitted_factory_children(db, request_id='parent',
            principal_id='owner', tenant_id='tenant')


def test_cross_tenant_child_blocks_entire_batch(tmp_path):
    db = database(tmp_path, bad_child=True)
    with pytest.raises(PermissionError):
        bind_admitted_factory_children(db, request_id='parent',
            principal_id='owner', tenant_id='tenant')
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT name FROM sqlite_master WHERE name='desktop_agent_assignments'").fetchone() is None
