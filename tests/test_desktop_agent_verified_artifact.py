import base64
import hashlib
import pytest
from services.desktop_agent_result_receipt import AgentResultReceipt
from services.desktop_agent_verified_artifact import receive_verified
from tests.test_desktop_agent_result_receipt import prepared, NOW


def test_real_bytes_verified_and_coordinator_remains_unaccepted(tmp_path):
    coordinator, delivery, lease = prepared(tmp_path)
    content = b'actual worker output bytes'
    digest = hashlib.sha256(content).hexdigest()
    kwargs = dict(request_id='agentexec-result', agent_id='agent-a', secret='credential-a',
                  lease=lease, artifact_b64=base64.b64encode(content).decode(), digest=digest, now=NOW)
    with pytest.raises(ValueError):
        receive_verified(AgentResultReceipt(delivery), **{**kwargs, 'digest': '0'*64})
    assert coordinator.get('agentexec-result', principal_id='owner', tenant_id='tenant-a')['execution_status'] == 'ADMITTED'
    outcome, actual = receive_verified(AgentResultReceipt(delivery), **kwargs)
    assert actual == content
    assert outcome['coordinator_accepted'] is False
    with pytest.raises(PermissionError):
        receive_verified(AgentResultReceipt(delivery), **kwargs)
    assert coordinator.get('agentexec-result', principal_id='owner', tenant_id='tenant-a')['execution_status'] == 'ADMITTED'


def test_wrong_agent_cannot_submit_verified_bytes(tmp_path):
    _, delivery, lease = prepared(tmp_path)
    content = b'actual worker output bytes'
    with pytest.raises(PermissionError):
        receive_verified(AgentResultReceipt(delivery), request_id='agentexec-result',
            agent_id='agent-b', secret='credential-b', lease=lease,
            artifact_b64=base64.b64encode(content).decode(),
            digest=hashlib.sha256(content).hexdigest(), now=NOW)


def test_artifact_persists_after_coordinator_reopen_and_reconcile_fails_closed(tmp_path):
    import sqlite3
    from tests.test_execution_coordinator import _coordinator
    from services.desktop_agent_coordinator_result_bridge import reconcile_verified_result
    coordinator, delivery, lease = prepared(tmp_path)
    content = b'actual worker output bytes'
    digest = hashlib.sha256(content).hexdigest()
    receive_verified(AgentResultReceipt(delivery), request_id='agentexec-result',
        agent_id='agent-a', secret='credential-a', lease=lease,
        artifact_b64=base64.b64encode(content).decode(), digest=digest, now=NOW)
    reopened, *_ = _coordinator(tmp_path)
    with sqlite3.connect(reopened._database_path) as conn:
        saved = conn.execute('SELECT sha256,content FROM desktop_agent_artifacts WHERE request_id=?',
                             ('agentexec-result',)).fetchone()
    assert saved == (digest, content)
    assert reconcile_verified_result(reopened, request_id='agentexec-result',
        principal_id='owner', tenant_id='tenant-a') == {
            'verified': False, 'reason': 'coordinator_not_accepted'}
    with pytest.raises(Exception):
        reconcile_verified_result(reopened, request_id='agentexec-result',
            principal_id='intruder', tenant_id='tenant-b')


def test_independent_coordinator_acceptance_does_not_launder_worker_digest(tmp_path):
    from datetime import timedelta
    from services.desktop_agent_coordinator_result_bridge import reconcile_verified_result
    coordinator, delivery, lease = prepared(tmp_path)
    content = b'unrelated worker bytes'
    receive_verified(AgentResultReceipt(delivery), request_id='agentexec-result',
        agent_id='agent-a', secret='credential-a', lease=lease,
        artifact_b64=base64.b64encode(content).decode(),
        digest=hashlib.sha256(content).hexdigest(), now=NOW)
    manifest = coordinator.resume('agentexec-result', token='token', now=NOW + timedelta(seconds=1))
    assert manifest['accepted'] is True
    assert manifest['artifact_digest'] != hashlib.sha256(content).hexdigest()
    assert reconcile_verified_result(coordinator, request_id='agentexec-result',
        principal_id='owner', tenant_id='tenant-a') == {
            'verified': False, 'reason': 'coordinator_evidence_mismatch'}


def test_verified_worker_result_requires_product_adapter_before_acceptance(tmp_path):
    from services.desktop_agent_coordinator_result_bridge import inspect_worker_acceptance_readiness
    coordinator, delivery, lease = prepared(tmp_path)
    content = b'worker result with no product-specific acceptance evidence'
    receive_verified(AgentResultReceipt(delivery), request_id='agentexec-result',
        agent_id='agent-a', secret='credential-a', lease=lease,
        artifact_b64=base64.b64encode(content).decode(),
        digest=hashlib.sha256(content).hexdigest(), now=NOW)
    readiness = inspect_worker_acceptance_readiness(coordinator, request_id='agentexec-result',
        principal_id='owner', tenant_id='tenant-a')
    assert readiness['ready'] and readiness['requires_verified_execution_adapter']
    assert readiness['coordinator_accepted'] is False
    assert coordinator.get('agentexec-result', principal_id='owner', tenant_id='tenant-a')['execution_status'] == 'ADMITTED'
    with pytest.raises(Exception):
        inspect_worker_acceptance_readiness(coordinator, request_id='agentexec-result',
            principal_id='intruder', tenant_id='tenant-b')


def test_verified_adapter_binds_agent_and_governance_without_false_acceptance(tmp_path):
    from services.desktop_agent_verified_execution_adapter import VerifiedAgentExecutionAdapter
    coordinator, delivery, lease = prepared(tmp_path)
    content = b'agent-generated content'
    receive_verified(AgentResultReceipt(delivery), request_id='agentexec-result',
        agent_id='agent-a', secret='credential-a', lease=lease,
        artifact_b64=base64.b64encode(content).decode(),
        digest=hashlib.sha256(content).hexdigest(), now=NOW)
    adapter = VerifiedAgentExecutionAdapter(coordinator)
    evidence = adapter.verify(request_id='agentexec-result', agent_id='agent-a',
        principal_id='owner', tenant_id='tenant-a')
    assert evidence['verified'] and evidence['product_acceptance_required']
    assert evidence['coordinator_accepted'] is False
    with pytest.raises(PermissionError):
        adapter.verify(request_id='agentexec-result', agent_id='agent-b',
            principal_id='owner', tenant_id='tenant-a')
    with pytest.raises(Exception):
        adapter.verify(request_id='agentexec-result', agent_id='agent-a',
            principal_id='other', tenant_id='tenant-b')
