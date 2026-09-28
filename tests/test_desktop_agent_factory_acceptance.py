import hashlib
import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from services.desktop_agent_factory_acceptance import inspect_factory_acceptance


def setup(tmp_path):
    db = tmp_path / 'coordinator.sqlite'
    artifact = b'verified factory product'
    digest = hashlib.sha256(artifact).hexdigest()
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE desktop_agent_assignments (request_id TEXT, agent_id TEXT, principal_id TEXT, tenant_id TEXT)')
        conn.execute('CREATE TABLE desktop_agent_result_receipts (request_id TEXT, agent_id TEXT, payload TEXT)')
        conn.execute('CREATE TABLE desktop_agent_artifacts (request_id TEXT, sha256 TEXT, content BLOB)')
        conn.execute('INSERT INTO desktop_agent_assignments VALUES (?,?,?,?)', ('child', 'agent-web', 'owner', 'tenant'))
        conn.execute('INSERT INTO desktop_agent_result_receipts VALUES (?,?,?)',
            ('child', 'agent-web', json.dumps({'status':'completed','artifact_sha256':digest})))
        conn.execute('INSERT INTO desktop_agent_artifacts VALUES (?,?,?)', ('child',digest,artifact))
    coordinator = SimpleNamespace(_database_path=db, get=lambda *a, **k: {'execution_status':'ACCEPTED'})
    plan = {'parent_status':'ADMITTED', 'steps':({'capability_id':'web',
        'child_request_id':'child', 'agent_id':'agent-web'},)}
    return coordinator, plan, digest


def inspect(coordinator, verifiers):
    return inspect_factory_acceptance(coordinator, request_id='parent',
        principal_id='owner', tenant_id='tenant', verifiers=verifiers)


def test_product_verifier_must_attest_exact_worker_digest(tmp_path):
    coordinator, plan, digest = setup(tmp_path)
    def verifier(**kwargs):
        assert kwargs['artifact_sha256'] == digest
        return {'verified':True,'agent_id':'agent-web','artifact_sha256':digest}
    with patch('services.desktop_agent_factory_acceptance.inspect_factory_execution', return_value=plan):
        result = inspect(coordinator, {'web':verifier})
        assert result['verified'] is True
        assert result['parent_coordinator_accepted'] is False
        with pytest.raises(PermissionError):
            inspect(coordinator, {})
        with pytest.raises(PermissionError):
            inspect(coordinator, {'web':lambda **kw: {'verified':True,'agent_id':'agent-web','artifact_sha256':'wrong'}})


def test_receipt_corruption_and_unaccepted_child_fail_closed(tmp_path):
    coordinator, plan, digest = setup(tmp_path)
    verifier = lambda **kw: {'verified':True,'agent_id':'agent-web','artifact_sha256':digest}
    with patch('services.desktop_agent_factory_acceptance.inspect_factory_execution', return_value=plan):
        coordinator.get = lambda *a, **k: {'execution_status':'ADMITTED'}
        with pytest.raises(PermissionError):
            inspect(coordinator, {'web':verifier})
        coordinator.get = lambda *a, **k: {'execution_status':'ACCEPTED'}
        with sqlite3.connect(coordinator._database_path) as conn:
            conn.execute('UPDATE desktop_agent_artifacts SET content=?', (b'corrupt',))
        with pytest.raises(PermissionError):
            inspect(coordinator, {'web':verifier})
