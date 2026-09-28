"""Web worker acceptance evidence gate; no generic local-runtime promotion.

Requires a dedicated, server-provisioned worker-consumption attestor. An
ordinary Web manifest is insufficient even when its digest happens to match.
"""
import hashlib


def verify_web_worker_product(*, coordinator, request_id, agent_id,
                              principal_id, tenant_id, artifact_sha256,
                              worker_attestor=None):
    from services.execution_coordinator import _WEB
    if (not isinstance(artifact_sha256, str) or len(artifact_sha256) != 64
            or any(c not in '0123456789abcdef' for c in artifact_sha256)):
        raise PermissionError('invalid worker artifact digest')
    adapter = coordinator._adapters.get(_WEB)
    runtime = getattr(adapter, '_runtime', None)
    if runtime is None or not callable(getattr(runtime, 'get_manifest', None)):
        raise PermissionError('canonical Web product runtime unavailable')
    state = runtime.get_state(request_id)
    if (state.get('requester_id') != principal_id
            or state.get('tenant_id') != tenant_id or state.get('status') != 'accepted'):
        raise PermissionError('Web product owner or acceptance mismatch')
    manifest = runtime.get_manifest(request_id)
    if (manifest.get('accepted') is not True or manifest.get('identity_proven') is not True
            or manifest.get('tenant_id') != tenant_id
            or manifest.get('artifact_digest') != artifact_sha256
            or manifest.get('grant_proven') is not True
            or manifest.get('admission_proven') is not True
            or manifest.get('source_commit_bound') is not True
            or not isinstance(manifest.get('qa'), dict)
            or manifest['qa'].get('passed') is not True
            or not manifest.get('source_project_digest')):
        raise PermissionError('Web product evidence does not match worker artifact')
    # This must be an independently provisioned implementation proving that
    # these exact uploaded worker bytes were consumed by the canonical runtime.
    if worker_attestor is None or not callable(worker_attestor):
        raise PermissionError('verified Web worker-consumption attestor unavailable')
    evidence = worker_attestor(coordinator=coordinator, request_id=request_id,
        agent_id=agent_id, principal_id=principal_id, tenant_id=tenant_id,
        artifact_sha256=artifact_sha256)
    if (not isinstance(evidence, dict) or evidence.get('verified') is not True
            or evidence.get('agent_id') != agent_id
            or evidence.get('artifact_sha256') != artifact_sha256):
        raise PermissionError('Web worker-consumption attestation rejected')
    return {'verified': True, 'agent_id': agent_id,
            'artifact_sha256': artifact_sha256}
