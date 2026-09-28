"""Opt-in worker video runtime integration against canonical product acceptance."""
import base64
import hashlib
import subprocess
from datetime import datetime, timedelta, timezone

import pytest
from services.desktop_agent_assignment_store import record_agent_assignment
from services.desktop_agent_delivery import AgentDelivery
from services.desktop_agent_result_receipt import AgentResultReceipt
from services.desktop_agent_verified_artifact import receive_verified
from services.desktop_agent_video_product_runtime import VerifiedWorkerVideoRuntime
from services.evidence import EvidenceStore
from tests.test_execution_coordinator import _coordinator

NOW = datetime(2026, 8, 15, tzinfo=timezone.utc)


def setup(tmp_path):
    coordinator, governance, _, grants, product = _coordinator(tmp_path)
    request = 'agentexec-worker-video'
    coordinator.prepare(request, 'Create a launch video and final MP4',
        token='token', principal_id='owner', tenant_id='tenant-a', now=NOW)
    record_agent_assignment(coordinator._database_path, request_id=request,
        agent_id='agent-a', principal_id='owner', tenant_id='tenant-a')
    delivery = AgentDelivery(coordinator._database_path, {'agent-a': 'credential-a'})
    lease = delivery.claim(request_id=request, agent_id='agent-a',
        secret='credential-a', now=NOW)
    delivery.acknowledge(request_id=request, agent_id='agent-a',
        secret='credential-a', lease=lease, now=NOW)
    product._video = VerifiedWorkerVideoRuntime(tmp_path / 'worker-video', grants,
        governance, EvidenceStore(tmp_path / 'worker-evidence'),
        coordinator_db=coordinator._database_path, agent_id='agent-a',
        principal_id='owner', tenant_id='tenant-a')
    return coordinator, delivery, lease, request


def upload(delivery, lease, request, content):
    return receive_verified(AgentResultReceipt(delivery), request_id=request,
        agent_id='agent-a', secret='credential-a', lease=lease,
        artifact_b64=base64.b64encode(content).decode(),
        digest=hashlib.sha256(content).hexdigest(), now=NOW)


def test_real_subprocess_video_accepted_by_canonical_product(tmp_path):
    coordinator, delivery, lease, request = setup(tmp_path)
    video = tmp_path / 'worker.mp4'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i',
        'color=c=blue:s=160x284:r=30:d=1', '-f', 'lavfi', '-i',
        'anullsrc=channel_layout=stereo:sample_rate=48000', '-t', '1',
        '-shortest', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', str(video)], check=True, capture_output=True, timeout=30)
    content = video.read_bytes()
    assert content[:8].endswith(b'ftyp')
    upload(delivery, lease, request, content)
    manifest = coordinator.resume(request, token='token', now=NOW + timedelta(seconds=1))
    assert manifest['accepted'] is True
    assert manifest['artifact_digest'] == hashlib.sha256(content).hexdigest()
    assert manifest['qa']['passed'] is True
    assert coordinator.get(request, principal_id='owner', tenant_id='tenant-a')['execution_status'] == 'ACCEPTED'


def test_invalid_worker_video_fails_canonical_product(tmp_path):
    coordinator, delivery, lease, request = setup(tmp_path)
    upload(delivery, lease, request, b'not a playable MP4')
    with pytest.raises(Exception):
        coordinator.resume(request, token='token', now=NOW + timedelta(seconds=1))
    assert coordinator.get(request, principal_id='owner', tenant_id='tenant-a')['execution_status'] != 'ACCEPTED'


def test_disconnected_worker_cannot_be_accepted(tmp_path):
    coordinator, _, _, request = setup(tmp_path)
    with pytest.raises(Exception):
        coordinator.resume(request, token='token', now=NOW + timedelta(seconds=1))
    assert coordinator.get(request, principal_id='owner', tenant_id='tenant-a')['execution_status'] != 'ACCEPTED'
