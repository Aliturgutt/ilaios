from __future__ import annotations

from dataclasses import replace

import pytest

from services.software_factory import ExecutionPolicy, SoftwareFactoryError
from services.web_app_preview_sandbox_observer import (
    PreviewHttpObservation,
    PreviewRuntimeBoundaryObservation,
    observe_generated_preview_sandbox,
)
from services.web_generated_sandbox_gate import SandboxVerdict, evaluate_generated_sandbox
from services.web_app_sandbox_evidence import GeneratedBuildSandboxObservation, produce_generated_sandbox_evidence


def _policy() -> ExecutionPolicy:
    return ExecutionPolicy(allowed_roots=frozenset({"generated-web"}), timeout_seconds=120)


def _runtime() -> PreviewRuntimeBoundaryObservation:
    return PreviewRuntimeBoundaryObservation(
        execution_id="exec-preview-1",
        tenant_id="tenant-a",
        source_sha256="a" * 64,
        artifact_sha256="b" * 64,
        privileged_session_origin="https://app.ilaios.com",
        http=PreviewHttpObservation(
            requested_url="https://preview.example.com",
            final_url="https://preview.example.com",
            request_cookie_header_present=False,
            authorization_header_present=False,
            response_csp="default-src 'none'; script-src 'self'; connect-src api.example.com; object-src 'none'; base-uri 'none'",
        ),
        strong_process_sandbox=True,
        allowed_egress_hosts=("api.example.com",),
        resolved_egress=(("api.example.com", "93.184.216.34"),),
        dns_snapshot_complete=True,
        dns_snapshot_age_seconds=20,
        controlled_egress_gateway=True,
        secret_material_mounted=False,
        host_shell_mounted=False,
        docker_socket_mounted=False,
        control_plane_db_mounted=False,
        unrestricted_filesystem_mounted=False,
        unrestricted_network_enabled=False,
        signing_material_mounted=False,
        wall_clock_timeout_seconds=90,
        memory_limit_mb=768,
        cpu_limit_millis=750,
    )


def _build() -> GeneratedBuildSandboxObservation:
    return GeneratedBuildSandboxObservation(
        execution_id="exec-preview-1", tenant_id="tenant-a", source_sha256="a" * 64,
        artifact_sha256="b" * 64, strong_process_sandbox=True, privileged_cookie_access=False,
        privileged_token_access=False, secret_material_access=False, host_shell_access=False,
        docker_socket_access=False, control_plane_db_access=False, unrestricted_filesystem_access=False,
        unrestricted_network_access=False, signing_material_access=False, package_install_scripts_disabled=True,
        wall_clock_timeout_seconds=120, memory_limit_mb=1024, cpu_limit_millis=1000,
    )


def test_observer_produces_gate_accepted_separate_origin_runtime_evidence() -> None:
    preview = observe_generated_preview_sandbox(runtime=_runtime(), policy=_policy())
    evidence = produce_generated_sandbox_evidence(build=_build(), preview=preview, policy=_policy())
    assert preview.generated_runtime_origin == "https://preview.example.com"
    assert preview.privileged_cookie_access is False
    assert preview.privileged_token_access is False
    assert evaluate_generated_sandbox(evidence).verdict is SandboxVerdict.PASS


def test_observer_rejects_privileged_cookie_or_bearer_authority() -> None:
    for http in (
        replace(_runtime().http, request_cookie_header_present=True),
        replace(_runtime().http, authorization_header_present=True),
    ):
        with pytest.raises(SoftwareFactoryError, match="authority"):
            observe_generated_preview_sandbox(runtime=replace(_runtime(), http=http), policy=_policy())


def test_observer_rejects_same_origin_or_cross_origin_redirect() -> None:
    with pytest.raises(SoftwareFactoryError, match="shares privileged"):
        observe_generated_preview_sandbox(
            runtime=replace(
                _runtime(),
                privileged_session_origin="https://preview.example.com",
            ),
            policy=_policy(),
        )
    with pytest.raises(SoftwareFactoryError, match="redirected outside"):
        observe_generated_preview_sandbox(
            runtime=replace(
                _runtime(),
                http=replace(_runtime().http, final_url="https://evil.example.com"),
            ),
            policy=_policy(),
        )


def test_observer_rejects_missing_csp_and_insecure_policy() -> None:
    with pytest.raises(SoftwareFactoryError, match="CSP"):
        observe_generated_preview_sandbox(
            runtime=replace(_runtime(), http=replace(_runtime().http, response_csp="")),
            policy=_policy(),
        )
    insecure = ExecutionPolicy(
        allowed_roots=frozenset({"generated-web"}),
        timeout_seconds=120,
        secure_mode=False,
        network_allowed=True,
    )
    with pytest.raises(SoftwareFactoryError, match="secure governed policy"):
        observe_generated_preview_sandbox(runtime=_runtime(), policy=insecure)
