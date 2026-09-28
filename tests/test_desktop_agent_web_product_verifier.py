from types import SimpleNamespace
import pytest
from services.desktop_agent_web_product_verifier import verify_web_worker_product
from services.desktop_agent_factory_verifiers import provision_factory_verifiers
from services.execution_coordinator import _WEB

DIGEST = 'a' * 64


def fixture():
    manifest = dict(accepted=True, identity_proven=True, tenant_id='tenant',
        artifact_digest=DIGEST, grant_proven=True, admission_proven=True,
        source_commit_bound=True, source_project_digest='source-digest',
        qa={'passed':True})
    runtime = SimpleNamespace(get_state=lambda rid: dict(requester_id='owner',
        tenant_id='tenant', status='accepted'), get_manifest=lambda rid:manifest)
    coordinator = SimpleNamespace(_adapters={_WEB:SimpleNamespace(_runtime=runtime)})
    args = dict(coordinator=coordinator, request_id='child', agent_id='web-agent',
        principal_id='owner', tenant_id='tenant', artifact_sha256=DIGEST)
    return args, manifest


def test_web_manifest_alone_never_authorizes_worker_result():
    args, manifest = fixture()
    with pytest.raises(PermissionError, match='attestor unavailable'):
        verify_web_worker_product(**args)
    with pytest.raises(PermissionError):
        provision_factory_verifiers(enabled_capabilities=(_WEB,))


def test_web_evidence_and_independent_attestation_must_both_match():
    args, manifest = fixture()
    attestor = lambda **kw: dict(verified=True, agent_id=kw['agent_id'],
                                 artifact_sha256=kw['artifact_sha256'])
    assert verify_web_worker_product(**args, worker_attestor=attestor)['verified'] is True
    for field, bad in [('artifact_digest','b'*64), ('grant_proven',False),
                       ('admission_proven',False), ('source_commit_bound',False),
                       ('qa',{'passed':False}), ('tenant_id','other')]:
        original = manifest[field]
        manifest[field] = bad
        with pytest.raises(PermissionError):
            verify_web_worker_product(**args, worker_attestor=attestor)
        manifest[field] = original
    with pytest.raises(PermissionError):
        verify_web_worker_product(**dict(args, tenant_id='other'), worker_attestor=attestor)
    with pytest.raises(PermissionError):
        verify_web_worker_product(**args, worker_attestor=lambda **kw:
            dict(verified=True, agent_id='wrong-agent', artifact_sha256=DIGEST))
    with pytest.raises(PermissionError):
        verify_web_worker_product(**args, worker_attestor=lambda **kw:
            dict(verified=True, agent_id='web-agent', artifact_sha256='b'*64))
