"""Authenticated, durable, agent-bound delivery lease for Desktop-owned tasks."""
from __future__ import annotations
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


class AgentDelivery:
    def __init__(self, db: Path, credentials: dict[str, str]):
        if not credentials or any(not a or not s for a, s in credentials.items()):
            raise ValueError('server-provisioned agent credentials required')
        self.db, self.credentials = db, dict(credentials)

    def _auth(self, agent: str, secret: str) -> None:
        expected = self.credentials.get(agent)
        if not expected or not secret or not hmac.compare_digest(expected, secret):
            raise PermissionError('agent authentication failed')

    def _schema(self, conn):
        conn.execute('CREATE TABLE IF NOT EXISTS desktop_agent_deliveries ('
                     'request_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, '
                     'lease_hash TEXT NOT NULL, expires_at TEXT NOT NULL, '
                     'acknowledged INTEGER NOT NULL DEFAULT 0)')

    def claim(self, *, request_id: str, agent_id: str, secret: str, now: datetime) -> str:
        self._auth(agent_id, secret)
        if now.tzinfo is None:
            raise ValueError('timezone-aware time required')
        with sqlite3.connect(self.db, timeout=10) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self._schema(conn)
            assignment = conn.execute('SELECT a.agent_id, e.status FROM desktop_agent_assignments a '
                'JOIN execution_requests e ON e.request_id=a.request_id '
                'AND e.principal_id=a.principal_id AND e.tenant_id=a.tenant_id '
                'WHERE a.request_id=?', (request_id,)).fetchone()
            if assignment is None or assignment[0] != agent_id or assignment[1] != 'ADMITTED':
                raise PermissionError('task is not assigned to this agent')
            current = conn.execute('SELECT expires_at, acknowledged FROM desktop_agent_deliveries '
                'WHERE request_id=?', (request_id,)).fetchone()
            if current and (current[1] or datetime.fromisoformat(current[0]) >= now):
                raise PermissionError('delivery already claimed or acknowledged')
            token = secrets.token_urlsafe(32)
            import hashlib
            digest = hashlib.sha256(token.encode()).hexdigest()
            conn.execute('INSERT OR REPLACE INTO desktop_agent_deliveries '
                '(request_id,agent_id,lease_hash,expires_at,acknowledged) VALUES (?,?,?,?,0)',
                (request_id, agent_id, digest, (now + timedelta(seconds=30)).isoformat()))
            return token

    def acknowledge(self, *, request_id: str, agent_id: str, secret: str,
                    lease: str, now: datetime) -> bool:
        self._auth(agent_id, secret)
        import hashlib
        digest = hashlib.sha256(lease.encode()).hexdigest()
        with sqlite3.connect(self.db, timeout=10) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT agent_id,lease_hash,expires_at,acknowledged '
                'FROM desktop_agent_deliveries WHERE request_id=?', (request_id,)).fetchone()
            if not row or row[0] != agent_id or not hmac.compare_digest(row[1], digest) or row[3]:
                raise PermissionError('invalid or consumed delivery lease')
            if now.tzinfo is None or now > datetime.fromisoformat(row[2]):
                raise PermissionError('expired delivery lease')
            conn.execute('UPDATE desktop_agent_deliveries SET acknowledged=1 WHERE request_id=?',
                         (request_id,))
            return True
