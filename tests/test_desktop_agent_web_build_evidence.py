import hashlib
import sqlite3
import pytest
from services.desktop_agent_web_build_evidence import reconcile_web_build_evidence


def fixture(tmp_path):
    db=tmp_path/'evidence.sqlite'
    payload=b'worker-archive'
    digest=hashlib.sha256(payload).hexdigest()
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE desktop_agent_artifacts (request_id TEXT, sha256 TEXT, content BLOB)')
        conn.execute('CREATE TABLE desktop_agent_assignments (request_id TEXT, agent_id TEXT, principal_id TEXT, tenant_id TEXT)')
        conn.execute('INSERT INTO desktop_agent_artifacts VALUES (?,?,?)',('r',digest,payload))
        conn.execute("INSERT INTO desktop_agent_assignments VALUES ('r','a','p','t')")
    build=tmp_path/digest/'.next'/'BUILD_ID'
    build.parent.mkdir(parents=True)
    build.write_bytes(b'build-123')
    evidence=dict(request_id='r',agent_id='a',principal_id='p',tenant_id='t',
        worker_artifact_sha256=digest,build_id_sha256=hashlib.sha256(b'build-123').hexdigest(),
        build_passed=True,typecheck_passed=True,coordinator_accepted=False,
        steps=[{'command':c,'exit_code':0} for c in
            (['ci','--ignore-scripts','--offline'],['run','typecheck'],['run','build'])])
    return db,evidence,build


def test_evidence_integrity_and_reconnect(tmp_path):
    db,evidence,build=fixture(tmp_path)
    for _ in range(2):
        result=reconcile_web_build_evidence(db,evidence,tmp_path)
        assert result['integrity_verified'] and not result['sandbox_attested']


def test_tampered_build_wrong_agent_tenant_and_worker_payload_denied(tmp_path):
    db,evidence,build=fixture(tmp_path)
    for key,bad in [('agent_id','other'),('tenant_id','other'),('build_id_sha256','0'*64)]:
        original=evidence[key]
        evidence[key]=bad
        with pytest.raises(PermissionError):
            reconcile_web_build_evidence(db,evidence,tmp_path)
        evidence[key]=original
    build.write_bytes(b'tampered')
    with pytest.raises(PermissionError):
        reconcile_web_build_evidence(db,evidence,tmp_path)
