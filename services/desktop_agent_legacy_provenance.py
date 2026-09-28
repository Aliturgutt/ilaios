"""Conservative historical provenance: ambiguous factory jobs require review."""
from __future__ import annotations
import sqlite3
from pathlib import Path
from services.desktop_agent_assignment_store import is_agent_assignment


def requires_agent_resume_guard(db: Path | None, request_id: str) -> bool:
    if request_id.startswith('agentexec-'):
        return True
    if db is None:
        return False
    if is_agent_assignment(db, request_id):
        return True
    with sqlite3.connect(db, timeout=10) as conn:
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                              "AND name='execution_requests'").fetchone()
        if not exists:
            return False
        # Historical video factory tasks cannot be proven human-only merely
        # because an assignment provenance record is absent.
        row = conn.execute('SELECT adapter_id FROM execution_requests '
                           'WHERE request_id=?', (request_id,)).fetchone()
        return bool(row and row[0] == 'video.product-runtime.v1')
