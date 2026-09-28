"""Only the original acknowledged worker can renew an expired upload lease."""
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from services.desktop_agent_assignment_store import record_agent_assignment
from services.desktop_agent_delivery import AgentDelivery
from services.desktop_agent_result_receipt import AgentResultReceipt
from tests.test_execution_coordinator import _coordinator

NOW = datetime(2026, 8, 15, tzinfo=timezone.utc)


def setup(tmp_path):
    coordinator, *_ = _coordinator(tmp_path)
    request = 'agentexec-renewal'
    coordinator.prepare(request, 'Create a launch video and final MP4', token='token',
        principal_id='owner', tenant_id='tenant-a', now=NOW)
    record_agent_assignment(coordinator._database_path, request_id=request,
        agent_id='agent-a', principal_id='owner', tenant_id='tenant-a')
    delivery = AgentDelivery(coordinator._database_path,
        {'agent-a':'credential-a', 'agent-b':'credential-b'})
    lease = delivery.claim(request_id=request, agent_id='agent-a',
        secret='credential-a', now=NOW)
    delivery.acknowledge(request_id=request, agent_id='agent-a',
        secret='credential-a', lease=lease, now=NOW)
    return coordinator, delivery, request, lease


def test_renew_expired_original_lease_without_rerunning_task(tmp_path):
    coordinator, delivery, request, lease = setup(tmp_path)
    kwargs = dict(request_id=request, agent_id='agent-a', secret='credential-a', lease=lease)
    with pytest.raises(PermissionError, match='active lease'):
        delivery.renew_acknowledged(**kwargs, now=NOW+timedelta(seconds=5))
    with pytest.raises(PermissionError):
        delivery.renew_acknowledged(**{**kwargs,'agent_id':'agent-b',
            'secret':'credential-b'}, now=NOW+timedelta(seconds=31))
    assert delivery.renew_acknowledged(**kwargs, now=NOW+timedelta(seconds=31)) == lease
    with pytest.raises(PermissionError):
        delivery.claim(request_id=request, agent_id='agent-a',
            secret='credential-a', now=NOW+timedelta(seconds=32))
    artifact = b'persisted upload after reconnect'
    receipt = AgentResultReceipt(delivery)
    receipt.submit(**kwargs, now=NOW+timedelta(seconds=32), artifact=artifact,
        result={'status':'completed','artifact_sha256':hashlib.sha256(artifact).hexdigest()})
    assert delivery.receipt_status(request_id=request, agent_id='agent-a',
        secret='credential-a')['received'] is True
    with pytest.raises(PermissionError, match='received output'):
        delivery.renew_acknowledged(**kwargs, now=NOW+timedelta(seconds=65))
    assert coordinator.get(request, principal_id='owner',
        tenant_id='tenant-a')['execution_status'] == 'ADMITTED'
