"""Server-issued human intent provenance; never infer legacy origin."""
import sqlite3
from pathlib import Path


def record_human_intent(db: Path, request_id: str, principal_id: str, tenant_id: str) -> None:
    if not all((request_id, principal_id, tenant_id)) or not request_id.startswith('exec-'):
        raise ValueError('invalid server-issued human intent')
    with sqlite3.connect(db, timeout=10) as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('CREATE TABLE IF NOT EXISTS desktop_human_intents ('
            'request_id TEXT PRIMARY KEY, principal_id TEXT NOT NULL, tenant_id TEXT NOT NULL)')
        row = conn.execute('SELECT principal_id, tenant_id FROM execution_requests '
                           'WHERE request_id=?', (request_id,)).fetchone()
        if row != (principal_id, tenant_id):
            raise ValueError('human intent owner mismatch')
        conn.execute('INSERT INTO desktop_human_intents VALUES (?, ?, ?)',
                     (request_id, principal_id, tenant_id))
