"""Real worker subprocess, loopback transport and canonical video acceptance."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from threading import Thread

import pytest
from services.desktop_agent_assignment_store import record_agent_assignment
from services.desktop_agent_delivery import AgentDelivery
from services.desktop_agent_delivery_http import AgentDeliveryHTTPServer
from services.desktop_agent_video_product_runtime import VerifiedWorkerVideoRuntime
from services.evidence import EvidenceStore
from tests.test_execution_coordinator import _coordinator


def prepared(tmp_path):
    coordinator, governance, _, grants, product = _coordinator(tmp_path)
    request = 'agentexec-real-worker-http'
    coordinator.prepare(request, 'Create a launch video and final MP4',
        token='token', principal_id='owner', tenant_id='tenant-a',
        now=datetime.now(timezone.utc))
    record_agent_assignment(coordinator._database_path, request_id=request,
        agent_id='agent-a', principal_id='owner', tenant_id='tenant-a')
    product._video = VerifiedWorkerVideoRuntime(tmp_path / 'worker-video', grants,
        governance, EvidenceStore(tmp_path / 'worker-evidence'),
        coordinator_db=coordinator._database_path, agent_id='agent-a',
        principal_id='owner', tenant_id='tenant-a')
    delivery = AgentDelivery(coordinator._database_path, {'agent-a': 'credential-a'})
    server = AgentDeliveryHTTPServer(('127.0.0.1', 0), delivery)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return coordinator, request, server, thread


def worker_script(endpoint, request, output, ffmpeg='ffmpeg'):
    script = ('import json,sys\n'
        'from services.desktop_agent_video_worker_client import execute_video_delivery\n'
        'print(json.dumps(execute_video_delivery(endpoint=sys.argv[1],'
        'request_id=sys.argv[2],agent_id="agent-a",secret="credential-a",'
        'output_path=sys.argv[3],ffmpeg=sys.argv[4])))')
    return subprocess.run([sys.executable, '-c', script, endpoint, request,
                           str(output), ffmpeg], capture_output=True, text=True,
                          timeout=35)


def test_worker_process_http_video_is_canonically_accepted(tmp_path):
    coordinator, request, server, thread = prepared(tmp_path)
    try:
        endpoint = f'http://127.0.0.1:{server.server_address[1]}/v1/agents/delivery'
        worker = worker_script(endpoint, request, tmp_path / 'worker.mp4')
        assert worker.returncode == 0, worker.stderr
        receipt = json.loads(worker.stdout)
        assert receipt['received'] and not receipt['coordinator_accepted']
        manifest = coordinator.resume(request, token='token',
                                      now=datetime.now(timezone.utc))
        assert manifest['accepted'] and manifest['artifact_digest'] == receipt['artifact_sha256']
    finally:
        server.shutdown(); thread.join(timeout=3); server.server_close()


def test_worker_render_failure_cannot_be_accepted(tmp_path):
    coordinator, request, server, thread = prepared(tmp_path)
    try:
        endpoint = f'http://127.0.0.1:{server.server_address[1]}/v1/agents/delivery'
        worker = worker_script(endpoint, request, tmp_path / 'failed.mp4',
                               ffmpeg='nonexistent-ffmpeg-executable')
        assert worker.returncode != 0
        with pytest.raises(Exception):
            coordinator.resume(request, token='token', now=datetime.now(timezone.utc))
        assert coordinator.get(request, principal_id='owner',
            tenant_id='tenant-a')['execution_status'] != 'ACCEPTED'
    finally:
        server.shutdown(); thread.join(timeout=3); server.server_close()


def test_connection_loss_after_ack_prevents_acceptance(tmp_path):
    import time
    coordinator, request, server, thread = prepared(tmp_path)
    endpoint = f'http://127.0.0.1:{server.server_address[1]}/v1/agents/delivery'
    # A distinct worker process claims and acknowledges before the server drops.
    script = '''import requests,sys
base=sys.argv[1]; rid=sys.argv[2]
h={'Authorization':'Bearer credential-a'}
p={'request_id':rid,'agent_id':'agent-a'}
r=requests.post(base+'/claim',json=p,headers=h,timeout=3);r.raise_for_status()
p['lease']=r.json()['lease']
r=requests.post(base+'/ack',json=p,headers=h,timeout=3);r.raise_for_status()
print('ACKNOWLEDGED',flush=True)
sys.stdin.readline()
try:
    requests.post(base+'/artifact',json={'request_id':rid},headers=h,timeout=1)
except requests.RequestException:
    print('DISCONNECTED',flush=True)
'''
    worker = subprocess.Popen([sys.executable, '-c', script, endpoint, request],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True)
    try:
        assert worker.stdout.readline().strip() == 'ACKNOWLEDGED'
        server.shutdown(); thread.join(timeout=3); server.server_close()
        worker.stdin.write('continue\n'); worker.stdin.flush()
        output, errors = worker.communicate(timeout=5)
        assert 'DISCONNECTED' in output, errors
        assert worker.returncode == 0
        with pytest.raises(Exception):
            coordinator.resume(request, token='token', now=datetime.now(timezone.utc))
        assert coordinator.get(request, principal_id='owner',
            tenant_id='tenant-a')['execution_status'] != 'ACCEPTED'
    finally:
        if worker.poll() is None:
            worker.kill(); worker.wait(timeout=5)
        server.server_close()


def test_reconnection_status_is_read_only_and_owner_bound(tmp_path):
    import requests
    coordinator, request, server, thread = prepared(tmp_path)
    endpoint = f'http://127.0.0.1:{server.server_address[1]}/v1/agents/delivery'
    headers = {'Authorization':'Bearer credential-a'}
    payload = {'request_id':request, 'agent_id':'agent-a'}
    try:
        before = requests.post(endpoint+'/status', json=payload, headers=headers, timeout=3)
        assert before.status_code == 200 and before.json()['received'] is False
        assert requests.post(endpoint+'/status', json=payload,
            headers={'Authorization':'Bearer invalid'}, timeout=3).status_code == 403
        worker = worker_script(endpoint, request, tmp_path/'reconnect.mp4')
        assert worker.returncode == 0, worker.stderr
        after = requests.post(endpoint+'/status', json=payload, headers=headers, timeout=3)
        assert after.status_code == 200 and after.json() == {
            'received':True, 'coordinator_accepted':False}
        assert requests.post(endpoint+'/claim', json=payload,
            headers=headers, timeout=3).status_code == 403
    finally:
        server.shutdown(); thread.join(timeout=3); server.server_close()
