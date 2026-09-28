"""Explicit worker-product verifier registry; no generic ACCEPTED shortcut.

Only video currently has a proven worker-byte-to-product acceptance contract.
Other canonical factories stay unavailable until independently implemented.
"""
from services.execution_coordinator import (_VIDEO, _WEB, _APP, _SOFTWARE,
    _RESEARCH, _DOCUMENT, _COMMERCE, _PERSONAL, _SECURITY)

CANONICAL_FACTORY_CAPABILITIES = frozenset((_VIDEO, _WEB, _APP, _SOFTWARE,
    _RESEARCH, _DOCUMENT, _COMMERCE, _PERSONAL, _SECURITY))


def verify_video_worker_product(*, coordinator, request_id, agent_id,
                                principal_id, tenant_id, artifact_sha256):
    from services.desktop_agent_verified_execution_adapter import VerifiedAgentExecutionAdapter
    from services.desktop_agent_video_product_runtime import VerifiedWorkerVideoRuntime
    adapter = coordinator._adapters.get(_VIDEO)
    runtime = getattr(getattr(adapter, '_runtime', None), '_video', None)
    if (not isinstance(runtime, VerifiedWorkerVideoRuntime)
            or runtime._agent_id != agent_id
            or runtime._principal_id != principal_id
            or runtime._tenant_id != tenant_id
            or str(runtime._coordinator_db) != str(coordinator._database_path)):
        raise PermissionError('dedicated owner-bound verified video runtime required')
    evidence = VerifiedAgentExecutionAdapter(coordinator).verify_product_contract(
        request_id=request_id, agent_id=agent_id,
        principal_id=principal_id, tenant_id=tenant_id)
    if evidence.get('artifact_sha256') != artifact_sha256:
        raise PermissionError('video product does not match worker artifact')
    return evidence


def provision_factory_verifiers(*, enabled_capabilities=()):
    """Only explicitly enabled, implemented worker-product contracts are exposed."""
    enabled = frozenset(enabled_capabilities)
    if not enabled <= CANONICAL_FACTORY_CAPABILITIES:
        raise ValueError('noncanonical factory capability')
    implemented = {_VIDEO: verify_video_worker_product}
    if not enabled <= implemented.keys():
        raise PermissionError('factory worker-product verifier not implemented')
    return {capability: implemented[capability] for capability in enabled}
