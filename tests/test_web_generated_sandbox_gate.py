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
        canonical_policy_secure_mode=True,
        canonical_policy_network_allowed=False,
        canonical_policy_secrets_allowed=False,
        canonical_policy_timeout_seconds=120,
        controlled_egress_gateway=True,
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


def test_canonical_policy_binding_is_required() -> None:
    missing = evaluate_generated_sandbox(
        replace(_evidence(), canonical_policy_timeout_seconds=None)
    )
    assert missing.verdict is SandboxVerdict.NOT_VERIFIED
    assert "missing evidence: canonical policy timeout" in missing.reasons
    for evidence in (
        replace(_evidence(), canonical_policy_secure_mode=False),
        replace(_evidence(), canonical_policy_network_allowed=True),
        replace(_evidence(), canonical_policy_secrets_allowed=True),
        replace(_evidence(), controlled_egress_gateway=False),
    ):
        assert evaluate_generated_sandbox(evidence).verdict is SandboxVerdict.FAIL


def test_runtime_timeout_cannot_exceed_canonical_policy() -> None:
    result = evaluate_generated_sandbox(replace(_evidence(), canonical_policy_timeout_seconds=60, wall_clock_timeout_seconds=61))
    assert result.verdict is SandboxVerdict.FAIL
    assert "sandbox wall clock timeout exceeds canonical execution policy" in result.reasons


def test_same_trust_domain_fails_closed() -> None:
    result = evaluate_generated_sandbox(replace(_evidence(), separate_origin=False, strong_process_sandbox=False))
    assert result.verdict is SandboxVerdict.FAIL


def test_separate_origin_requires_exact_origin_binding() -> None:
    assert evaluate_generated_sandbox(replace(_evidence(), generated_runtime_origin="")).verdict is SandboxVerdict.NOT_VERIFIED
    assert evaluate_generated_sandbox(replace(_evidence(), privileged_session_origin="")).verdict is SandboxVerdict.NOT_VERIFIED


def test_generated_origin_cannot_equal_privileged_session_origin() -> None:
    result = evaluate_generated_sandbox(replace(_evidence(), generated_runtime_origin="https://app.example.com", privileged_session_origin="https://app.example.com/"))
    assert result.verdict is SandboxVerdict.FAIL


def test_separate_origin_cannot_rely_on_port_only() -> None:
    result = evaluate_generated_sandbox(replace(_evidence(), generated_runtime_origin="https://app.example.com:8443", privileged_session_origin="https://app.example.com"))
    assert result.verdict is SandboxVerdict.FAIL


def test_origin_binding_rejects_non_https_or_non_origin_values() -> None:
    for generated, privileged in (
        ("http://preview.example.com", "https://app.example.com"),
        ("https://preview.example.com/path", "https://app.example.com"),
        ("https://user@preview.example.com", "https://app.example.com"),
        ("https://preview.example.com", "https://localhost"),
    ):
        assert evaluate_generated_sandbox(replace(_evidence(), generated_runtime_origin=generated, privileged_session_origin=privileged)).verdict is SandboxVerdict.FAIL


def test_privileged_capability_exposure_fails() -> None:
    for evidence in (
        replace(_evidence(), privileged_cookie_access=True),
        replace(_evidence(), privileged_token_access=True),
        replace(_evidence(), secret_material_access=True),
        replace(_evidence(), host_shell_access=True),
        replace(_evidence(), docker_socket_access=True),
        replace(_evidence(), control_plane_db_access=True),
        replace(_evidence(), unrestricted_filesystem_access=True),
        replace(_evidence(), unrestricted_network_access=True),
        replace(_evidence(), signing_material_access=True),
    ):
        assert evaluate_generated_sandbox(evidence).verdict is SandboxVerdict.FAIL


def test_package_lifecycle_scripts_must_be_disabled() -> None:
    assert evaluate_generated_sandbox(replace(_evidence(), package_install_scripts_disabled=False)).verdict is SandboxVerdict.FAIL


def test_csp_wildcard_egress_and_missing_hardening_fail() -> None:
    result = evaluate_generated_sandbox(replace(_evidence(), csp="default-src 'none'; script-src 'self'; connect-src *"))
    assert result.verdict is SandboxVerdict.FAIL


def test_csp_default_and_script_sources_fail_closed() -> None:
    for csp in (
        "default-src *; script-src 'self'; connect-src api.example.com; object-src 'none'; base-uri 'none'",
        "default-src 'none'; script-src *; connect-src api.example.com; object-src 'none'; base-uri 'none'",
        "default-src 'none'; script-src https://cdn.example.com; connect-src api.example.com; object-src 'none'; base-uri 'none'",
        "default-src 'none'; script-src 'unsafe-eval'; connect-src api.example.com; object-src 'none'; base-uri 'none'",
    ):
        assert evaluate_generated_sandbox(replace(_evidence(), csp=csp)).verdict is SandboxVerdict.FAIL


def test_csp_connect_sources_cannot_exceed_runtime_egress_allowlist() -> None:
    result = evaluate_generated_sandbox(replace(_evidence(), csp="default-src 'none'; script-src 'self'; connect-src api.example.com evil.example; object-src 'none'; base-uri 'none'"))
    assert result.verdict is SandboxVerdict.FAIL


def test_csp_duplicate_directives_fail_closed() -> None:
    result = evaluate_generated_sandbox(replace(_evidence(), csp="default-src 'none'; script-src 'self'; connect-src api.example.com; connect-src evil.example; object-src 'none'; base-uri 'none'"))
    assert result.verdict is SandboxVerdict.FAIL


def test_egress_allowlist_rejects_wildcards_urls_and_paths() -> None:
    for host in ("*", "*.example.com", "https://api.example.com", "api.example.com/v1"):
        assert evaluate_generated_sandbox(replace(_evidence(), allowed_egress_hosts=(host,))).verdict is SandboxVerdict.FAIL


def test_egress_allowlist_rejects_privileged_and_nonpublic_targets() -> None:
    for host in ("localhost", "127.0.0.1", "10.0.0.1", "169.254.169.254", "::1"):
        csp_host = host if ":" not in host else "localhost"
        result = evaluate_generated_sandbox(replace(_evidence(), allowed_egress_hosts=(host,), resolved_egress=((host, "93.184.216.34"),), csp=f"default-src 'none'; script-src 'self'; connect-src {csp_host}; object-src 'none'; base-uri 'none'"))
        assert result.verdict is SandboxVerdict.FAIL


def test_csp_rejects_privileged_nonpublic_connect_target() -> None:
    result = evaluate_generated_sandbox(replace(_evidence(), allowed_egress_hosts=("127.0.0.1",), resolved_egress=(("127.0.0.1", "127.0.0.1"),), csp="default-src 'none'; script-src 'self'; connect-src 127.0.0.1; object-src 'none'; base-uri 'none'"))
    assert result.verdict is SandboxVerdict.FAIL


def test_missing_resolved_egress_is_not_verified() -> None:
    assert evaluate_generated_sandbox(replace(_evidence(), resolved_egress=())).verdict is SandboxVerdict.NOT_VERIFIED


def test_each_allowed_host_requires_resolution_evidence() -> None:
    result = evaluate_generated_sandbox(replace(_evidence(), allowed_egress_hosts=("api.example.com", "cdn.example.com")))
    assert result.verdict is SandboxVerdict.NOT_VERIFIED


def test_dns_snapshot_must_be_complete_and_fresh() -> None:
    assert evaluate_generated_sandbox(replace(_evidence(), dns_snapshot_complete=False)).verdict is SandboxVerdict.NOT_VERIFIED
    assert evaluate_generated_sandbox(replace(_evidence(), dns_snapshot_age_seconds=None)).verdict is SandboxVerdict.NOT_VERIFIED
    assert evaluate_generated_sandbox(replace(_evidence(), dns_snapshot_age_seconds=301)).verdict is SandboxVerdict.NOT_VERIFIED


def test_dns_snapshot_rejects_invalid_negative_age() -> None:
    assert evaluate_generated_sandbox(replace(_evidence(), dns_snapshot_age_seconds=-1)).verdict is SandboxVerdict.FAIL


def test_dns_rebinding_to_nonpublic_ip_fails_closed() -> None:
    for target in ("127.0.0.1", "10.10.0.5", "169.254.169.254", "::1"):
        assert evaluate_generated_sandbox(replace(_evidence(), resolved_egress=(("api.example.com", target),))).verdict is SandboxVerdict.FAIL


def test_resolved_egress_cannot_introduce_unapproved_host() -> None:
    result = evaluate_generated_sandbox(replace(_evidence(), resolved_egress=(("api.example.com", "93.184.216.34"), ("evil.example", "93.184.216.35"))))
    assert result.verdict is SandboxVerdict.FAIL


def test_invalid_resolved_ip_fails_closed() -> None:
    assert evaluate_generated_sandbox(replace(_evidence(), resolved_egress=(("api.example.com", "not-an-ip"),))).verdict is SandboxVerdict.FAIL


def test_cross_sha_or_malformed_digest_evidence_fails() -> None:
    assert evaluate_generated_sandbox(replace(_evidence(), source_sha256="not-a-sha", artifact_sha256="z" * 64)).verdict is SandboxVerdict.FAIL


def test_nonpositive_resource_limits_fail() -> None:
    result = evaluate_generated_sandbox(replace(_evidence(), wall_clock_timeout_seconds=0, memory_limit_mb=-1, cpu_limit_millis=0))
    assert result.verdict is SandboxVerdict.FAIL
