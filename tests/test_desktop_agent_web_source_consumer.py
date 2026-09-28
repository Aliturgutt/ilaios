import io
import json
import zipfile
import pytest
from services.desktop_agent_web_source_consumer import consume_staged_web_source
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from test_desktop_agent_web_upload_gate import database


def bundle(valid=True):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream,'w') as archive:
        archive.writestr('package.json',json.dumps({'scripts':{'build':'next build' if valid else 'echo fake'},'dependencies':{'next':'16.3.3'}}))
        archive.writestr('app/layout.tsx','export default function Layout({children}) {return children}')
        archive.writestr('app/page.tsx','export default function Page() {return null}')
    return stream.getvalue()


def consume(db, root, **kwargs):
    args = dict(request_id='child',agent_id='web-agent',principal_id='owner',tenant_id='tenant')
    return consume_staged_web_source(db,root/'stage',root/'source',**dict(args,**kwargs))


def test_real_uploaded_source_consumed_and_reconnect_reuses(tmp_path):
    db = database(tmp_path,bundle())
    first = consume(db,tmp_path)
    assert first['source_consumed'] and first['source_files'] == 3
    assert not first['build_passed'] and not first['coordinator_accepted']
    second = consume(db,tmp_path)
    assert second['reused'] and second['source_path'] == first['source_path']


def test_fake_source_wrong_agent_and_tenant_denied(tmp_path):
    fake = tmp_path/'fake'
    with pytest.raises(PermissionError):
        consume(database(fake,bundle(False)),fake)
    db = database(tmp_path/'valid',bundle())
    for change in ({'agent_id':'other'},{'tenant_id':'other'}):
        with pytest.raises(PermissionError):
            consume(db,tmp_path/'valid',**change)

