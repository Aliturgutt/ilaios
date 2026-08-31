"""Trusted-host HTTPS probe for generated Web preview sandbox observations.

The probe is an observation producer only. It does not create a preview runtime,
grant egress, own credentials, deploy, or publish. It performs a credential-free
HTTPS request through a bounded transport and combines the observed HTTP facts with
trusted isolation facts supplied by the incumbent runtime boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
from socket import AF_INET, AF_INET6, SOCK_STREAM, getaddrinfo
from typing import Any, Mapping, Protocol
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

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


class _RejectPreviewRedirects(HTTPRedirectHandler):
    """Prevent the observer host from following untrusted preview redirects."""

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        raise SoftwareFactoryError("generated preview redirect denied before follow")


class UrllibPreviewHttpTransport:
    """Credential-free stdlib HTTPS transport used by the trusted observer host."""

    def get(self, url: str, *, timeout_seconds: int) -> PreviewHttpProbeResult:
        if timeout_seconds < 1 or timeout_seconds > 60:
            raise SoftwareFactoryError("preview probe timeout is invalid")
        _validate_public_https_target(url, resolve_dns=True)
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
            opener = build_opener(ProxyHandler({}), _RejectPreviewRedirects())
            with opener.open(request, timeout=timeout_seconds) as response:
                headers = {str(key): str(value) for key, value in response.headers.items()}
                final_url = response.geturl()
                _validate_public_https_target(final_url, resolve_dns=True)
                return PreviewHttpProbeResult(final_url=final_url, response_headers=headers)
        except SoftwareFactoryError:
            raise
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
    _validate_public_https_target(preview_url, resolve_dns=True)
    client = transport or UrllibPreviewHttpTransport()
    result = client.get(preview_url, timeout_seconds=timeout_seconds)
    _validate_public_https_target(result.final_url, resolve_dns=True)
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


def _validate_public_https_target(value: str, *, resolve_dns: bool = False) -> None:
    raw = value.strip()
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as error:
        raise SoftwareFactoryError("generated preview target is malformed") from error
    if parsed.scheme.casefold() != "https" or parsed.hostname is None:
        raise SoftwareFactoryError("generated preview target must be HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise SoftwareFactoryError("generated preview target cannot contain userinfo")
    if port is not None and (port < 1 or port > 65535):
        raise SoftwareFactoryError("generated preview target port is invalid")

    host = parsed.hostname.casefold().rstrip(".")
    if not host or host == "localhost" or host.endswith(".localhost"):
        raise SoftwareFactoryError("generated preview target cannot be local")
    try:
        address = ip_address(host)
    except ValueError:
        if resolve_dns:
            _require_public_dns_resolution(host, 443 if port is None else port)
        return
    if not address.is_global:
        raise SoftwareFactoryError("generated preview target IP must be globally routable")


def _require_public_dns_resolution(host: str, port: int) -> None:
    """Fail closed when a preview hostname resolves to any non-public address."""
    try:
        answers = getaddrinfo(host, port, family=0, type=SOCK_STREAM)
    except OSError as error:
        raise SoftwareFactoryError("generated preview target DNS resolution failed closed") from error
    addresses: set[str] = set()
    for family, _socktype, _proto, _canonname, sockaddr in answers:
        if family not in (AF_INET, AF_INET6) or not sockaddr:
            continue
        addresses.add(str(sockaddr[0]))
    if not addresses:
        raise SoftwareFactoryError("generated preview target DNS resolution is empty")
    for raw_address in addresses:
        try:
            address = ip_address(raw_address)
        except ValueError as error:
            raise SoftwareFactoryError("generated preview target DNS answer is invalid") from error
        if not address.is_global:
            raise SoftwareFactoryError(
                "generated preview target DNS resolves to a non-public address"
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
