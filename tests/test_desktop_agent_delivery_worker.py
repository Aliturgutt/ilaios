from datetime import datetime, timedelta, timezone
import pytest
from services.desktop_agent_delivery import AgentDelivery
from services.desktop_agent_assignment_store import record_agent_assignment
from tests.test_execution_coordinator import _coordinator

NOW = datetime.now(timezone.utc)

def test_wrong_agent_disconnect_reclaim_and_restart(tmp_path):
    coordinator, *_ = _coordinator(tmp_path)
    coordinator.prepare('agentexec-worker', 'Create a launch video and final MP4', token='token', principal_id='owner', tenant_id='tenant-a', now=NOW)
    record_agent_assignment(coordinator._database_path, request_id='agentexec-worker', agent_id='agent-a', principal_id='owner', tenant_id='tenant-a')
    delivery = AgentDelivery(coordinator._database_path, {'agent-a': 'credential-a', 'agent-b': 'credential-b'})
    with pytest.raises(PermissionError):
        delivery.claim(request_id='agentexec-worker', agent_id='agent-b', secret='credential-b', now=NOW)
    lease = delivery.claim(request_id='agentexec-worker', agent_id='agent-a', secret='credential-a', now=NOW)
    with pytest.raises(PermissionError):
        delivery.claim(request_id='agentexec-worker', agent_id='agent-a', secret='credential-a', now=NOW + timedelta(seconds=5))
    restarted = AgentDelivery(coordinator._database_path, {'agent-a': 'credential-a'})
    with pytest.raises(PermissionError):
        restarted.acknowledge(request_id='agentexec-worker', agent_id='agent-a', secret='credential-a', lease=lease, now=NOW + timedelta(seconds=31))
    new_lease = restarted.claim(request_id='agentexec-worker', agent_id='agent-a', secret='credential-a', now=NOW + timedelta(seconds=32))
    assert restarted.acknowledge(request_id='agentexec-worker', agent_id='agent-a', secret='credential-a', lease=new_lease, now=NOW + timedelta(seconds=33))
    with pytest.raises(PermissionError):
        restarted.claim(request_id='agentexec-worker', agent_id='agent-a', secret='credential-a', now=NOW + timedelta(seconds=70))


def test_separate_worker_process_http_delivery(tmp_path):
    from threading import Thread
    import subprocess
    import sys
    import requests
    from services.desktop_agent_delivery_http import AgentDeliveryHTTPServer
    coordinator, *_ = _coordinator(tmp_path)
    coordinator.prepare('agentexec-worker', 'Create a launch video and final MP4', token='token', principal_id='owner', tenant_id='tenant-a', now=NOW)
    record_agent_assignment(coordinator._database_path, request_id='agentexec-worker', agent_id='agent-a', principal_id='owner', tenant_id='tenant-a')
    delivery = AgentDelivery(coordinator._database_path, {'agent-a': 'credential-a', 'agent-b': 'credential-b'})
    http = AgentDeliveryHTTPServer(('127.0.0.1', 0), delivery)
    thread = Thread(target=http.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{http.server_address[1]}/v1/agents/delivery'
    worker_script = '''import requests,sys
base=sys.argv[1]
headers={'Authorization':'Bearer credential-a'}
body={'request_id':'agentexec-worker','agent_id':'agent-a'}
claim=requests.post(base+'/claim',json=body,headers=headers,timeout=3)
assert claim.status_code==200,claim.text
ack=requests.post(base+'/ack',json={**body,'lease':claim.json()['lease']},headers=headers,timeout=3)
assert ack.status_code==204,ack.text
'''
    try:
        denied = requests.post(base+'/claim', json={'request_id':'agentexec-worker','agent_id':'agent-b'}, headers={'Authorization':'Bearer credential-b'}, timeout=3)
        assert denied.status_code == 403
        worker = subprocess.run([sys.executable, '-c', worker_script, base], capture_output=True, text=True, timeout=15)
        assert worker.returncode == 0, worker.stderr
        again = requests.post(base+'/claim', json={'request_id':'agentexec-worker','agent_id':'agent-a'}, headers={'Authorization':'Bearer credential-a'}, timeout=3)
        assert again.status_code == 403
    finally:
        http.shutdown()
        thread.join(timeout=3)
        http.server_close()


def test_cancelled_task_cannot_be_delivered(tmp_path):
    coordinator, *_ = _coordinator(tmp_path)
    coordinator.prepare('agentexec-cancelled', 'Create a launch video and final MP4', token='token', principal_id='owner', tenant_id='tenant-a', now=NOW)
    record_agent_assignment(coordinator._database_path, request_id='agentexec-cancelled', agent_id='agent-a', principal_id='owner', tenant_id='tenant-a')
    coordinator.cancel('agentexec-cancelled', token='token', actor_id='owner', tenant_id='tenant-a', now=NOW)
    delivery = AgentDelivery(coordinator._database_path, {'agent-a': 'credential-a'})
    with pytest.raises(PermissionError):
        delivery.claim(request_id='agentexec-cancelled', agent_id='agent-a', secret='credential-a', now=NOW)


def test_actual_worker_process_termination_requires_expired_lease(tmp_path):
    import subprocess
    import sys
    import time
    coordinator, *_ = _coordinator(tmp_path)
    coordinator.prepare('agentexec-disconnect', 'Create a launch video and final MP4',
        token='token', principal_id='owner', tenant_id='tenant-a', now=NOW)
    record_agent_assignment(coordinator._database_path, request_id='agentexec-disconnect',
        agent_id='agent-a', principal_id='owner', tenant_id='tenant-a')
    delivery = AgentDelivery(coordinator._database_path, {'agent-a': 'credential-a'})
    worker = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
    try:
        lease = delivery.claim(request_id='agentexec-disconnect', agent_id='agent-a',
                               secret='credential-a', now=NOW)
        worker.terminate()
        worker.wait(timeout=5)
        with pytest.raises(PermissionError):
            delivery.claim(request_id='agentexec-disconnect', agent_id='agent-a',
                           secret='credential-a', now=NOW + timedelta(seconds=5))
        replacement = AgentDelivery(coordinator._database_path, {'agent-a': 'credential-a'})
        with pytest.raises(PermissionError):
            replacement.acknowledge(request_id='agentexec-disconnect', agent_id='agent-a',
                secret='credential-a', lease=lease, now=NOW + timedelta(seconds=31))
        new_lease = replacement.claim(request_id='agentexec-disconnect', agent_id='agent-a',
            secret='credential-a', now=NOW + timedelta(seconds=32))
        assert new_lease != lease
    finally:
        if worker.poll() is None:
            worker.kill(); worker.wait(timeout=5)
