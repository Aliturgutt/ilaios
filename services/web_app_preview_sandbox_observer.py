"""Trusted-host observer for generated Web preview sandbox evidence.

This module does not create a preview runtime or a second policy authority. It turns
facts observed by the incumbent preview/runtime boundary into the canonical
``GeneratedPreviewSandboxObservation`` consumed by Web App sandbox acceptance.
Unknown or contradictory facts fail closed instead of being inferred as safe.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from services.software_factory import ExecutionPolicy, SoftwareFactoryError
from services.web_app_sandbox_evidence import GeneratedPreviewSandboxObservation


@dataclass(frozen=True, slots=True)
class PreviewHttpObservation:
    requested_url: str
    final_url: str
    request_cookie_header_present: bool
    authorization_header_present: bool
    response_csp: str


@dataclass(frozen=True, slots=True)
class PreviewRuntimeBoundaryObservation:
    execution_id: str
    tenant_id: str
    source_sha256: str
    artifact_sha256: str
    privileged_session_origin: str
    http: PreviewHttpObservation
    strong_process_sandbox: bool
    allowed_egress_hosts: tuple[str, ...]
    resolved_egress: tuple[tuple[str, str], ...]
    dns_snapshot_complete: bool
    dns_snapshot_age_seconds: int | None
    controlled_egress_gateway: bool
    secret_material_mounted: bool
    host_shell_mounted: bool
    docker_socket_mounted: bool
    control_plane_db_mounted: bool
    unrestricted_filesystem_mounted: bool
    unrestricted_network_enabled: bool
    signing_material_mounted: bool
    wall_clock_timeout_seconds: int | None
    memory_limit_mb: int | None
    cpu_limit_millis: int | None


def observe_generated_preview_sandbox(
    *,
    runtime: PreviewRuntimeBoundaryObservation,
    policy: ExecutionPolicy,
) -> GeneratedPreviewSandboxObservation:
    """Produce preview evidence only from exact trusted-host observations."""
    if not runtime.execution_id or not runtime.tenant_id:
        raise SoftwareFactoryError("generated preview execution binding is incomplete")
    for label, digest in (
        ("source", runtime.source_sha256),
        ("artifact", runtime.artifact_sha256),
    ):
        if len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
            raise SoftwareFactoryError(f"generated preview {label} digest is invalid")
    if not policy.secure_mode or policy.network_allowed or policy.secrets_allowed:
        raise SoftwareFactoryError("generated preview requires secure governed policy")

    requested_origin = _https_origin(runtime.http.requested_url, "requested preview URL")
    final_origin = _https_origin(runtime.http.final_url, "final preview URL")
    privileged_origin = _https_origin(runtime.privileged_session_origin, "privileged session origin")
    if requested_origin != final_origin:
        raise SoftwareFactoryError("generated preview redirected outside its observed origin")
    if final_origin == privileged_origin:
        raise SoftwareFactoryError("generated preview shares privileged session origin")
    if runtime.http.request_cookie_header_present:
        raise SoftwareFactoryError("generated preview request carried privileged cookie authority")
    if runtime.http.authorization_header_present:
        raise SoftwareFactoryError("generated preview request carried bearer authorization authority")
    if not runtime.http.response_csp.strip():
        raise SoftwareFactoryError("generated preview CSP observation is missing")

    return GeneratedPreviewSandboxObservation(
        execution_id=runtime.execution_id,
        tenant_id=runtime.tenant_id,
        source_sha256=runtime.source_sha256.lower(),
        artifact_sha256=runtime.artifact_sha256.lower(),
        separate_origin=True,
        strong_process_sandbox=runtime.strong_process_sandbox,
        generated_runtime_origin=final_origin,
        privileged_session_origin=privileged_origin,
        csp=runtime.http.response_csp,
        allowed_egress_hosts=runtime.allowed_egress_hosts,
        resolved_egress=runtime.resolved_egress,
        dns_snapshot_complete=runtime.dns_snapshot_complete,
        dns_snapshot_age_seconds=runtime.dns_snapshot_age_seconds,
        controlled_egress_gateway=runtime.controlled_egress_gateway,
        privileged_cookie_access=False,
        privileged_token_access=False,
        secret_material_access=runtime.secret_material_mounted,
        host_shell_access=runtime.host_shell_mounted,
        docker_socket_access=runtime.docker_socket_mounted,
        control_plane_db_access=runtime.control_plane_db_mounted,
        unrestricted_filesystem_access=runtime.unrestricted_filesystem_mounted,
        unrestricted_network_access=runtime.unrestricted_network_enabled,
        signing_material_access=runtime.signing_material_mounted,
        wall_clock_timeout_seconds=runtime.wall_clock_timeout_seconds,
        memory_limit_mb=runtime.memory_limit_mb,
        cpu_limit_millis=runtime.cpu_limit_millis,
    )


def _https_origin(value: str, label: str) -> str:
    raw = value.strip()
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as error:
        raise SoftwareFactoryError(f"{label} is malformed") from error
    if parsed.scheme.casefold() != "https" or parsed.hostname is None:
        raise SoftwareFactoryError(f"{label} must be HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise SoftwareFactoryError(f"{label} cannot contain userinfo")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise SoftwareFactoryError(f"{label} must be an exact origin")
    host = parsed.hostname.casefold().rstrip(".")
    if not host or "*" in host or "/" in host:
        raise SoftwareFactoryError(f"{label} host is invalid")
    return f"https://{host}" if port in (None, 443) else f"https://{host}:{port}"
