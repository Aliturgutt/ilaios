"""Durable, content-addressed staging for authenticated quarantined Web bundles.

Staging is not product consumption, QA or coordinator acceptance. The native
Web builder must explicitly consume these bytes and independently attest QA.
"""
import hashlib
import os
import sqlite3
import tempfile
from pathlib import Path
from services.desktop_agent_web_upload_gate import inspect_web_worker_upload


def stage_web_worker_upload(db, root, *, request_id, agent_id, principal_id, tenant_id):
    proof = inspect_web_worker_upload(db, request_id=request_id, agent_id=agent_id,
        principal_id=principal_id, tenant_id=tenant_id)
    with sqlite3.connect(db, timeout=10) as conn:
        row = conn.execute('SELECT content FROM desktop_agent_artifacts WHERE request_id=? '
            'AND sha256=?', (request_id, proof['artifact_sha256'])).fetchone()
    if row is None or hashlib.sha256(row[0]).hexdigest() != proof['artifact_sha256']:
        raise PermissionError('worker upload changed after quarantine')
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    target = root / (proof['artifact_sha256'] + '.zip')
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != proof['artifact_sha256']:
            raise PermissionError('staged Web artifact collision')
        return {**proof, 'staged_path':str(target), 'reused':True}
    fd, temporary = tempfile.mkstemp(prefix='.web-', dir=root)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(row[0])
            stream.flush()
            os.fsync(stream.fileno())
        # A concurrent identical stage may already exist; never overwrite it.
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != proof['artifact_sha256']:
                raise PermissionError('staged Web artifact collision')
        else:
            os.replace(temporary, target)
        return {**proof, 'staged_path':str(target), 'reused':False}
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
