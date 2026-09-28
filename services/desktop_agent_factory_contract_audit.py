"""Conservative audit of nine factory worker acceptance contracts.

Local product runtimes are not proof that uploaded worker bytes were consumed.
No factory is enabled here merely because a local runtime exists.
"""
from dataclasses import dataclass
from services.execution_coordinator import (_VIDEO, _WEB, _APP, _SOFTWARE,
    _RESEARCH, _DOCUMENT, _COMMERCE, _PERSONAL, _SECURITY)
from services.desktop_agent_factory_verifiers import CANONICAL_FACTORY_CAPABILITIES


@dataclass(frozen=True)
class FactoryContract:
    capability_id: str
    local_runtime: str | None
    worker_product_verifier: str | None
    missing_proof: str


FACTORY_CONTRACTS = (
    FactoryContract(_VIDEO, 'VerifiedWorkerVideoRuntime',
        'verify_video_worker_product (dedicated owner-bound runtime)',
        'production sidecar per-owner runtime binding and end-to-end Windows evidence'),
    FactoryContract(_WEB, 'DurableWebProductRuntime / RecoverableWebProductRuntime', None,
        'worker-uploaded bundle digest bound to web QA, source project and grant'),
    FactoryContract(_APP, 'DurableAppProductRuntime', None,
        'worker executable digest bound to build, runtime evidence, signing and grant'),
    FactoryContract(_SOFTWARE, 'DurableSoftwareProductRuntime / RecoverableSoftwareProductRuntime', None,
        'worker artifact digest bound to tested source, evidence store and grant'),
    FactoryContract(_DOCUMENT, 'DocumentProductRuntime', None,
        'worker bundle manifest binding all five governed outputs and tenant/job'),
    FactoryContract(_RESEARCH, None, None,
        'discover governed runtime, research provenance and worker evidence contract'),
    FactoryContract(_COMMERCE, None, None,
        'discover governed runtime, external side-effect policy and worker evidence'),
    FactoryContract(_PERSONAL, None, None,
        'discover governed runtime, personal-data consent and worker evidence'),
    FactoryContract(_SECURITY, None, None,
        'discover governed runtime, sandboxed security checks and worker evidence'),
)


def audit_factory_contracts():
    capabilities = tuple(contract.capability_id for contract in FACTORY_CONTRACTS)
    if len(capabilities) != 9 or set(capabilities) != CANONICAL_FACTORY_CAPABILITIES:
        raise RuntimeError('canonical factory audit incomplete')
    return FACTORY_CONTRACTS
