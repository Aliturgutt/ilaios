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
