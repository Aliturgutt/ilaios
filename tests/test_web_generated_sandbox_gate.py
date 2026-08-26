from __future__ import annotations

from dataclasses import replace

from services.web_generated_sandbox_gate import (
    GeneratedSandboxEvidence,
    SandboxVerdict,
    evaluate_generated_sandbox,
)


def _evidence() -> GeneratedSandboxEvidence:
    return GeneratedSandboxEvidence(
        execution_id="exec-web-1",
        tenant_id="tenant-a",
        source_sha256="a" * 64,
        artifact_sha256="b" * 64,
        separate_origin=True,
        strong_process_sandbox=True,
        csp=(
            "default-src 'none'; script-src 'self'; connect-src api.example.com; "
            "object-src 'none'; base-uri 'none'"
        ),
        allowed_egress_hosts=("api.example.com",),
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


def test_complete_sandbox_evidence_passes() -> None:
    result = evaluate_generated_sandbox(_evidence())
    assert result.verdict is SandboxVerdict.PASS
    assert result.reasons == ()


def test_missing_enforced_resource_bound_is_not_verified() -> None:
    result = evaluate_generated_sandbox(replace(_evidence(), memory_limit_mb=None))
    assert result.verdict is SandboxVerdict.NOT_VERIFIED
    assert "missing evidence: memory limit" in result.reasons


def test_same_trust_domain_fails_closed() -> None:
    result = evaluate_generated_sandbox(
        replace(_evidence(), separate_origin=False, strong_process_sandbox=False)
    )
    assert result.verdict is SandboxVerdict.FAIL
    assert any("separate-origin" in reason for reason in result.reasons)


def test_privileged_capability_exposure_fails() -> None:
    for field_name in (
        "privileged_cookie_access",
        "privileged_token_access",
        "secret_material_access",
        "host_shell_access",
        "docker_socket_access",
        "control_plane_db_access",
        "unrestricted_filesystem_access",
        "unrestricted_network_access",
        "signing_material_access",
    ):
        result = evaluate_generated_sandbox(replace(_evidence(), **{field_name: True}))
        assert result.verdict is SandboxVerdict.FAIL
        assert any("forbidden capability" in reason for reason in result.reasons)


def test_package_lifecycle_scripts_must_be_disabled() -> None:
    result = evaluate_generated_sandbox(
        replace(_evidence(), package_install_scripts_disabled=False)
    )
    assert result.verdict is SandboxVerdict.FAIL
    assert "package lifecycle scripts are not proven disabled" in result.reasons


def test_csp_wildcard_egress_and_missing_hardening_fail() -> None:
    result = evaluate_generated_sandbox(
        replace(
            _evidence(),
            csp="default-src 'none'; script-src 'self'; connect-src *",
        )
    )
    assert result.verdict is SandboxVerdict.FAIL
    assert "CSP connect-src cannot allow wildcard egress" in result.reasons
    assert "CSP is missing object-src" in result.reasons
    assert "CSP is missing base-uri" in result.reasons


def test_egress_allowlist_rejects_wildcards_urls_and_paths() -> None:
    for host in ("*", "*.example.com", "https://api.example.com", "api.example.com/v1"):
        result = evaluate_generated_sandbox(
            replace(_evidence(), allowed_egress_hosts=(host,))
        )
        assert result.verdict is SandboxVerdict.FAIL
        assert "egress allowlist contains an invalid or wildcard host" in result.reasons


def test_cross_sha_or_malformed_digest_evidence_fails() -> None:
    result = evaluate_generated_sandbox(
        replace(_evidence(), source_sha256="not-a-sha", artifact_sha256="z" * 64)
    )
    assert result.verdict is SandboxVerdict.FAIL
    assert "source_sha256 must be an exact SHA-256 hex digest" in result.reasons
    assert "artifact_sha256 must be an exact SHA-256 hex digest" in result.reasons


def test_nonpositive_resource_limits_fail() -> None:
    result = evaluate_generated_sandbox(
        replace(
            _evidence(),
            wall_clock_timeout_seconds=0,
            memory_limit_mb=-1,
            cpu_limit_millis=0,
        )
    )
    assert result.verdict is SandboxVerdict.FAIL
    assert len(result.reasons) == 3
