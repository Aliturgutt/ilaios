from __future__ import annotations

from dataclasses import replace

import pytest

from services.runtime.generated_app_docker_boundary import DockerSecureCommandBoundary
from services.software_factory import ExecutionPolicy, SoftwareFactoryError
from services.software_factory_runtime import RuntimeEvidence, RuntimeStepResult
from services.web_app_build_sandbox_observer import observe_docker_build_sandbox

_SOURCE = "a" * 64
_ARTIFACT = "b" * 64


def _policy(**overrides: object) -> ExecutionPolicy:
    values: dict[str, object] = {
        "allowed_roots": frozenset({"."}),
        "network_allowed": False,
        "secrets_allowed": False,
        "secure_mode": True,
        "timeout_seconds": 45,
    }
    values.update(overrides)
    return ExecutionPolicy(**values)  # type: ignore[arg-type]


def _step(stage: str, command: tuple[str, ...], *, passed: bool = True) -> RuntimeStepResult:
    return RuntimeStepResult(stage, command, 0 if passed else 1, "1" * 64, "2" * 64, passed)


def _runtime(*, dependency: tuple[str, ...] | None = None) -> RuntimeEvidence:
    command = dependency or (
        "pnpm",
        "install",
        "--offline",
        "--frozen-lockfile",
        "--ignore-scripts",
    )
    return RuntimeEvidence(
        adapter_id="ilaios.runtime.node",
        workspace_sha256=_SOURCE,
        steps=(
            _step("prepare", ("pnpm", "--version")),
            _step("resolve_dependencies", command),
            _step("lint", ("pnpm", "run", "lint")),
            _step("typecheck", ("pnpm", "run", "typecheck")),
            _step("test", ("pnpm", "run", "test:site")),
            _step("build", ("pnpm", "run", "build")),
            _step("package", ("pnpm", "pack", "--dry-run")),
            _step("smoke_test", ("pnpm", "run", "test:site")),
        ),
        passed=True,
    )


def _boundary() -> DockerSecureCommandBoundary:
    return DockerSecureCommandBoundary(
        runtime_image="ilaios/generated-runtime:test",
        memory_limit="1024m",
        cpu_limit="1.5",
    )


def test_observation_derives_enforced_docker_and_runtime_facts() -> None:
    observation = observe_docker_build_sandbox(
        execution_id="exec-1",
        tenant_id="tenant-1",
        source_sha256=_SOURCE,
        artifact_sha256=_ARTIFACT,
        runtime_evidence=_runtime(),
        boundary=_boundary(),
        policy=_policy(),
    )

    assert observation.strong_process_sandbox is True
    assert observation.package_install_scripts_disabled is True
    assert observation.unrestricted_network_access is False
    assert observation.secret_material_access is False
    assert observation.docker_socket_access is False
    assert observation.wall_clock_timeout_seconds == 45
    assert observation.memory_limit_mb == 1024
    assert observation.cpu_limit_millis == 1500


def test_observation_rejects_cross_source_runtime_evidence() -> None:
    evidence = replace(_runtime(), workspace_sha256="c" * 64)

    with pytest.raises(SoftwareFactoryError, match="another source"):
        observe_docker_build_sandbox(
            execution_id="exec-1",
            tenant_id="tenant-1",
            source_sha256=_SOURCE,
            artifact_sha256=_ARTIFACT,
            runtime_evidence=evidence,
            boundary=_boundary(),
            policy=_policy(),
        )


def test_observation_rejects_dependency_install_without_lifecycle_script_denial() -> None:
    evidence = _runtime(dependency=("pnpm", "install", "--frozen-lockfile"))

    with pytest.raises(SoftwareFactoryError, match="lifecycle scripts"):
        observe_docker_build_sandbox(
            execution_id="exec-1",
            tenant_id="tenant-1",
            source_sha256=_SOURCE,
            artifact_sha256=_ARTIFACT,
            runtime_evidence=evidence,
            boundary=_boundary(),
            policy=_policy(),
        )


def test_observation_rejects_policy_that_grants_network_or_secrets() -> None:
    for policy in (
        _policy(network_allowed=True),
        _policy(secrets_allowed=True),
        _policy(secure_mode=False),
    ):
        with pytest.raises(SoftwareFactoryError, match="secure no-network no-secret"):
            observe_docker_build_sandbox(
                execution_id="exec-1",
                tenant_id="tenant-1",
                source_sha256=_SOURCE,
                artifact_sha256=_ARTIFACT,
                runtime_evidence=_runtime(),
                boundary=_boundary(),
                policy=policy,
            )


def test_observation_rejects_unparseable_resource_limit_instead_of_claiming_it() -> None:
    boundary = DockerSecureCommandBoundary(
        runtime_image="ilaios/generated-runtime:test",
        memory_limit="unbounded",
        cpu_limit="1.0",
    )

    with pytest.raises(SoftwareFactoryError, match="resource limits"):
        observe_docker_build_sandbox(
            execution_id="exec-1",
            tenant_id="tenant-1",
            source_sha256=_SOURCE,
            artifact_sha256=_ARTIFACT,
            runtime_evidence=_runtime(),
            boundary=boundary,
            policy=_policy(),
        )
