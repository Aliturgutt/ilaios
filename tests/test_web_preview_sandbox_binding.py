from __future__ import annotations

from dataclasses import replace

import pytest

from services.integrations.web_delivery import WebDeploymentError, WebDeploymentReceipt
from services.integrations.web_preview_sandbox_binding import (
    PreviewIsolationAttestation,
    bind_isolation_attestation_to_receipt,
    bind_preview_sandbox_to_receipt,
    probe_and_bind_preview_sandbox_to_receipt,
)
from services.software_factory import ExecutionPolicy
from services.web_app_preview_runtime_probe import (
    PreviewHttpProbeResult,
    PreviewIsolationBoundaryFacts,
)
from services.web_app_preview_sandbox_observer import (
    PreviewHttpObservation,
    PreviewRuntimeBoundaryObservation,
)


SOURCE_SHA256 = "a" * 64
ARTIFACT_SHA256 = "b" * 64
COMMIT_SHA = "c" * 40
PREVIEW_ORIGIN = "https://preview-123.example.net"


class _Transport:
    def __init__(self, result: PreviewHttpProbeResult) -> None:
        self.result = result
        self.calls: list[tuple[str, int]] = []

    def get(self, url: str, *, timeout_seconds: int) -> PreviewHttpProbeResult:
        self.calls.append((url, timeout_seconds))
        return self.result


def _policy() -> ExecutionPolicy:
    return ExecutionPolicy(allowed_roots=frozenset({"."}), timeout_seconds=90)


def _receipt() -> WebDeploymentReceipt:
    return WebDeploymentReceipt(
        contract="web.deployment-receipt.v1",
        provider="vercel.web-deployment.v1",
        deployment_id="dpl_preview123",
        source_commit_sha=COMMIT_SHA,
        artifact_sha256=ARTIFACT_SHA256,
        live_url=PREVIEW_ORIGIN,
        health="HEALTHY_PUBLIC_PREVIEW",
        rollback_reference=None,
        deployed_at="2026-08-28T18:00:00Z",
        public_production_proven=False,
    )


def _isolation() -> PreviewIsolationBoundaryFacts:
    return PreviewIsolationBoundaryFacts(
        strong_process_sandbox=True,
        allowed_egress_hosts=("api.example.com",),
        resolved_egress=(("api.example.com", "203.0.113.10"),),
        dns_snapshot_complete=True,
        dns_snapshot_age_seconds=3,
        controlled_egress_gateway=True,
        secret_material_mounted=False,
        host_shell_mounted=False,
        docker_socket_mounted=False,
        control_plane_db_mounted=False,
        unrestricted_filesystem_mounted=False,
        unrestricted_network_enabled=False,
        signing_material_mounted=False,
        wall_clock_timeout_seconds=90,
        memory_limit_mb=512,
        cpu_limit_millis=1000,
    )


def _attestation() -> PreviewIsolationAttestation:
    receipt = _receipt()
    return PreviewIsolationAttestation(
        contract="web.preview-isolation-attestation.v1",
        provider=receipt.provider,
        deployment_id=receipt.deployment_id,
        source_commit_sha=receipt.source_commit_sha,
        artifact_sha256=receipt.artifact_sha256,
        preview_origin=receipt.live_url,
        facts=_isolation(),
    )


def _runtime() -> PreviewRuntimeBoundaryObservation:
    return PreviewRuntimeBoundaryObservation(
        execution_id="exec-preview-1",
        tenant_id="tenant-1",
        source_sha256=SOURCE_SHA256,
        artifact_sha256=ARTIFACT_SHA256,
        privileged_session_origin="https://app.ilaios.com",
        http=PreviewHttpObservation(
            requested_url=PREVIEW_ORIGIN,
            final_url=PREVIEW_ORIGIN,
            request_cookie_header_present=False,
            authorization_header_present=False,
            response_csp="default-src 'none'; script-src 'self'; connect-src https://egress.ilaios.com",
        ),
        strong_process_sandbox=True,
        allowed_egress_hosts=("api.example.com",),
        resolved_egress=(("api.example.com", "203.0.113.10"),),
        dns_snapshot_complete=True,
        dns_snapshot_age_seconds=3,
        controlled_egress_gateway=True,
        secret_material_mounted=False,
        host_shell_mounted=False,
        docker_socket_mounted=False,
        control_plane_db_mounted=False,
        unrestricted_filesystem_mounted=False,
        unrestricted_network_enabled=False,
        signing_material_mounted=False,
        wall_clock_timeout_seconds=90,
        memory_limit_mb=512,
        cpu_limit_millis=1000,
    )


def test_binds_exact_preview_receipt_to_trusted_runtime_observation() -> None:
    evidence = bind_preview_sandbox_to_receipt(
        receipt=_receipt(),
        runtime=_runtime(),
        policy=_policy(),
    )
    assert evidence.execution_id == "exec-preview-1"
    assert evidence.tenant_id == "tenant-1"
    assert evidence.artifact_sha256 == ARTIFACT_SHA256
    assert evidence.generated_runtime_origin == PREVIEW_ORIGIN
    assert evidence.separate_origin is True


def test_probe_uses_exact_receipt_url_artifact_and_isolation_lineage() -> None:
    transport = _Transport(
        PreviewHttpProbeResult(
            final_url=PREVIEW_ORIGIN,
            response_headers={
                "Content-Security-Policy": "default-src 'none'; script-src 'self'; object-src 'none'"
            },
        )
    )
    evidence = probe_and_bind_preview_sandbox_to_receipt(
        receipt=_receipt(),
        execution_id="exec-preview-1",
        tenant_id="tenant-1",
        source_sha256=SOURCE_SHA256,
        privileged_session_origin="https://app.ilaios.com",
        isolation_attestation=_attestation(),
        policy=_policy(),
        transport=transport,
        timeout_seconds=9,
    )
    assert transport.calls == [(PREVIEW_ORIGIN, 9)]
    assert evidence.artifact_sha256 == ARTIFACT_SHA256
    assert evidence.generated_runtime_origin == PREVIEW_ORIGIN


def test_probe_rejects_non_preview_receipt_before_network() -> None:
    transport = _Transport(
        PreviewHttpProbeResult(
            final_url=PREVIEW_ORIGIN,
            response_headers={"Content-Security-Policy": "default-src 'none'"},
        )
    )
    receipt = replace(
        _receipt(),
        health="HEALTHY_PUBLIC_PRODUCTION",
        public_production_proven=True,
    )
    with pytest.raises(WebDeploymentError, match="production receipt"):
        probe_and_bind_preview_sandbox_to_receipt(
            receipt=receipt,
            execution_id="exec-preview-1",
            tenant_id="tenant-1",
            source_sha256=SOURCE_SHA256,
            privileged_session_origin="https://app.ilaios.com",
            isolation_attestation=_attestation(),
            policy=_policy(),
            transport=transport,
        )
    assert transport.calls == []


def test_probe_rejects_cross_origin_redirect_after_exact_receipt_probe() -> None:
    transport = _Transport(
        PreviewHttpProbeResult(
            final_url="https://evil.example.net",
            response_headers={"Content-Security-Policy": "default-src 'none'"},
        )
    )
    with pytest.raises(WebDeploymentError, match="URL does not match"):
        probe_and_bind_preview_sandbox_to_receipt(
            receipt=_receipt(),
            execution_id="exec-preview-1",
            tenant_id="tenant-1",
            source_sha256=SOURCE_SHA256,
            privileged_session_origin="https://app.ilaios.com",
            isolation_attestation=_attestation(),
            policy=_policy(),
            transport=transport,
        )


def test_rejects_cross_deployment_isolation_attestation_before_network() -> None:
    transport = _Transport(
        PreviewHttpProbeResult(
            final_url=PREVIEW_ORIGIN,
            response_headers={"Content-Security-Policy": "default-src 'none'"},
        )
    )
    attestation = replace(_attestation(), deployment_id="dpl_other")
    with pytest.raises(WebDeploymentError, match="isolation deployment does not match"):
        probe_and_bind_preview_sandbox_to_receipt(
            receipt=_receipt(),
            execution_id="exec-preview-1",
            tenant_id="tenant-1",
            source_sha256=SOURCE_SHA256,
            privileged_session_origin="https://app.ilaios.com",
            isolation_attestation=attestation,
            policy=_policy(),
            transport=transport,
        )
    assert transport.calls == []


def test_rejects_cross_lineage_isolation_attestations() -> None:
    cases = (
        (
            replace(_attestation(), provider="other.provider"),
            "isolation provider does not match",
        ),
        (
            replace(_attestation(), source_commit_sha="d" * 40),
            "isolation source commit does not match",
        ),
        (
            replace(_attestation(), artifact_sha256="d" * 64),
            "isolation artifact does not match",
        ),
        (
            replace(_attestation(), preview_origin="https://other-preview.example.net"),
            "isolation origin does not match",
        ),
    )
    for attestation, message in cases:
        with pytest.raises(WebDeploymentError, match=message):
            bind_isolation_attestation_to_receipt(receipt=_receipt(), attestation=attestation)


def test_rejects_noncanonical_isolation_attestation_contract() -> None:
    attestation = replace(_attestation(), contract="web.preview-isolation-attestation.v2")
    with pytest.raises(WebDeploymentError, match="attestation contract"):
        bind_isolation_attestation_to_receipt(receipt=_receipt(), attestation=attestation)


def test_rejects_cross_artifact_preview_evidence_reuse() -> None:
    receipt = replace(_receipt(), artifact_sha256="d" * 64)
    with pytest.raises(WebDeploymentError, match="artifact does not match"):
        bind_preview_sandbox_to_receipt(receipt=receipt, runtime=_runtime(), policy=_policy())


def test_rejects_cross_origin_preview_evidence_reuse() -> None:
    receipt = replace(_receipt(), live_url="https://another-preview.example.net")
    with pytest.raises(WebDeploymentError, match="URL does not match"):
        bind_preview_sandbox_to_receipt(receipt=receipt, runtime=_runtime(), policy=_policy())


def test_rejects_production_receipt_as_preview_authority() -> None:
    receipt = replace(
        _receipt(),
        health="HEALTHY_PUBLIC_PRODUCTION",
        public_production_proven=True,
    )
    with pytest.raises(WebDeploymentError, match="production receipt"):
        bind_preview_sandbox_to_receipt(receipt=receipt, runtime=_runtime(), policy=_policy())


def test_rejects_malformed_source_commit_lineage() -> None:
    receipt = replace(_receipt(), source_commit_sha="not-a-commit")
    with pytest.raises(WebDeploymentError, match="source commit SHA"):
        bind_preview_sandbox_to_receipt(receipt=receipt, runtime=_runtime(), policy=_policy())
