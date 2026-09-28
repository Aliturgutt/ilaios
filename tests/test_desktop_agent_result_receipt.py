from datetime import datetime, timedelta, timezone
import hashlib
import pytest
from services.desktop_agent_assignment_store import record_agent_assignment
from services.desktop_agent_delivery import AgentDelivery
from services.desktop_agent_result_receipt import AgentResultReceipt
from tests.test_execution_coordinator import _coordinator

NOW = datetime(2026, 8, 15, tzinfo=timezone.utc)
RESULT = {'status': 'completed', 'artifact_sha256': hashlib.sha256(b'worker artifact').hexdigest()}


def prepared(tmp_path):
    coordinator, *_ = _coordinator(tmp_path)
    coordinator.prepare('agentexec-result', 'Create a launch video and final MP4', token='token', principal_id='owner', tenant_id='tenant-a', now=NOW)
    record_agent_assignment(coordinator._database_path, request_id='agentexec-result', agent_id='agent-a', principal_id='owner', tenant_id='tenant-a')
    delivery = AgentDelivery(coordinator._database_path, {'agent-a': 'credential-a', 'agent-b': 'credential-b'})
    lease = delivery.claim(request_id='agentexec-result', agent_id='agent-a', secret='credential-a', now=NOW)
    delivery.acknowledge(request_id='agentexec-result', agent_id='agent-a', secret='credential-a', lease=lease, now=NOW)
    return coordinator, delivery, lease


def test_verified_result_is_durable_but_does_not_claim_coordinator_acceptance(tmp_path):
    import sqlite3
    coordinator, delivery, lease = prepared(tmp_path)
    receipt = AgentResultReceipt(delivery)
    with pytest.raises(PermissionError):
        receipt.submit(request_id='agentexec-result', agent_id='agent-b', secret='credential-b', lease=lease, result=RESULT, now=NOW)
    with pytest.raises(PermissionError):
        receipt.submit(request_id='agentexec-result', agent_id='agent-a', secret='credential-a', lease='forged', result=RESULT, now=NOW)
    response = receipt.submit(request_id='agentexec-result', agent_id='agent-a', secret='credential-a', lease=lease, result=RESULT, now=NOW)
    assert response == {'received': True, 'coordinator_accepted': False}
    with pytest.raises(PermissionError):
        AgentResultReceipt(AgentDelivery(coordinator._database_path, {'agent-a': 'credential-a'})).submit(request_id='agentexec-result', agent_id='agent-a', secret='credential-a', lease=lease, result=RESULT, now=NOW)
    with sqlite3.connect(coordinator._database_path) as conn:
        assert conn.execute('SELECT agent_id FROM desktop_agent_result_receipts').fetchone() == ('agent-a',)
    assert coordinator.get('agentexec-result', principal_id='owner', tenant_id='tenant-a')['execution_status'] == 'ADMITTED'


def test_expired_or_malformed_result_is_rejected(tmp_path):
    coordinator, delivery, lease = prepared(tmp_path)
    receipt = AgentResultReceipt(delivery)
    with pytest.raises(PermissionError):
        receipt.submit(request_id='agentexec-result', agent_id='agent-a', secret='credential-a', lease=lease, result=RESULT, now=NOW + timedelta(seconds=31))
    with pytest.raises(ValueError):
        receipt.submit(request_id='agentexec-result', agent_id='agent-a', secret='credential-a', lease=lease, result={'status':'completed','artifact_sha256':'unverified'}, now=NOW)


def test_separate_worker_process_submits_computed_digest_over_http(tmp_path):
    from threading import Thread
    import subprocess
    import sys
    import requests
    import sqlite3
    from services.desktop_agent_delivery_http import AgentDeliveryHTTPServer
    coordinator, delivery, _ = prepared(tmp_path)
    # Use a fresh task because the fixture above already acknowledged its lease.
    http = AgentDeliveryHTTPServer(('127.0.0.1', 0), delivery)
    thread = Thread(target=http.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{http.server_address[1]}/v1/agents/delivery'
    script = '''import requests,sys,hashlib
base,lease=sys.argv[1:]
headers={'Authorization':'Bearer credential-a'}
result={'status':'completed','artifact_sha256':hashlib.sha256(b'worker artifact').hexdigest()}
response=requests.post(base+'/result',json={'request_id':'agentexec-result','agent_id':'agent-a','lease':lease,'result':result},headers=headers,timeout=3)
assert response.status_code==202,response.text
'''
    # The delivery lease itself is intentionally never stored in plaintext.
    # For this test issue a new claim on a separate prepared request.
    coordinator.prepare('agentexec-http-result', 'Create a launch video and final MP4', token='token', principal_id='owner', tenant_id='tenant-a', now=datetime.now(timezone.utc))
    record_agent_assignment(coordinator._database_path, request_id='agentexec-http-result', agent_id='agent-a', principal_id='owner', tenant_id='tenant-a')
    fresh = datetime.now(timezone.utc)
    lease = delivery.claim(request_id='agentexec-http-result', agent_id='agent-a', secret='credential-a', now=fresh)
    delivery.acknowledge(request_id='agentexec-http-result', agent_id='agent-a', secret='credential-a', lease=lease, now=fresh)
    script = script.replace('agentexec-result', 'agentexec-http-result')
    try:
        worker = subprocess.run([sys.executable, '-c', script, base, lease], capture_output=True, text=True, timeout=15)
        assert worker.returncode == 0, worker.stderr
        with sqlite3.connect(coordinator._database_path) as conn:
            assert conn.execute('SELECT agent_id FROM desktop_agent_result_receipts WHERE request_id=?', ('agentexec-http-result',)).fetchone() == ('agent-a',)
        assert coordinator.get('agentexec-http-result', principal_id='owner', tenant_id='tenant-a')['execution_status'] == 'ADMITTED'
    finally:
        http.shutdown(); thread.join(timeout=3); http.server_close()
