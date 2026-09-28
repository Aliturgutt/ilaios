"""Read-only reconciliation of durable factory plans with canonical coordinator steps.

Never turns a plan into a dispatch or changes coordinator state. Workers must
still pass separate task admission, lease, receipt and adapter acceptance.
"""
import sqlite3
from services.desktop_agent_factory_lifecycle import read_factory_plan


def inspect_factory_execution(db, *, request_id, principal_id, tenant_id):
    assignments = read_factory_plan(db, request_id=request_id,
        principal_id=principal_id, tenant_id=tenant_id)
    if not assignments:
        return {'ready': False, 'reason': 'factory_plan_missing', 'steps': ()}
    with sqlite3.connect(db, timeout=10) as conn:
        parent = conn.execute('SELECT status FROM execution_requests '
            'WHERE request_id=? AND principal_id=? AND tenant_id=?',
            (request_id, principal_id, tenant_id)).fetchone()
        table = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='execution_steps'").fetchone()
        if not parent or not table:
            return {'ready': False, 'reason': 'coordinator_steps_missing', 'steps': ()}
        rows = conn.execute('SELECT capability_id, adapter_id, child_request_id, status '
            'FROM execution_steps WHERE request_id=? ORDER BY step_index',
            (request_id,)).fetchall()
    expected = tuple((item.capability_id, item.adapter_id) for item in assignments)
    actual = tuple((row[0], row[1]) for row in rows)
    if actual != expected or any(not row[2] for row in rows):
        return {'ready': False, 'reason': 'coordinator_plan_mismatch', 'steps': ()}
    steps = tuple({'capability_id': item.capability_id,
        'agent_id': item.agent_id, 'adapter_id': item.adapter_id,
        'child_request_id': row[2], 'coordinator_status': row[3]}
        for item, row in zip(assignments, rows))
    return {'ready': parent[0] == 'ADMITTED' and all(row[3] == 'ADMITTED' for row in rows),
            'parent_status': parent[0], 'steps': steps}
