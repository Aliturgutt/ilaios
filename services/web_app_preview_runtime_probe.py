"""Trusted-host HTTPS probe for generated Web preview sandbox observations.

The probe is an observation producer only. It does not create a preview runtime,
grant egress, own credentials, deploy, or publish. It performs a credential-free
HTTPS request through a bounded transport and combines the observed HTTP facts with
trusted isolation facts supplied by the incumbent runtime boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol
from urllib.request import ProxyHandler, Request, build_opener

from services.software_factory import SoftwareFactoryError
from services.web_app_preview_sandbox_observer import (
    PreviewHttpObservation,
    PreviewRuntimeBoundaryObservation,
)


@dataclass(frozen=True, slots=True)
class PreviewIsolationBoundaryFacts:
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


@dataclass(frozen=True, slots=True)
class PreviewHttpProbeResult:
    final_url: str
    response_headers: Mapping[str, str]


class PreviewHttpTransport(Protocol):
    def get(self, url: str, *, timeout_seconds: int) -> PreviewHttpProbeResult: ...


class UrllibPreviewHttpTransport:
    """Credential-free stdlib HTTPS transport used by the trusted observer host."""

    def get(self, url: str, *, timeout_seconds: int) -> PreviewHttpProbeResult:
        if timeout_seconds < 1 or timeout_seconds > 60:
            raise SoftwareFactoryError("preview probe timeout is invalid")
        request = Request(
            url,
            method="GET",
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "User-Agent": "ILAIOS-Web-Preview-Observer/1",
            },
        )
        try:
            # Never inherit host HTTP(S)_PROXY configuration or proxy credentials.
            # Governed egress gateways must be supplied explicitly by the incumbent
            # runtime through another PreviewHttpTransport implementation.
            opener = build_opener(ProxyHandler({}))
            with opener.open(request, timeout=timeout_seconds) as response:
                headers = {str(key): str(value) for key, value in response.headers.items()}
                return PreviewHttpProbeResult(final_url=response.geturl(), response_headers=headers)
        except Exception as error:
            raise SoftwareFactoryError("generated preview HTTPS probe failed closed") from error


def probe_preview_runtime_boundary(
    *,
    preview_url: str,
    execution_id: str,
    tenant_id: str,
    source_sha256: str,
    artifact_sha256: str,
    privileged_session_origin: str,
    isolation: PreviewIsolationBoundaryFacts,
    transport: PreviewHttpTransport | None = None,
    timeout_seconds: int = 15,
) -> PreviewRuntimeBoundaryObservation:
    """Emit trusted runtime observation from a real credential-free HTTP probe."""
    if not preview_url.strip():
        raise SoftwareFactoryError("generated preview URL is missing")
    client = transport or UrllibPreviewHttpTransport()
    result = client.get(preview_url, timeout_seconds=timeout_seconds)
    csp = _header(result.response_headers, "content-security-policy")
    return PreviewRuntimeBoundaryObservation(
        execution_id=execution_id,
        tenant_id=tenant_id,
        source_sha256=source_sha256,
        artifact_sha256=artifact_sha256,
        privileged_session_origin=privileged_session_origin,
        http=PreviewHttpObservation(
            requested_url=preview_url,
            final_url=result.final_url,
            request_cookie_header_present=False,
            authorization_header_present=False,
            response_csp=csp,
        ),
        strong_process_sandbox=isolation.strong_process_sandbox,
        allowed_egress_hosts=isolation.allowed_egress_hosts,
        resolved_egress=isolation.resolved_egress,
        dns_snapshot_complete=isolation.dns_snapshot_complete,
        dns_snapshot_age_seconds=isolation.dns_snapshot_age_seconds,
        controlled_egress_gateway=isolation.controlled_egress_gateway,
        secret_material_mounted=isolation.secret_material_mounted,
        host_shell_mounted=isolation.host_shell_mounted,
        docker_socket_mounted=isolation.docker_socket_mounted,
        control_plane_db_mounted=isolation.control_plane_db_mounted,
        unrestricted_filesystem_mounted=isolation.unrestricted_filesystem_mounted,
        unrestricted_network_enabled=isolation.unrestricted_network_enabled,
        signing_material_mounted=isolation.signing_material_mounted,
        wall_clock_timeout_seconds=isolation.wall_clock_timeout_seconds,
        memory_limit_mb=isolation.memory_limit_mb,
        cpu_limit_millis=isolation.cpu_limit_millis,
    )


def _header(headers: Mapping[str, str], name: str) -> str:
    wanted = name.casefold()
    for key, value in headers.items():
        if key.casefold() == wanted:
            return value.strip()
    return ""


__all__ = [
    "PreviewHttpProbeResult",
    "PreviewHttpTransport",
    "PreviewIsolationBoundaryFacts",
    "UrllibPreviewHttpTransport",
    "probe_preview_runtime_boundary",
]
