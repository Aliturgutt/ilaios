"""Atomic admission of canonical child tasks to shared authenticated delivery.

No child is bound unless all canonical child requests exist, are independently
ADMITTED and owned by the same principal/tenant. Never creates fake child tasks.
"""
import sqlite3
from services.desktop_agent_factory_coordinator_binding import inspect_factory_execution


def bind_admitted_factory_children(db, *, request_id, principal_id, tenant_id):
    verified = inspect_factory_execution(db, request_id=request_id,
        principal_id=principal_id, tenant_id=tenant_id)
    if not verified['ready']:
        raise PermissionError('canonical factory plan not admitted')
    steps = verified['steps']
    child_ids = [step['child_request_id'] for step in steps]
    if len(child_ids) != len(set(child_ids)) or request_id in child_ids:
        raise PermissionError('duplicate or recursive factory child')
    with sqlite3.connect(db, timeout=10) as conn:
        conn.execute('BEGIN IMMEDIATE')
        parent = conn.execute('SELECT status FROM execution_requests WHERE request_id=? '
            'AND principal_id=? AND tenant_id=?',
            (request_id, principal_id, tenant_id)).fetchone()
        rows = conn.execute('SELECT capability_id, adapter_id, child_request_id, status '
            'FROM execution_steps WHERE request_id=? ORDER BY step_index',
            (request_id,)).fetchall()
        if (parent != ('ADMITTED',) or len(rows) != len(steps)
                or any(tuple(row) != (step['capability_id'], step['adapter_id'],
                                    step['child_request_id'], 'ADMITTED')
                       for row, step in zip(rows, steps))):
            raise PermissionError('canonical factory admission changed')
        for step in steps:
            child = conn.execute('SELECT principal_id, tenant_id, status, capability_id, '
                'adapter_id FROM execution_requests WHERE request_id=?',
                (step['child_request_id'],)).fetchone()
            if child != (principal_id, tenant_id, 'ADMITTED',
                         step['capability_id'], step['adapter_id']):
                raise PermissionError('child admission or ownership mismatch')
        conn.execute('CREATE TABLE IF NOT EXISTS desktop_agent_assignments ('
            'request_id TEXT PRIMARY KEY REFERENCES execution_requests(request_id), '
            'agent_id TEXT NOT NULL, principal_id TEXT NOT NULL, tenant_id TEXT NOT NULL)')
        for step in steps:
            if conn.execute('SELECT 1 FROM desktop_agent_assignments WHERE request_id=?',
                            (step['child_request_id'],)).fetchone():
                raise PermissionError('child already assigned')
        conn.executemany('INSERT INTO desktop_agent_assignments VALUES (?,?,?,?)',
            [(step['child_request_id'], step['agent_id'], principal_id, tenant_id)
             for step in steps])
    return tuple((step['child_request_id'], step['agent_id']) for step in steps)
