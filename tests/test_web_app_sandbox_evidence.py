from __future__ import annotations

from dataclasses import replace

import pytest

from services.runtime.generated_app_docker_boundary import DockerSecureCommandBoundary
from services.software_factory import ExecutionPolicy, SoftwareFactoryError
from services.software_factory_runtime import RuntimeEvidence, RuntimeStepResult
from services.web_app_build_sandbox_observer import observe_docker_build_sandbox
from services.web_app_sandbox_evidence import (
    GeneratedBuildSandboxObservation,
    GeneratedPreviewSandboxObservation,
    produce_generated_sandbox_evidence,
)
from services.web_generated_sandbox_gate import SandboxVerdict, evaluate_generated_sandbox


def _policy() -> ExecutionPolicy:
    return ExecutionPolicy(allowed_roots=frozenset({"generated-web"}), timeout_seconds=120)


def _build() -> GeneratedBuildSandboxObservation:
    return GeneratedBuildSandboxObservation(
        execution_id="exec-web-1",
        tenant_id="tenant-a",
        source_sha256="a" * 64,
        artifact_sha256="b" * 64,
        strong_process_sandbox=True,
        privileged_cookie_access=False,
        privileged_token_access=False,
        secret_material_access=False,
        host_shell_access=False,
        docker_socket_access=False,
        control_plane_db_access=False,
        unrestricted_filesystem_access=False,
        unrestricted_network_access=False,
        signing_material_access=False,
        package_install_scripts_disabled=True,
        wall_clock_timeout_seconds=120,
        memory_limit_mb=1024,
        cpu_limit_millis=1000,
    )


def _preview() -> GeneratedPreviewSandboxObservation:
    return GeneratedPreviewSandboxObservation(
        execution_id="exec-web-1",
        tenant_id="tenant-a",
        source_sha256="a" * 64,
        artifact_sha256="b" * 64,
        separate_origin=True,
        generated_runtime_origin="https://preview.example.com",
        privileged_session_origin="https://app.example.com",
        csp=(
            "default-src 'none'; script-src 'self'; connect-src api.example.com; "
            "object-src 'none'; base-uri 'none'"
        ),
        allowed_egress_hosts=("api.example.com",),
        resolved_egress=(("api.example.com", "93.184.216.34"),),
        dns_snapshot_complete=True,
        dns_snapshot_age_seconds=30,
        controlled_egress_gateway=True,
    )


def _runtime_evidence(*, dependency: tuple[str, ...] | None = None) -> RuntimeEvidence:
    dependency_command = dependency or (
        "pnpm",
        "install",
        "--offline",
        "--frozen-lockfile",
        "--ignore-scripts",
    )

    def step(stage: str, command: tuple[str, ...]) -> RuntimeStepResult:
        return RuntimeStepResult(stage, command, 0, "1" * 64, "2" * 64, True)

    return RuntimeEvidence(
        adapter_id="ilaios.runtime.node",
        workspace_sha256="a" * 64,
        steps=(
            step("prepare", ("pnpm", "--version")),
            step("resolve_dependencies", dependency_command),
            step("lint", ("pnpm", "run", "lint")),
            step("typecheck", ("pnpm", "run", "typecheck")),
            step("test", ("pnpm", "run", "test:site")),
            step("build", ("pnpm", "run", "build")),
            step("package", ("pnpm", "pack", "--dry-run")),
            step("smoke_test", ("pnpm", "run", "test:site")),
        ),
        passed=True,
    )


def test_producer_binds_runtime_preview_and_canonical_policy() -> None:
    evidence = produce_generated_sandbox_evidence(
        build=_build(), preview=_preview(), policy=_policy()
    )
    assert evidence.execution_id == "exec-web-1"
    assert evidence.tenant_id == "tenant-a"
    assert evidence.canonical_policy_secure_mode is True
    assert evidence.canonical_policy_network_allowed is False
    assert evidence.canonical_policy_secrets_allowed is False
    assert evidence.canonical_policy_timeout_seconds == 120
    assert evaluate_generated_sandbox(evidence).verdict is SandboxVerdict.PASS


def test_cross_execution_tenant_source_or_artifact_evidence_fails_closed() -> None:
    mismatches = (
        replace(_preview(), execution_id="exec-other"),
        replace(_preview(), tenant_id="tenant-b"),
        replace(_preview(), source_sha256="c" * 64),
        replace(_preview(), artifact_sha256="d" * 64),
    )
    for preview in mismatches:
        with pytest.raises(ValueError, match="does not bind exactly"):
            produce_generated_sandbox_evidence(build=_build(), preview=preview, policy=_policy())


def test_policy_authority_is_derived_not_caller_fabricated() -> None:
    policy = ExecutionPolicy(
        allowed_roots=frozenset({"generated-web"}),
        secure_mode=False,
        network_allowed=True,
        secrets_allowed=False,
        timeout_seconds=120,
    )
    evidence = produce_generated_sandbox_evidence(build=_build(), preview=_preview(), policy=policy)
    result = evaluate_generated_sandbox(evidence)
    assert result.verdict is SandboxVerdict.FAIL
    assert "canonical execution policy is not in secure mode" in result.reasons
    assert "canonical execution policy grants direct network authority" in result.reasons


def test_build_observation_is_derived_from_incumbent_docker_runtime_evidence() -> None:
    observation = observe_docker_build_sandbox(
        execution_id="exec-web-1",
        tenant_id="tenant-a",
        source_sha256="a" * 64,
        artifact_sha256="b" * 64,
        runtime_evidence=_runtime_evidence(),
        boundary=DockerSecureCommandBoundary(
            runtime_image="ilaios/generated-runtime:test",
            memory_limit="1024m",
            cpu_limit="1.5",
        ),
        policy=_policy(),
    )

    assert observation.strong_process_sandbox is True
    assert observation.package_install_scripts_disabled is True
    assert observation.unrestricted_network_access is False
    assert observation.secret_material_access is False
    assert observation.docker_socket_access is False
    assert observation.wall_clock_timeout_seconds == 120
    assert observation.memory_limit_mb == 1024
    assert observation.cpu_limit_millis == 1500


def test_build_observation_rejects_cross_source_or_script_enabled_evidence() -> None:
    boundary = DockerSecureCommandBoundary(runtime_image="ilaios/generated-runtime:test")
    with pytest.raises(SoftwareFactoryError, match="another source"):
        observe_docker_build_sandbox(
            execution_id="exec-web-1",
            tenant_id="tenant-a",
            source_sha256="a" * 64,
            artifact_sha256="b" * 64,
            runtime_evidence=replace(_runtime_evidence(), workspace_sha256="c" * 64),
            boundary=boundary,
            policy=_policy(),
        )

    with pytest.raises(SoftwareFactoryError, match="lifecycle scripts"):
        observe_docker_build_sandbox(
            execution_id="exec-web-1",
            tenant_id="tenant-a",
            source_sha256="a" * 64,
            artifact_sha256="b" * 64,
            runtime_evidence=_runtime_evidence(
                dependency=("pnpm", "install", "--frozen-lockfile")
            ),
            boundary=boundary,
            policy=_policy(),
        )
