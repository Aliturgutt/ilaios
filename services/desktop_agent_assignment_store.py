"""Durable server-owned agent assignment provenance in coordinator SQLite."""
from __future__ import annotations
import sqlite3
from pathlib import Path


def record_agent_assignment(db: Path, *, request_id: str, agent_id: str,
                            principal_id: str, tenant_id: str) -> None:
    if not all((request_id, agent_id, principal_id, tenant_id)):
        raise ValueError('complete agent assignment provenance required')
    with sqlite3.connect(db, timeout=10) as connection:
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('CREATE TABLE IF NOT EXISTS desktop_agent_assignments ('
            'request_id TEXT PRIMARY KEY REFERENCES execution_requests(request_id), '
            'agent_id TEXT NOT NULL, principal_id TEXT NOT NULL, tenant_id TEXT NOT NULL)')
        row = connection.execute('SELECT principal_id, tenant_id FROM execution_requests '
                                 'WHERE request_id=?', (request_id,)).fetchone()
        if row != (principal_id, tenant_id):
            raise ValueError('coordinator ownership mismatch')
        connection.execute('INSERT INTO desktop_agent_assignments VALUES (?, ?, ?, ?)',
                           (request_id, agent_id, principal_id, tenant_id))


def is_agent_assignment(db: Path, request_id: str) -> bool:
    with sqlite3.connect(db, timeout=10) as connection:
        exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                                    "AND name='desktop_agent_assignments'").fetchone()
        if not exists:
            return False
        return connection.execute('SELECT 1 FROM desktop_agent_assignments '
                                  'WHERE request_id=?', (request_id,)).fetchone() is not None
