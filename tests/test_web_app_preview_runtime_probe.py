from __future__ import annotations

import socket

import pytest

import services.web_app_preview_runtime_probe as preview_probe
from services.software_factory import ExecutionPolicy, SoftwareFactoryError
from services.web_app_preview_runtime_probe import (
    PreviewHttpProbeResult,
    PreviewIsolationBoundaryFacts,
    UrllibPreviewHttpTransport,
    probe_preview_runtime_boundary,
)
from services.web_app_preview_sandbox_observer import observe_generated_preview_sandbox


PUBLIC_PREVIEW = "https://93.184.216.34"
PUBLIC_OTHER = "https://8.8.8.8"


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
        dns_snapshot_age_seconds=12,
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


def _policy() -> ExecutionPolicy:
    return ExecutionPolicy(allowed_roots=frozenset({"generated-web"}), timeout_seconds=120)


def test_probe_emits_observer_accepted_runtime_facts() -> None:
    transport = _Transport(
        PreviewHttpProbeResult(
            final_url=PUBLIC_PREVIEW,
            response_headers={
                "Content-Security-Policy": "default-src 'none'; script-src 'self'; object-src 'none'; base-uri 'none'"
            },
        )
    )
    runtime = probe_preview_runtime_boundary(
        preview_url=PUBLIC_PREVIEW,
        execution_id="exec-1",
        tenant_id="tenant-a",
        source_sha256="a" * 64,
        artifact_sha256="b" * 64,
        privileged_session_origin="https://app.ilaios.com",
        isolation=_isolation(),
        transport=transport,
        timeout_seconds=11,
    )
    evidence = observe_generated_preview_sandbox(runtime=runtime, policy=_policy())
    assert transport.calls == [(PUBLIC_PREVIEW, 11)]
    assert evidence.generated_runtime_origin == PUBLIC_PREVIEW
    assert evidence.csp.startswith("default-src")
    assert evidence.privileged_cookie_access is False
    assert evidence.privileged_token_access is False


def test_probe_missing_csp_fails_closed_in_canonical_observer() -> None:
    runtime = probe_preview_runtime_boundary(
        preview_url=PUBLIC_PREVIEW,
        execution_id="exec-1",
        tenant_id="tenant-a",
        source_sha256="a" * 64,
        artifact_sha256="b" * 64,
        privileged_session_origin="https://app.ilaios.com",
        isolation=_isolation(),
        transport=_Transport(PreviewHttpProbeResult(final_url=PUBLIC_PREVIEW, response_headers={})),
    )
    with pytest.raises(SoftwareFactoryError, match="CSP"):
        observe_generated_preview_sandbox(runtime=runtime, policy=_policy())


def test_probe_cross_origin_redirect_fails_closed_in_canonical_observer() -> None:
    runtime = probe_preview_runtime_boundary(
        preview_url=PUBLIC_PREVIEW,
        execution_id="exec-1",
        tenant_id="tenant-a",
        source_sha256="a" * 64,
        artifact_sha256="b" * 64,
        privileged_session_origin="https://app.ilaios.com",
        isolation=_isolation(),
        transport=_Transport(
            PreviewHttpProbeResult(
                final_url=PUBLIC_OTHER,
                response_headers={"Content-Security-Policy": "default-src 'none'"},
            )
        ),
    )
    with pytest.raises(SoftwareFactoryError, match="redirected outside"):
        observe_generated_preview_sandbox(runtime=runtime, policy=_policy())


def _assert_probe_rejects_non_public_target(preview_url: str) -> None:
    transport = _Transport(
        PreviewHttpProbeResult(
            final_url=PUBLIC_PREVIEW,
            response_headers={"Content-Security-Policy": "default-src 'none'"},
        )
    )
    with pytest.raises(SoftwareFactoryError, match="target"):
        probe_preview_runtime_boundary(
            preview_url=preview_url,
            execution_id="exec-1",
            tenant_id="tenant-a",
            source_sha256="a" * 64,
            artifact_sha256="b" * 64,
            privileged_session_origin="https://app.ilaios.com",
            isolation=_isolation(),
            transport=transport,
        )
    assert transport.calls == []


def test_probe_rejects_http_target_before_transport() -> None:
    _assert_probe_rejects_non_public_target("http://preview.example.com")


def test_probe_rejects_localhost_target_before_transport() -> None:
    _assert_probe_rejects_non_public_target("https://localhost")


def test_probe_rejects_localhost_subdomain_before_transport() -> None:
    _assert_probe_rejects_non_public_target("https://preview.localhost")


def test_probe_rejects_loopback_ipv4_target_before_transport() -> None:
    _assert_probe_rejects_non_public_target("https://127.0.0.1")


def test_probe_rejects_link_local_metadata_target_before_transport() -> None:
    _assert_probe_rejects_non_public_target("https://169.254.169.254/latest/meta-data")


def test_probe_rejects_private_ipv4_target_before_transport() -> None:
    _assert_probe_rejects_non_public_target("https://10.0.0.8")


def test_probe_rejects_loopback_ipv6_target_before_transport() -> None:
    _assert_probe_rejects_non_public_target("https://[::1]")


def test_probe_rejects_private_final_target_from_injected_transport() -> None:
    transport = _Transport(
        PreviewHttpProbeResult(
            final_url="https://169.254.169.254/latest/meta-data",
            response_headers={"Content-Security-Policy": "default-src 'none'"},
        )
    )
    with pytest.raises(SoftwareFactoryError, match="globally routable"):
        probe_preview_runtime_boundary(
            preview_url=PUBLIC_PREVIEW,
            execution_id="exec-1",
            tenant_id="tenant-a",
            source_sha256="a" * 64,
            artifact_sha256="b" * 64,
            privileged_session_origin="https://app.ilaios.com",
            isolation=_isolation(),
            transport=transport,
        )
    assert transport.calls == [(PUBLIC_PREVIEW, 15)]


def test_default_transport_rejects_unbounded_timeout_before_network() -> None:
    with pytest.raises(SoftwareFactoryError, match="timeout"):
        UrllibPreviewHttpTransport().get("https://preview.example.com", timeout_seconds=61)


def test_default_transport_rejects_hostname_resolving_to_private_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        preview_probe,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("10.0.0.7", 443))
        ],
    )
    with pytest.raises(SoftwareFactoryError, match="DNS resolves to a non-public address"):
        UrllibPreviewHttpTransport().get("https://preview.example.com", timeout_seconds=5)


def test_default_transport_rejects_mixed_public_private_dns_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        preview_probe,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("169.254.169.254", 443)),
        ],
    )
    with pytest.raises(SoftwareFactoryError, match="DNS resolves to a non-public address"):
        UrllibPreviewHttpTransport().get("https://preview.example.com", timeout_seconds=5)
