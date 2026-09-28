"""Explicit, owner-authorized acceptance of a bound remote video worker result.

Requires a dedicated coordinator whose video product runtime is configured with
VerifiedWorkerVideoRuntime. Never swaps adapters on a shared coordinator.
"""
from services.desktop_agent_verified_execution_adapter import VerifiedAgentExecutionAdapter
from services.desktop_agent_video_product_runtime import VerifiedWorkerVideoRuntime


def accept_uploaded_worker_video(coordinator, *, request_id, agent_id,
                                 principal_id, tenant_id, token, now):
    verifier = VerifiedAgentExecutionAdapter(coordinator)
    before = verifier.verify(request_id=request_id, agent_id=agent_id,
                             principal_id=principal_id, tenant_id=tenant_id)
    from services.execution_coordinator import _VIDEO
    video_adapter = coordinator._adapters.get(_VIDEO)
    runtime = getattr(getattr(video_adapter, '_runtime', None), '_video', None)
    if not isinstance(runtime, VerifiedWorkerVideoRuntime):
        raise PermissionError('dedicated verified worker video adapter required')
    if (runtime._agent_id != agent_id or runtime._principal_id != principal_id
            or runtime._tenant_id != tenant_id
            or str(runtime._coordinator_db) != str(coordinator._database_path)):
        raise PermissionError('video adapter bound to another worker or owner')
    manifest = coordinator.resume(request_id, token=token, now=now)
    evidence = verifier.verify_product_contract(request_id=request_id,
        agent_id=agent_id, principal_id=principal_id, tenant_id=tenant_id)
    if manifest.get('accepted') is not True or manifest.get('artifact_digest') != before['artifact_sha256'] \
            or evidence['artifact_sha256'] != before['artifact_sha256']:
        raise PermissionError('product acceptance and worker artifact mismatch')
    return {'accepted': True, 'agent_id': agent_id,
            'artifact_sha256': evidence['artifact_sha256']}
