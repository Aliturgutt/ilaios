from __future__ import annotations

from dataclasses import replace

import pytest

from services.software_factory import ExecutionPolicy, SoftwareFactoryError
from services.web_app_preview_runtime_probe import (
    PreviewHttpProbeResult,
    PreviewIsolationBoundaryFacts,
    UrllibPreviewHttpTransport,
    probe_preview_runtime_boundary,
)
from services.web_app_preview_sandbox_observer import observe_generated_preview_sandbox


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
            final_url="https://preview.example.com",
            response_headers={
                "Content-Security-Policy": "default-src 'none'; script-src 'self'; object-src 'none'; base-uri 'none'"
            },
        )
    )
    runtime = probe_preview_runtime_boundary(
        preview_url="https://preview.example.com",
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
    assert transport.calls == [("https://preview.example.com", 11)]
    assert evidence.generated_runtime_origin == "https://preview.example.com"
    assert evidence.csp.startswith("default-src")
    assert evidence.privileged_cookie_access is False
    assert evidence.privileged_token_access is False


def test_probe_missing_csp_fails_closed_in_canonical_observer() -> None:
    runtime = probe_preview_runtime_boundary(
        preview_url="https://preview.example.com",
        execution_id="exec-1",
        tenant_id="tenant-a",
        source_sha256="a" * 64,
        artifact_sha256="b" * 64,
        privileged_session_origin="https://app.ilaios.com",
        isolation=_isolation(),
        transport=_Transport(
            PreviewHttpProbeResult(final_url="https://preview.example.com", response_headers={})
        ),
    )
    with pytest.raises(SoftwareFactoryError, match="CSP"):
        observe_generated_preview_sandbox(runtime=runtime, policy=_policy())


def test_probe_cross_origin_redirect_fails_closed_in_canonical_observer() -> None:
    runtime = probe_preview_runtime_boundary(
        preview_url="https://preview.example.com",
        execution_id="exec-1",
        tenant_id="tenant-a",
        source_sha256="a" * 64,
        artifact_sha256="b" * 64,
        privileged_session_origin="https://app.ilaios.com",
        isolation=_isolation(),
        transport=_Transport(
            PreviewHttpProbeResult(
                final_url="https://evil.example.com",
                response_headers={"Content-Security-Policy": "default-src 'none'"},
            )
        ),
    )
    with pytest.raises(SoftwareFactoryError, match="redirected outside"):
        observe_generated_preview_sandbox(runtime=runtime, policy=_policy())


def test_default_transport_rejects_unbounded_timeout_before_network() -> None:
    with pytest.raises(SoftwareFactoryError, match="timeout"):
        UrllibPreviewHttpTransport().get("https://preview.example.com", timeout_seconds=61)
