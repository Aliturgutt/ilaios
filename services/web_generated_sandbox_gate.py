"""Evidence-only acceptance gate for the generated Web App sandbox contract.

This module does not execute generated code and does not create a second runtime or
security authority. It validates evidence emitted by the canonical governed runtime.
"""

from __future__ import annotations

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

    csp = _normalize_csp(evidence.csp)
    for required in ("default-src", "script-src", "connect-src", "object-src", "base-uri"):
        if required not in csp:
            failures.append(f"CSP is missing {required}")
    if csp.get("object-src") != ("'none'",):
        failures.append("CSP object-src must be 'none'")
    if csp.get("base-uri") != ("'none'",):
        failures.append("CSP base-uri must be 'none'")
    if "*" in csp.get("connect-src", ()):
        failures.append("CSP connect-src cannot allow wildcard egress")

    if not evidence.allowed_egress_hosts:
        failures.append("controlled egress allowlist evidence is empty")
    if any(not _valid_host(host) for host in evidence.allowed_egress_hosts):
        failures.append("egress allowlist contains an invalid or wildcard host")

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

    if missing:
        return SandboxGateResult(
            SandboxVerdict.NOT_VERIFIED,
            tuple(sorted(set(f"missing evidence: {item}" for item in missing))),
        )
    if failures:
        return SandboxGateResult(SandboxVerdict.FAIL, tuple(sorted(set(failures))))
    return SandboxGateResult(SandboxVerdict.PASS, ())


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


def _valid_host(value: str) -> bool:
    host = value.strip().casefold()
    if not host or "*" in host or "://" in host or "/" in host:
        return False
    return all(part and part.replace("-", "").isalnum() for part in host.split("."))


def _is_hex(value: str) -> bool:
    return all(character in "0123456789abcdefABCDEF" for character in value)
