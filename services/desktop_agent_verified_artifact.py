"""Verify actual worker artifact bytes without granting coordinator acceptance."""
import base64
import binascii
import hashlib
import hmac

MAX_BYTES = 1024 * 1024


def receive_verified(receipt, *, request_id, agent_id, secret, lease, artifact_b64, digest, now):
    if not isinstance(artifact_b64, str) or len(artifact_b64) > 4 * ((MAX_BYTES + 2) // 3):
        raise ValueError('invalid artifact size')
    try:
        artifact = base64.b64decode(artifact_b64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError('invalid artifact encoding') from exc
    if not artifact or len(artifact) > MAX_BYTES or not isinstance(digest, str):
        raise ValueError('invalid artifact')
    actual = hashlib.sha256(artifact).hexdigest()
    if not hmac.compare_digest(actual, digest):
        raise ValueError('artifact digest mismatch')
    outcome = receipt.submit(request_id=request_id, agent_id=agent_id, secret=secret,
        lease=lease, result={'status': 'completed', 'artifact_sha256': actual}, now=now)
    return outcome, artifact
