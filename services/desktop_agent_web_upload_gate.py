"""Quarantined Web upload validation before any product runtime may consume it.

The current Web runtime builds its own generated site; this gate does not
pretend it consumed an uploaded worker bundle or authorize coordinator accept.
"""
import hashlib
import io
import json
import sqlite3
import zipfile
from pathlib import PurePosixPath


def inspect_web_worker_upload(db, *, request_id, agent_id, principal_id, tenant_id):
    with sqlite3.connect(db, timeout=10) as conn:
        row = conn.execute('SELECT r.payload,a.sha256,a.content FROM '
            'desktop_agent_assignments d JOIN execution_requests e '
            'ON e.request_id=d.request_id AND e.principal_id=d.principal_id '
            'AND e.tenant_id=d.tenant_id JOIN desktop_agent_result_receipts r '
            'ON r.request_id=d.request_id AND r.agent_id=d.agent_id '
            'JOIN desktop_agent_artifacts a ON a.request_id=d.request_id '
            'WHERE d.request_id=? AND d.agent_id=? AND d.principal_id=? '
            "AND d.tenant_id=? AND e.status='ADMITTED'",
            (request_id, agent_id, principal_id, tenant_id)).fetchone()
    if not row or hashlib.sha256(row[2]).hexdigest() != row[1]:
        raise PermissionError('missing or corrupt owner-bound worker upload')
    receipt = json.loads(row[0])
    if receipt != {'status':'completed', 'artifact_sha256':row[1]}:
        raise PermissionError('worker receipt does not match uploaded bundle')
    try:
        with zipfile.ZipFile(io.BytesIO(row[2])) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > 128:
                raise ValueError('invalid Web archive entry count')
            seen = set()
            for entry in entries:
                name = entry.filename
                path = PurePosixPath(name)
                if (not name or '\\' in name or path.is_absolute()
                        or any(part in ('', '.', '..') for part in name.rstrip('/').split('/'))
                        or name.rstrip('/') in seen or entry.file_size > 1024 * 1024
                        or entry.flag_bits & 1 or (entry.external_attr >> 16) & 0o170000 == 0o120000):
                    raise ValueError('unsafe Web archive entry')
                seen.add(name.rstrip('/'))
            if sum(item.file_size for item in entries) > 1024 * 1024:
                raise ValueError('oversized Web archive')
    except (ValueError, zipfile.BadZipFile) as error:
        raise PermissionError('invalid quarantined Web upload') from error
    return {'quarantined':True, 'request_id':request_id, 'agent_id':agent_id,
            'artifact_sha256':row[1], 'entry_count':len(entries),
            'runtime_consumed':False, 'coordinator_accepted':False}
