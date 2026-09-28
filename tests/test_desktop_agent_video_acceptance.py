"""Owner-triggered worker video acceptance cannot bypass canonical product QA."""
import hashlib
import subprocess
from datetime import timedelta

import pytest
from services.desktop_agent_video_acceptance import accept_uploaded_worker_video
from tests.test_desktop_agent_worker_video_product import NOW, setup, upload


def accept(coordinator, request, agent='agent-a', owner='owner'):
    return accept_uploaded_worker_video(coordinator, request_id=request,
        agent_id=agent, principal_id=owner, tenant_id='tenant-a',
        token='token', now=NOW+timedelta(seconds=1))


def test_bound_worker_video_owner_acceptance(tmp_path):
    coordinator, delivery, lease, request = setup(tmp_path)
    output = tmp_path/'agent-produced.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i',
        'color=c=blue:s=160x284:r=30:d=1','-f','lavfi','-i',
        'anullsrc=channel_layout=stereo:sample_rate=48000','-t','1',
        '-shortest','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',
        str(output)], check=True, capture_output=True, timeout=30)
    content = output.read_bytes()
    upload(delivery, lease, request, content)
    with pytest.raises(PermissionError):
        accept(coordinator, request, agent='agent-b')
    with pytest.raises(Exception):
        accept(coordinator, request, owner='other')
    accepted = accept(coordinator, request)
    assert accepted == {'accepted':True,'agent_id':'agent-a',
                        'artifact_sha256':hashlib.sha256(content).hexdigest()}
    with pytest.raises(PermissionError):
        accept(coordinator, request)


def test_missing_worker_upload_does_not_resume(tmp_path):
    coordinator, _, _, request = setup(tmp_path)
    with pytest.raises(PermissionError, match='no bound worker result'):
        accept(coordinator, request)
    assert coordinator.get(request, principal_id='owner',
        tenant_id='tenant-a')['execution_status']=='ADMITTED'
