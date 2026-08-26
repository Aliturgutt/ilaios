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
    hostile_evidence = (
        replace(_evidence(), privileged_cookie_access=True),
        replace(_evidence(), privileged_token_access=True),
        replace(_evidence(), secret_material_access=True),
        replace(_evidence(), host_shell_access=True),
        replace(_evidence(), docker_socket_access=True),
        replace(_evidence(), control_plane_db_access=True),
        replace(_evidence(), unrestricted_filesystem_access=True),
        replace(_evidence(), unrestricted_network_access=True),
        replace(_evidence(), signing_material_access=True),
    )
    for evidence in hostile_evidence:
        result = evaluate_generated_sandbox(evidence)
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


def test_csp_default_and_script_sources_fail_closed() -> None:
    hostile_csp = (
        "default-src *; script-src 'self'; connect-src api.example.com; "
        "object-src 'none'; base-uri 'none'",
        "default-src 'none'; script-src *; connect-src api.example.com; "
        "object-src 'none'; base-uri 'none'",
        "default-src 'none'; script-src https://cdn.example.com; connect-src api.example.com; "
        "object-src 'none'; base-uri 'none'",
        "default-src 'none'; script-src 'unsafe-eval'; connect-src api.example.com; "
        "object-src 'none'; base-uri 'none'",
    )
    for csp in hostile_csp:
        result = evaluate_generated_sandbox(replace(_evidence(), csp=csp))
        assert result.verdict is SandboxVerdict.FAIL


def test_csp_connect_sources_cannot_exceed_runtime_egress_allowlist() -> None:
    result = evaluate_generated_sandbox(
        replace(
            _evidence(),
            csp=(
                "default-src 'none'; script-src 'self'; connect-src api.example.com evil.example; "
                "object-src 'none'; base-uri 'none'"
            ),
        )
    )
    assert result.verdict is SandboxVerdict.FAIL
    assert "CSP connect-src exceeds the controlled egress allowlist" in result.reasons


def test_csp_duplicate_directives_fail_closed() -> None:
    result = evaluate_generated_sandbox(
        replace(
            _evidence(),
            csp=(
                "default-src 'none'; script-src 'self'; connect-src api.example.com; "
                "connect-src evil.example; object-src 'none'; base-uri 'none'"
            ),
        )
    )
    assert result.verdict is SandboxVerdict.FAIL
    assert "CSP contains duplicate directives" in result.reasons


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
