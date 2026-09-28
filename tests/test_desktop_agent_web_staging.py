import hashlib
import sqlite3
import pytest
from services.desktop_agent_web_staging import stage_web_worker_upload
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from test_desktop_agent_web_upload_gate import database


def stage(db, root, **changes):
    args = dict(request_id='child',agent_id='web-agent',principal_id='owner',tenant_id='tenant')
    return stage_web_worker_upload(db,root,**dict(args,**changes))


def test_real_worker_zip_staged_durably_and_restart_is_idempotent(tmp_path):
    db = database(tmp_path)
    root = tmp_path / 'staged'
    first = stage(db,root)
    assert first['runtime_consumed'] is False
    assert first['coordinator_accepted'] is False
    assert hashlib.sha256(open(first['staged_path'],'rb').read()).hexdigest() == first['artifact_sha256']
    second = stage(db,root)
    assert second['reused'] is True
    assert second['staged_path'] == first['staged_path']


def test_wrong_owner_agent_and_forged_upload_fail_before_stage(tmp_path):
    db = database(tmp_path)
    root = tmp_path / 'staged'
    for change in ({'tenant_id':'other'},{'agent_id':'other'}):
        with pytest.raises(PermissionError):
            stage(db,root,**change)
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE desktop_agent_artifacts SET content=?',(b'forged',))
    with pytest.raises(PermissionError):
        stage(db,root)
    assert not root.exists()


def test_staged_content_tamper_denied_on_reconnect(tmp_path):
    db = database(tmp_path)
    first = stage(db,tmp_path/'staged')
    with open(first['staged_path'],'wb') as stream:
        stream.write(b'forged')
    with pytest.raises(PermissionError):
        stage(db,tmp_path/'staged')

