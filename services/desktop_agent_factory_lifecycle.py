"""Atomic, owner-bound multi-factory plan persistence.

This records a verified plan, not an execution or permission to dispatch.
Individual factory tasks require separate coordinator admission and receipts.
"""
import sqlite3
from pathlib import Path
from services.desktop_agent_factory_plan import FactoryAssignment


def record_factory_plan(db: Path, *, request_id: str, principal_id: str,
                        tenant_id: str, assignments: tuple[FactoryAssignment, ...]) -> None:
    if not all((request_id, principal_id, tenant_id)) or not assignments:
        raise ValueError('complete owner-bound factory plan required')
    if (len({item.capability_id for item in assignments}) != len(assignments)
            or len({item.agent_id for item in assignments}) != len(assignments)
            or any(not all((item.capability_id, item.agent_id, item.adapter_id))
                   for item in assignments)):
        raise ValueError('duplicate or incomplete factory assignment')
    with sqlite3.connect(db, timeout=10) as conn:
        conn.execute('BEGIN IMMEDIATE')
        owner = conn.execute('SELECT principal_id, tenant_id FROM execution_requests '
                             'WHERE request_id=?', (request_id,)).fetchone()
        if owner != (principal_id, tenant_id):
            raise PermissionError('coordinator ownership mismatch')
        conn.execute('CREATE TABLE IF NOT EXISTS desktop_factory_plans ('
            'request_id TEXT NOT NULL, capability_id TEXT NOT NULL, '
            'agent_id TEXT NOT NULL, adapter_id TEXT NOT NULL, '
            'principal_id TEXT NOT NULL, tenant_id TEXT NOT NULL, '
            'PRIMARY KEY(request_id, capability_id), '
            'UNIQUE(request_id, agent_id), '
            'FOREIGN KEY(request_id) REFERENCES execution_requests(request_id))')
        if conn.execute('SELECT 1 FROM desktop_factory_plans WHERE request_id=?',
                        (request_id,)).fetchone():
            raise PermissionError('factory plan already recorded')
        conn.executemany('INSERT INTO desktop_factory_plans VALUES (?,?,?,?,?,?)',
            [(request_id, item.capability_id, item.agent_id, item.adapter_id,
              principal_id, tenant_id) for item in assignments])


def read_factory_plan(db: Path, *, request_id: str, principal_id: str,
                      tenant_id: str) -> tuple[FactoryAssignment, ...]:
    with sqlite3.connect(db, timeout=10) as conn:
        owner = conn.execute('SELECT principal_id, tenant_id FROM execution_requests '
                             'WHERE request_id=?', (request_id,)).fetchone()
        if owner != (principal_id, tenant_id):
            raise PermissionError('coordinator ownership mismatch')
        rows = conn.execute('SELECT capability_id, agent_id, adapter_id '
            'FROM desktop_factory_plans WHERE request_id=? '
            'AND principal_id=? AND tenant_id=? ORDER BY rowid',
            (request_id, principal_id, tenant_id)).fetchall()
        return tuple(FactoryAssignment(*row) for row in rows)
