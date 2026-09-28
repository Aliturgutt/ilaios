import hashlib
import io
import json
import sqlite3
import zipfile
import pytest
from services.desktop_agent_web_upload_gate import inspect_web_worker_upload


def archive(name='src/page.tsx'):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as bundle:
        bundle.writestr(name, 'export default function Page() {return null;}')
    return data.getvalue()


def database(tmp_path, content=None):
    content = archive() if content is None else content
    digest = hashlib.sha256(content).hexdigest()
    tmp_path.mkdir(parents=True, exist_ok=True)
    db = tmp_path / 'worker.sqlite'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE execution_requests (request_id TEXT, principal_id TEXT, tenant_id TEXT, status TEXT)')
        conn.execute('CREATE TABLE desktop_agent_assignments (request_id TEXT, agent_id TEXT, principal_id TEXT, tenant_id TEXT)')
        conn.execute('CREATE TABLE desktop_agent_result_receipts (request_id TEXT, agent_id TEXT, payload TEXT)')
        conn.execute('CREATE TABLE desktop_agent_artifacts (request_id TEXT, sha256 TEXT, content BLOB)')
        conn.execute("INSERT INTO execution_requests VALUES ('child','owner','tenant','ADMITTED')")
        conn.execute("INSERT INTO desktop_agent_assignments VALUES ('child','web-agent','owner','tenant')")
        conn.execute('INSERT INTO desktop_agent_result_receipts VALUES (?,?,?)',
            ('child','web-agent',json.dumps({'status':'completed','artifact_sha256':digest})))
        conn.execute('INSERT INTO desktop_agent_artifacts VALUES (?,?,?)', ('child',digest,content))
    return db


def inspect(db, **overrides):
    args = dict(request_id='child',agent_id='web-agent',principal_id='owner',tenant_id='tenant')
    return inspect_web_worker_upload(db, **dict(args, **overrides))


def test_valid_bundle_is_quarantined_not_accepted(tmp_path):
    result = inspect(database(tmp_path))
    assert result['quarantined'] and not result['runtime_consumed']
    assert not result['coordinator_accepted']


def test_cross_tenant_wrong_agent_and_tamper_denied(tmp_path):
    db = database(tmp_path)
    for change in ({'tenant_id':'other'}, {'agent_id':'other'}):
        with pytest.raises(PermissionError):
            inspect(db, **change)
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE desktop_agent_artifacts SET content=?',(b'forged',))
    with pytest.raises(PermissionError):
        inspect(db)


def test_zip_traversal_and_non_zip_denied(tmp_path):
    for name in ('../escape.txt', '/absolute.txt', 'src/../../escape'):
        with pytest.raises(PermissionError):
            inspect(database(tmp_path / name.replace('/','_'),archive(name)))

