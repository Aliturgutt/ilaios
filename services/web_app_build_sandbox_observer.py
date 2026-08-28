"""Trusted build-sandbox observation adapter for the canonical Web App runtime.

This module does not create a second sandbox. It projects facts enforced by the
existing ``DockerSecureCommandBoundary`` plus exact ``RuntimeEvidence`` into the
Phase-11 generated-sandbox evidence contract. Caller-supplied security booleans
are intentionally not accepted.
"""

from __future__ import annotations

import re

from services.runtime.generated_app_docker_boundary import DockerSecureCommandBoundary
from services.software_factory import ExecutionPolicy, SoftwareFactoryError
from services.software_factory_runtime import RuntimeEvidence, RuntimeStepResult
from services.web_app_sandbox_evidence import GeneratedBuildSandboxObservation

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MEMORY_RE = re.compile(r"^(\d+)([kKmMgG])$")


def observe_docker_build_sandbox(
    *,
    execution_id: str,
    tenant_id: str,
    source_sha256: str,
    artifact_sha256: str,
    runtime_evidence: RuntimeEvidence,
    boundary: DockerSecureCommandBoundary,
    policy: ExecutionPolicy,
) -> GeneratedBuildSandboxObservation:
    """Project exact passed runtime evidence into a build-sandbox observation.

    Security properties are derived from the concrete incumbent Docker boundary;
    they cannot be asserted by generated/imported code. The source digest must be
    the exact workspace digest collected by the runtime adapter, and dependency
    lifecycle-script denial must be visible in the passed dependency step.
    """

    if not execution_id.strip() or not tenant_id.strip():
        raise SoftwareFactoryError("generated sandbox lineage identity is incomplete")
    _require_sha256("source", source_sha256)
    _require_sha256("artifact", artifact_sha256)
    if runtime_evidence.workspace_sha256 != source_sha256:
        raise SoftwareFactoryError("generated sandbox runtime evidence is bound to another source")
    if not runtime_evidence.passed or not runtime_evidence.steps:
        raise SoftwareFactoryError("generated sandbox runtime evidence did not pass")
    if not policy.secure_mode or policy.network_allowed or policy.secrets_allowed:
        raise SoftwareFactoryError("generated sandbox observation requires secure no-network no-secret policy")

    dependency_step = _exact_stage(runtime_evidence.steps, "resolve_dependencies")
    scripts_disabled = _package_scripts_disabled(dependency_step)
    if not scripts_disabled:
        raise SoftwareFactoryError("generated sandbox package lifecycle scripts are not proven disabled")

    memory_limit_mb = _memory_limit_mb(boundary._memory_limit)
    cpu_limit_millis = _cpu_limit_millis(boundary._cpu_limit)
    if memory_limit_mb is None or cpu_limit_millis is None:
        raise SoftwareFactoryError("generated sandbox resource limits are not evidence-compatible")

    return GeneratedBuildSandboxObservation(
        execution_id=execution_id,
        tenant_id=tenant_id,
        source_sha256=source_sha256,
        artifact_sha256=artifact_sha256,
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
        wall_clock_timeout_seconds=policy.timeout_seconds,
        memory_limit_mb=memory_limit_mb,
        cpu_limit_millis=cpu_limit_millis,
    )


def _exact_stage(steps: tuple[RuntimeStepResult, ...], stage: str) -> RuntimeStepResult:
    matches = tuple(step for step in steps if step.stage == stage)
    if len(matches) != 1 or not matches[0].passed:
        raise SoftwareFactoryError(f"generated sandbox {stage} evidence is missing or failed")
    return matches[0]


def _package_scripts_disabled(step: RuntimeStepResult) -> bool:
    command = step.command
    return (
        len(command) >= 3
        and command[0] == "pnpm"
        and command[1] == "install"
        and "--ignore-scripts" in command[2:]
        and "--frozen-lockfile" in command[2:]
    )


def _require_sha256(label: str, value: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise SoftwareFactoryError(f"generated sandbox {label} SHA-256 is invalid")


def _memory_limit_mb(value: str) -> int | None:
    match = _MEMORY_RE.fullmatch(value.strip())
    if match is None:
        return None
    amount = int(match.group(1))
    unit = match.group(2).casefold()
    if amount <= 0:
        return None
    if unit == "g":
        return amount * 1024
    if unit == "m":
        return amount
    if unit == "k":
        return max(1, amount // 1024)
    return None


def _cpu_limit_millis(value: str) -> int | None:
    try:
        cores = float(value)
    except ValueError:
        return None
    millis = int(cores * 1000)
    return millis if millis > 0 else None
