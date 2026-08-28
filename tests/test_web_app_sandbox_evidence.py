from __future__ import annotations

from dataclasses import replace

import pytest

from services.software_factory import ExecutionPolicy
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


def test_producer_binds_runtime_preview_and_canonical_policy() -> None:
    evidence = produce_generated_sandbox_evidence(
        build=_build(),
        preview=_preview(),
        policy=_policy(),
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
            produce_generated_sandbox_evidence(
                build=_build(),
                preview=preview,
                policy=_policy(),
            )


def test_policy_authority_is_derived_not_caller_fabricated() -> None:
    policy = ExecutionPolicy(
        allowed_roots=frozenset({"generated-web"}),
        secure_mode=False,
        network_allowed=True,
        secrets_allowed=False,
        timeout_seconds=120,
    )
    evidence = produce_generated_sandbox_evidence(
        build=_build(),
        preview=_preview(),
        policy=policy,
    )

    result = evaluate_generated_sandbox(evidence)
    assert result.verdict is SandboxVerdict.FAIL
    assert "canonical execution policy is not in secure mode" in result.reasons
    assert "canonical execution policy grants direct network authority" in result.reasons
