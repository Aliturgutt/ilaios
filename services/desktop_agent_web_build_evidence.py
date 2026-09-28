"""Reconcile opt-in Web build evidence against original worker bytes and build output.

This is integrity reconciliation, not an attestation of sandbox provenance.
"""
import hashlib
import sqlite3
from pathlib import Path


def reconcile_web_build_evidence(db, evidence, source_root):
    if (not isinstance(evidence, dict) or evidence.get('build_passed') is not True
            or evidence.get('typecheck_passed') is not True
            or evidence.get('coordinator_accepted') is not False):
        raise PermissionError('untrusted Web build evidence')
    digest = evidence.get('worker_artifact_sha256')
    if not isinstance(digest, str) or len(digest) != 64:
        raise PermissionError('invalid worker digest')
    with sqlite3.connect(db, timeout=10) as conn:
        row = conn.execute('SELECT a.sha256,a.content FROM desktop_agent_artifacts a '
            'JOIN desktop_agent_assignments d ON d.request_id=a.request_id '
            'WHERE d.request_id=? AND d.agent_id=? AND d.principal_id=? AND d.tenant_id=?',
            (evidence.get('request_id'), evidence.get('agent_id'),
             evidence.get('principal_id'), evidence.get('tenant_id'))).fetchone()
    if not row or row[0] != digest or hashlib.sha256(row[1]).hexdigest() != digest:
        raise PermissionError('build evidence is not bound to worker upload')
    build = Path(source_root) / digest / '.next' / 'BUILD_ID'
    if (not build.is_file() or not build.read_bytes()
            or hashlib.sha256(build.read_bytes()).hexdigest() != evidence.get('build_id_sha256')):
        raise PermissionError('build output does not match reported evidence')
    if [step.get('command') for step in evidence.get('steps', [])] != [
            ['ci','--ignore-scripts','--offline'], ['run','typecheck'], ['run','build']]:
        raise PermissionError('required build steps missing')
    if any(step.get('exit_code') != 0 for step in evidence['steps']):
        raise PermissionError('failed build step')
    return {'integrity_verified':True, 'worker_artifact_sha256':digest,
            'build_id_sha256':evidence['build_id_sha256'],
            'sandbox_attested':False, 'coordinator_accepted':False}
