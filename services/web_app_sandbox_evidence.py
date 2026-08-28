"""Fail-closed producer for canonical generated Web sandbox acceptance evidence.

This module does not create a second sandbox, policy authority, credential store, or
preview runtime. It binds observations emitted by the incumbent governed build
boundary and preview/runtime path into the existing ``GeneratedSandboxEvidence``
contract. Cross-execution, cross-tenant, cross-source, or cross-artifact evidence
is rejected before the acceptance evaluator can see it.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.software_factory import ExecutionPolicy
from services.web_generated_sandbox_gate import GeneratedSandboxEvidence


@dataclass(frozen=True, slots=True)
class GeneratedBuildSandboxObservation:
    execution_id: str
    tenant_id: str
    source_sha256: str
    artifact_sha256: str
    strong_process_sandbox: bool
    privileged_cookie_access: bool
    privileged_token_access: bool
    secret_material_access: bool
    host_shell_access: bool
    docker_socket_access: bool
    control_plane_db_access: bool
    unrestricted_filesystem_access: bool
    unrestricted_network_access: bool
    signing_material_access: bool
    package_install_scripts_disabled: bool
    wall_clock_timeout_seconds: int | None
    memory_limit_mb: int | None
    cpu_limit_millis: int | None


@dataclass(frozen=True, slots=True)
class GeneratedPreviewSandboxObservation:
    execution_id: str
    tenant_id: str
    source_sha256: str
    artifact_sha256: str
    separate_origin: bool
    generated_runtime_origin: str
    privileged_session_origin: str
    csp: str
    allowed_egress_hosts: tuple[str, ...]
    resolved_egress: tuple[tuple[str, str], ...]
    dns_snapshot_complete: bool
    dns_snapshot_age_seconds: int | None
    controlled_egress_gateway: bool


def produce_generated_sandbox_evidence(
    *,
    build: GeneratedBuildSandboxObservation,
    preview: GeneratedPreviewSandboxObservation,
    policy: ExecutionPolicy,
) -> GeneratedSandboxEvidence:
    """Bind independent runtime observations into one immutable acceptance record.

    The producer deliberately derives canonical-policy fields from the incumbent
    ``ExecutionPolicy`` instead of accepting caller-supplied policy booleans. The
    build and preview observations must describe the same execution, tenant,
    source and artifact; otherwise evidence production fails closed.
    """

    _require_exact_binding("execution_id", build.execution_id, preview.execution_id)
    _require_exact_binding("tenant_id", build.tenant_id, preview.tenant_id)
    _require_exact_binding("source_sha256", build.source_sha256, preview.source_sha256)
    _require_exact_binding("artifact_sha256", build.artifact_sha256, preview.artifact_sha256)

    return GeneratedSandboxEvidence(
        execution_id=build.execution_id,
        tenant_id=build.tenant_id,
        source_sha256=build.source_sha256,
        artifact_sha256=build.artifact_sha256,
        separate_origin=preview.separate_origin,
        strong_process_sandbox=build.strong_process_sandbox,
        generated_runtime_origin=preview.generated_runtime_origin,
        privileged_session_origin=preview.privileged_session_origin,
        csp=preview.csp,
        allowed_egress_hosts=preview.allowed_egress_hosts,
        resolved_egress=preview.resolved_egress,
        dns_snapshot_complete=preview.dns_snapshot_complete,
        dns_snapshot_age_seconds=preview.dns_snapshot_age_seconds,
        privileged_cookie_access=build.privileged_cookie_access,
        privileged_token_access=build.privileged_token_access,
        secret_material_access=build.secret_material_access,
        host_shell_access=build.host_shell_access,
        docker_socket_access=build.docker_socket_access,
        control_plane_db_access=build.control_plane_db_access,
        unrestricted_filesystem_access=build.unrestricted_filesystem_access,
        unrestricted_network_access=build.unrestricted_network_access,
        signing_material_access=build.signing_material_access,
        package_install_scripts_disabled=build.package_install_scripts_disabled,
        canonical_policy_secure_mode=policy.secure_mode,
        canonical_policy_network_allowed=policy.network_allowed,
        canonical_policy_secrets_allowed=policy.secrets_allowed,
        canonical_policy_timeout_seconds=policy.timeout_seconds,
        controlled_egress_gateway=preview.controlled_egress_gateway,
        wall_clock_timeout_seconds=build.wall_clock_timeout_seconds,
        memory_limit_mb=build.memory_limit_mb,
        cpu_limit_millis=build.cpu_limit_millis,
    )


def _require_exact_binding(label: str, build_value: str, preview_value: str) -> None:
    if not build_value or not preview_value or build_value != preview_value:
        raise ValueError(f"generated sandbox {label} evidence does not bind exactly")
