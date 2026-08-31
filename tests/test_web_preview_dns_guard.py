from __future__ import annotations

import socket

import pytest

import services.web_app_preview_runtime_probe as preview_probe
from services.software_factory import SoftwareFactoryError
from services.web_app_preview_runtime_probe import (
    PreviewHttpProbeResult,
    PreviewIsolationBoundaryFacts,
    probe_preview_runtime_boundary,
)


class _Transport:
    def __init__(self, result: PreviewHttpProbeResult) -> None:
        self.result = result
        self.calls: list[tuple[str, int]] = []

    def get(self, url: str, *, timeout_seconds: int) -> PreviewHttpProbeResult:
        self.calls.append((url, timeout_seconds))
        return self.result


def _isolation() -> PreviewIsolationBoundaryFacts:
    return PreviewIsolationBoundaryFacts(
        strong_process_sandbox=True,
        allowed_egress_hosts=("api.example.com",),
        resolved_egress=(("api.example.com", "93.184.216.34"),),
        dns_snapshot_complete=True,
        dns_snapshot_age_seconds=1,
        controlled_egress_gateway=True,
        secret_material_mounted=False,
        host_shell_mounted=False,
        docker_socket_mounted=False,
        control_plane_db_mounted=False,
        unrestricted_filesystem_mounted=False,
        unrestricted_network_enabled=False,
        signing_material_mounted=False,
        wall_clock_timeout_seconds=60,
        memory_limit_mb=512,
        cpu_limit_millis=750,
    )


def test_injected_transport_rejects_private_dns_before_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        preview_probe,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("10.0.0.7", 443))
        ],
    )
    transport = _Transport(
        PreviewHttpProbeResult(
            final_url="https://preview.example.com",
            response_headers={"Content-Security-Policy": "default-src 'none'"},
        )
    )

    with pytest.raises(SoftwareFactoryError, match="DNS resolves to a non-public address"):
        probe_preview_runtime_boundary(
            preview_url="https://preview.example.com",
            execution_id="exec-dns-guard",
            tenant_id="tenant-a",
            source_sha256="a" * 64,
            artifact_sha256="b" * 64,
            privileged_session_origin="https://app.ilaios.com",
            isolation=_isolation(),
            transport=transport,
        )

    assert transport.calls == []


def test_injected_transport_revalidates_final_hostname_dns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _resolve(host: str, port: int, **kwargs: object) -> list[tuple[object, ...]]:
        address = "169.254.169.254" if host == "rebound.example.com" else "93.184.216.34"
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, port))]

    monkeypatch.setattr(preview_probe, "getaddrinfo", _resolve)
    transport = _Transport(
        PreviewHttpProbeResult(
            final_url="https://rebound.example.com",
            response_headers={"Content-Security-Policy": "default-src 'none'"},
        )
    )

    with pytest.raises(SoftwareFactoryError, match="DNS resolves to a non-public address"):
        probe_preview_runtime_boundary(
            preview_url="https://preview.example.com",
            execution_id="exec-dns-guard",
            tenant_id="tenant-a",
            source_sha256="a" * 64,
            artifact_sha256="b" * 64,
            privileged_session_origin="https://app.ilaios.com",
            isolation=_isolation(),
            transport=transport,
        )

    assert transport.calls == [("https://preview.example.com", 15)]
