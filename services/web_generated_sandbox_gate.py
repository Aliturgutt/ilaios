"""Evidence-only acceptance gate for the generated Web App sandbox contract.

This module does not execute generated code and does not create a second runtime or
security authority. It validates evidence emitted by the canonical governed runtime.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from enum import StrEnum


class SandboxVerdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_VERIFIED = "NOT_VERIFIED"


@dataclass(frozen=True, slots=True)
class GeneratedSandboxEvidence:
    execution_id: str
    tenant_id: str
    source_sha256: str
    artifact_sha256: str
    separate_origin: bool
    strong_process_sandbox: bool
    csp: str
    allowed_egress_hosts: tuple[str, ...]
    resolved_egress: tuple[tuple[str, str], ...]
    privileged_cookie_access: bool
    privileged_token_access: bool
    secret_material_access: bool
    host_shell_access: bool
    docker_socket_access: bool
    control_plane_db_access: bool
    unrestricted_filesystem_access: bool
    unrestricted_network_access: bool
    signing_material_access: bool
    package_install_scripts_disabled: bool
    canonical_policy_secure_mode: bool
    canonical_policy_network_allowed: bool
    canonical_policy_secrets_allowed: bool
    canonical_policy_timeout_seconds: int | None
    controlled_egress_gateway: bool
    wall_clock_timeout_seconds: int | None
    memory_limit_mb: int | None
    cpu_limit_millis: int | None


@dataclass(frozen=True, slots=True)
class SandboxGateResult:
    verdict: SandboxVerdict
    reasons: tuple[str, ...]


def evaluate_generated_sandbox(evidence: GeneratedSandboxEvidence) -> SandboxGateResult:
    missing: list[str] = []
    failures: list[str] = []

    for field_name, value in (
        ("execution_id", evidence.execution_id),
        ("tenant_id", evidence.tenant_id),
        ("source_sha256", evidence.source_sha256),
        ("artifact_sha256", evidence.artifact_sha256),
        ("csp", evidence.csp),
    ):
        if not value.strip():
            missing.append(field_name)

    if len(evidence.source_sha256) != 64 or not _is_hex(evidence.source_sha256):
        failures.append("source_sha256 must be an exact SHA-256 hex digest")
    if len(evidence.artifact_sha256) != 64 or not _is_hex(evidence.artifact_sha256):
        failures.append("artifact_sha256 must be an exact SHA-256 hex digest")

    if not (evidence.separate_origin or evidence.strong_process_sandbox):
        failures.append("no separate-origin or equivalently strong process sandbox evidence")

    if not evidence.canonical_policy_secure_mode:
        failures.append("canonical execution policy is not in secure mode")
    if evidence.canonical_policy_network_allowed:
        failures.append("canonical execution policy grants direct network authority")
    if evidence.canonical_policy_secrets_allowed:
        failures.append("canonical execution policy grants secret authority")
    if not evidence.controlled_egress_gateway:
        failures.append("controlled egress is not proven to use the governed gateway boundary")
    _check_positive_bound(
        "canonical policy timeout",
        evidence.canonical_policy_timeout_seconds,
        missing,
        failures,
    )

    csp = _normalize_csp(evidence.csp)
    duplicate_directives = _duplicate_csp_directives(evidence.csp)
    if duplicate_directives:
        failures.append("CSP contains duplicate directives")
    for required in ("default-src", "script-src", "connect-src", "object-src", "base-uri"):
        if required not in csp:
            failures.append(f"CSP is missing {required}")
    if csp.get("default-src") != ("'none'",):
        failures.append("CSP default-src must be 'none'")
    if not _strict_script_sources(csp.get("script-src", ())):
        failures.append("CSP script-src permits unsafe or remote script execution")
    if csp.get("object-src") != ("'none'",):
        failures.append("CSP object-src must be 'none'")
    if csp.get("base-uri") != ("'none'",):
        failures.append("CSP base-uri must be 'none'")

    normalized_egress_hosts = tuple(host.strip().casefold() for host in evidence.allowed_egress_hosts)
    if not normalized_egress_hosts:
        failures.append("controlled egress allowlist evidence is empty")
    if any(not _valid_host(host) for host in normalized_egress_hosts):
        failures.append("egress allowlist contains an invalid or wildcard host")
    if any(_privileged_egress_target(host) for host in normalized_egress_hosts):
        failures.append("egress allowlist contains a privileged or non-public target")

    _validate_resolved_egress(
        normalized_egress_hosts,
        evidence.resolved_egress,
        missing,
        failures,
    )

    connect_sources = csp.get("connect-src", ())
    if "*" in connect_sources:
        failures.append("CSP connect-src cannot allow wildcard egress")
    if any(not _valid_host(source) for source in connect_sources):
        failures.append("CSP connect-src contains a non-host or unsafe source")
    if any(_privileged_egress_target(source) for source in connect_sources):
        failures.append("CSP connect-src contains a privileged or non-public target")
    if any(source.casefold() not in normalized_egress_hosts for source in connect_sources):
        failures.append("CSP connect-src exceeds the controlled egress allowlist")

    forbidden_capabilities = {
        "privileged cookie": evidence.privileged_cookie_access,
        "privileged token": evidence.privileged_token_access,
        "secret material": evidence.secret_material_access,
        "host shell": evidence.host_shell_access,
        "Docker socket": evidence.docker_socket_access,
        "control-plane DB": evidence.control_plane_db_access,
        "unrestricted filesystem": evidence.unrestricted_filesystem_access,
        "unrestricted network": evidence.unrestricted_network_access,
        "signing material": evidence.signing_material_access,
    }
    for capability, exposed in forbidden_capabilities.items():
        if exposed:
            failures.append(f"generated runtime exposes forbidden capability: {capability}")

    if not evidence.package_install_scripts_disabled:
        failures.append("package lifecycle scripts are not proven disabled")

    _check_positive_bound(
        "wall clock timeout",
        evidence.wall_clock_timeout_seconds,
        missing,
        failures,
    )
    _check_positive_bound("memory limit", evidence.memory_limit_mb, missing, failures)
    _check_positive_bound("CPU limit", evidence.cpu_limit_millis, missing, failures)
    if (
        evidence.canonical_policy_timeout_seconds is not None
        and evidence.wall_clock_timeout_seconds is not None
        and evidence.canonical_policy_timeout_seconds > 0
        and evidence.wall_clock_timeout_seconds > evidence.canonical_policy_timeout_seconds
    ):
        failures.append("sandbox wall clock timeout exceeds canonical execution policy")

    if failures:
        return SandboxGateResult(SandboxVerdict.FAIL, tuple(sorted(set(failures))))
    if missing:
        return SandboxGateResult(
            SandboxVerdict.NOT_VERIFIED,
            tuple(sorted(set(f"missing evidence: {item}" for item in missing))),
        )
    return SandboxGateResult(SandboxVerdict.PASS, ())


def _validate_resolved_egress(
    allowed_hosts: tuple[str, ...],
    resolved_egress: tuple[tuple[str, str], ...],
    missing: list[str],
    failures: list[str],
) -> None:
    if not resolved_egress:
        missing.append("resolved egress")
        return

    allowed = set(allowed_hosts)
    resolved_hosts: set[str] = set()
    for raw_host, raw_ip in resolved_egress:
        host = raw_host.strip().casefold()
        ip = raw_ip.strip()
        if host not in allowed:
            failures.append("resolved egress contains a host outside the controlled allowlist")
            continue
        resolved_hosts.add(host)
        try:
            address = ipaddress.ip_address(ip)
        except ValueError:
            failures.append("resolved egress contains an invalid IP address")
            continue
        if not address.is_global:
            failures.append("resolved egress maps an allowed host to a privileged or non-public IP")

    for host in allowed:
        if host not in resolved_hosts:
            missing.append(f"resolved egress for {host}")


def _check_positive_bound(
    label: str,
    value: int | None,
    missing: list[str],
    failures: list[str],
) -> None:
    if value is None:
        missing.append(label)
    elif value <= 0:
        failures.append(f"{label} must be a positive enforced bound")


def _normalize_csp(value: str) -> dict[str, tuple[str, ...]]:
    directives: dict[str, tuple[str, ...]] = {}
    for segment in value.split(";"):
        tokens = tuple(token for token in segment.strip().split() if token)
        if not tokens:
            continue
        directives[tokens[0].casefold()] = tokens[1:]
    return directives


def _duplicate_csp_directives(value: str) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for segment in value.split(";"):
        tokens = tuple(token for token in segment.strip().split() if token)
        if not tokens:
            continue
        directive = tokens[0].casefold()
        if directive in seen:
            duplicates.add(directive)
        seen.add(directive)
    return duplicates


def _strict_script_sources(sources: tuple[str, ...]) -> bool:
    if not sources:
        return False
    for source in sources:
        normalized = source.casefold()
        if normalized == "'self'":
            continue
        if normalized.startswith("'nonce-") and normalized.endswith("'"):
            continue
        if normalized.startswith(("'sha256-", "'sha384-", "'sha512-")) and normalized.endswith("'"):
            continue
        return False
    return True


def _valid_host(value: str) -> bool:
    host = value.strip().casefold()
    if not host or "*" in host or "://" in host or "/" in host:
        return False
    return all(part and part.replace("-", "").isalnum() for part in host.split("."))


def _privileged_egress_target(value: str) -> bool:
    host = value.strip().casefold().rstrip(".")
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return not address.is_global


def _is_hex(value: str) -> bool:
    return all(character in "0123456789abcdefABCDEF" for character in value)
