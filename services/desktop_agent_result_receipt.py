"""Quarantined worker result receipt: never marks coordinator execution accepted."""
import hashlib
import hmac
import json
import sqlite3
from datetime import datetime


class AgentResultReceipt:
    def __init__(self, delivery):
        self.delivery = delivery

    def submit(self, *, request_id, agent_id, secret, lease, result, now, artifact=None):
        self.delivery._auth(agent_id, secret)
        if artifact is not None:
            if not isinstance(artifact, bytes) or not artifact or len(artifact) > 1024 * 1024:
                raise ValueError('invalid artifact bytes')
            if not isinstance(result, dict) or hashlib.sha256(artifact).hexdigest() != result.get('artifact_sha256'):
                raise ValueError('artifact digest mismatch')
        if not isinstance(result, dict) or set(result) != {'status', 'artifact_sha256'}:
            raise ValueError('invalid result shape')
        if result['status'] not in ('completed', 'failed'):
            raise ValueError('invalid result status')
        digest = result['artifact_sha256']
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('artifact digest required')
        if not isinstance(lease, str) or not lease or now.tzinfo is None:
            raise PermissionError('invalid receipt authorization')
        lease_hash = hashlib.sha256(lease.encode()).hexdigest()
        payload = json.dumps(result, sort_keys=True, separators=(',', ':'))
        with sqlite3.connect(self.delivery.db, timeout=10) as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('CREATE TABLE IF NOT EXISTS desktop_agent_result_receipts ('
                'request_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, '
                'payload TEXT NOT NULL, received_at TEXT NOT NULL)')
            row = conn.execute('SELECT d.agent_id,d.lease_hash,d.expires_at,d.acknowledged, '
                'a.tenant_id,e.status FROM desktop_agent_deliveries d '
                'JOIN desktop_agent_assignments a ON a.request_id=d.request_id '
                'AND a.agent_id=d.agent_id JOIN execution_requests e '
                'ON e.request_id=a.request_id AND e.principal_id=a.principal_id '
                'AND e.tenant_id=a.tenant_id WHERE d.request_id=?', (request_id,)).fetchone()
            if not row or row[0] != agent_id or not hmac.compare_digest(row[1], lease_hash) or not row[3] or row[5] != 'ADMITTED':
                raise PermissionError('unauthorized result')
            if now > datetime.fromisoformat(row[2]):
                raise PermissionError('result lease expired')
            if conn.execute('SELECT 1 FROM desktop_agent_result_receipts WHERE request_id=?',
                            (request_id,)).fetchone():
                raise PermissionError('result already submitted')
            conn.execute('CREATE TABLE IF NOT EXISTS desktop_agent_artifacts ('
                'request_id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, content BLOB NOT NULL)')
            if artifact is not None:
                conn.execute('INSERT INTO desktop_agent_artifacts VALUES (?,?,?)',
                             (request_id, digest, artifact))
            conn.execute('INSERT INTO desktop_agent_result_receipts VALUES (?,?,?,?)',
                         (request_id, agent_id, payload, now.isoformat()))
            return {'received': True, 'coordinator_accepted': False}
