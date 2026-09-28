"""Separate-process video worker client for authenticated Desktop delivery.

The current server binds loopback only; this client does not claim WAN/TLS support.
The caller supplies an already authorized task ID and server-provisioned identity.
"""
import base64
import hashlib
import subprocess
from pathlib import Path

import requests


class WorkerDeliveryError(RuntimeError):
    pass


def execute_video_delivery(*, endpoint, request_id, agent_id, secret, output_path,
                           ffmpeg='ffmpeg', timeout=20):
    """Claim, acknowledge, render and upload once; never fabricate acceptance."""
    if not endpoint.startswith('http://127.0.0.1:'):
        raise ValueError('only loopback delivery endpoint is currently supported')
    headers = {'Authorization': 'Bearer ' + secret}
    body = {'request_id': request_id, 'agent_id': agent_id}
    claim = requests.post(endpoint + '/claim', json=body, headers=headers, timeout=5)
    claim.raise_for_status()
    body['lease'] = claim.json()['lease']
    ack = requests.post(endpoint + '/ack', json=body, headers=headers, timeout=5)
    ack.raise_for_status()
    output = Path(output_path)
    completed = subprocess.run([ffmpeg, '-y', '-v', 'error', '-f', 'lavfi', '-i',
        'color=c=blue:s=160x284:r=30:d=1', '-f', 'lavfi', '-i',
        'anullsrc=channel_layout=stereo:sample_rate=48000', '-t', '1',
        '-shortest', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', str(output)], capture_output=True, timeout=timeout)
    if completed.returncode != 0:
        raise WorkerDeliveryError('worker video render failed')
    content = output.read_bytes()
    body['artifact_b64'] = base64.b64encode(content).decode('ascii')
    body['digest'] = hashlib.sha256(content).hexdigest()
    try:
        result = requests.post(endpoint + '/artifact', json=body,
                               headers=headers, timeout=10)
    except requests.RequestException as error:
        raise WorkerDeliveryError('upload outcome unknown; do not automatically replay') from error
    result.raise_for_status()
    if result.status_code != 202:
        raise WorkerDeliveryError('unexpected artifact receipt status')
    return {'received': True, 'coordinator_accepted': False,
            'artifact_sha256': body['digest']}
