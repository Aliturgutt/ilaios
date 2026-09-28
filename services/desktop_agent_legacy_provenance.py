"""Conservative provenance guard for all historical coordinator adapters.

A legacy execution row does not prove human-only origin. Historical rows are
quarantined from generic resume pending independently verified provenance.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path


def requires_agent_resume_guard(db: Path | None, request_id: str) -> bool:
    if not request_id or request_id.startswith('agentexec-'):
        return True
    if db is None:
        # This compatibility branch only applies to coordinators without a
        # database path (e.g. old in-memory test doubles).
        return False
    try:
        with sqlite3.connect(f'file:{db.as_posix()}?mode=ro', uri=True, timeout=10) as conn:
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if 'execution_requests' not in tables:
                return True
            row = conn.execute('SELECT 1 FROM execution_requests WHERE request_id=?',
                               (request_id,)).fetchone()
            if row is None:
                return False
            if 'desktop_agent_assignments' in tables and conn.execute(
                'SELECT 1 FROM desktop_agent_assignments WHERE request_id=?',
                (request_id,)).fetchone():
                return True
            return not ('desktop_human_intents' in tables and conn.execute(
                'SELECT 1 FROM desktop_human_intents WHERE request_id=?',
                (request_id,)).fetchone())
    except (sqlite3.Error, OSError):
        return True
