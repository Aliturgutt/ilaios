from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Mapping

GeneratedSecurityVerdict = Literal["PASS", "FAIL", "NOT_VERIFIED"]


@dataclass(frozen=True)
class GeneratedSecurityFinding:
    category: str
    path: str
    rule: str


@dataclass(frozen=True)
class GeneratedSecurityResult:
    verdict: GeneratedSecurityVerdict
    findings: tuple[GeneratedSecurityFinding, ...]


_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai-api-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("bearer-token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}\b", re.IGNORECASE)),
)

_CODE_RULES: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("xss", "dangerous-dom-html", re.compile(r"\b(?:innerHTML|outerHTML|srcdoc)\s*=|dangerouslySetInnerHTML|document\.write\s*\(|insertAdjacentHTML\s*\(")),
    ("script-injection", "dynamic-code-execution", re.compile(r"\b(?:eval|Function)\s*\(|\b(?:setTimeout|setInterval)\s*\(\s*[\"']", re.IGNORECASE)),
    ("script-injection", "javascript-url-execution", re.compile(r"(?:href|src|action)\s*=\s*[\"']\s*javascript\s*:|[\"']javascript\s*:", re.IGNORECASE)),
    ("remote-script", "remote-script-source", re.compile(r"<script[^>]+src\s*=\s*[\"'](?:https?:)?//|\bimport\s*\([^)]*[\"'](?:https?:)?//", re.IGNORECASE)),
    ("ssrf", "metadata-or-loopback-fetch", re.compile(r"(?:fetch|axios\.(?:get|post)|requests?\.get)\s*\([^\n]*(?:169\.254\.169\.254|metadata\.google\.internal|127\.0\.0\.1|\[?::1\]?|localhost|0\.0\.0\.0|file://)", re.IGNORECASE)),
    ("open-redirect", "unvalidated-location-assignment", re.compile(r"(?:(?:window\.)?location(?:\.href)?\s*=|(?:window\.)?location\.(?:assign|replace)\s*\()\s*(?:new\s+URLSearchParams|searchParams|getQuery|query\b|params\b)", re.IGNORECASE)),
    ("client-token-leak", "browser-storage-secret", re.compile(r"(?:(?:localStorage|sessionStorage|indexedDB)[^\n]{0,120}|document\.cookie\s*=[^\n]{0,120})(?:token|secret|credential|session)", re.IGNORECASE)),
    ("unsafe-template", "unsafe-html-template", re.compile(r"\|\s*safe\b|\bMarkup\s*\(|\bv-html\s*=", re.IGNORECASE)),
    ("path-file", "archive-or-path-traversal", re.compile(r"(?:extract|writeFile|open|Path|join)[^\n]{0,160}(?:\.\./|\.\.\\\\)", re.IGNORECASE)),
    ("path-file", "unsafe-symlink-creation", re.compile(r"\b(?:os\.symlink|fs\.symlink|symlinkSync)\s*\(", re.IGNORECASE)),
    ("tenant-escape", "caller-controlled-tenant-authority", re.compile(r"tenant[_-]?id\s*=\s*(?:req\.(?:query|params)|request\.(?:query|args)|searchParams)", re.IGNORECASE)),
    ("privileged-semantics", "governance-bypass-marker", re.compile(r"(?:BYPASS|DISABLE|SKIP)[_-]?(?:POLICY|APPROVAL|TOOL_GATEWAY|EVIDENCE|TENANT|AUTH)", re.IGNORECASE)),
)


def evaluate_generated_web_product(files: Mapping[str, str], *, content_security_policy: str | None) -> GeneratedSecurityResult:
    """Fail-closed static acceptance gate for untrusted generated/revised Web products."""
    if not files:
        return GeneratedSecurityResult(verdict="NOT_VERIFIED", findings=())

    findings: list[GeneratedSecurityFinding] = []
    for path, source in sorted(files.items()):
        normalized_path = path.replace("\\", "/")
        if normalized_path.startswith("/") or "/../" in f"/{normalized_path}/" or normalized_path.startswith("../"):
            findings.append(GeneratedSecurityFinding("path-file", normalized_path, "unsafe-output-path"))
        for category, rule, pattern in _CODE_RULES:
            if pattern.search(source):
                findings.append(GeneratedSecurityFinding(category, normalized_path, rule))
        for rule, pattern in _SECRET_PATTERNS:
            if pattern.search(source):
                findings.append(GeneratedSecurityFinding("secret-leak", normalized_path, rule))
        lowered = source.lower()
        if ("preinstall" in lowered or "postinstall" in lowered or "prepare" in lowered) and normalized_path.endswith("package.json"):
            findings.append(GeneratedSecurityFinding("malicious-dependency", normalized_path, "package-install-hook-present"))

    findings.extend(_validate_csp(content_security_policy))
    return GeneratedSecurityResult(verdict="FAIL" if findings else "PASS", findings=tuple(findings))


def _validate_csp(content_security_policy: str | None) -> list[GeneratedSecurityFinding]:
    if content_security_policy is None or not content_security_policy.strip():
        return [GeneratedSecurityFinding("csp", "<headers>", "missing-content-security-policy")]
    directives: dict[str, tuple[str, ...]] = {}
    for raw_directive in content_security_policy.split(";"):
        parts = raw_directive.strip().split()
        if parts:
            directives[parts[0].lower()] = tuple(part.lower() for part in parts[1:])
    findings: list[GeneratedSecurityFinding] = []
    default_src = directives.get("default-src")
    script_src = directives.get("script-src", default_src)
    connect_src = directives.get("connect-src", default_src)
    object_src = directives.get("object-src")
    base_uri = directives.get("base-uri")
    if default_src is None or "'self'" not in default_src:
        findings.append(GeneratedSecurityFinding("csp", "<headers>", "default-src-self-required"))
    if script_src is None:
        findings.append(GeneratedSecurityFinding("csp", "<headers>", "script-src-required"))
    else:
        if "*" in script_src or "'unsafe-eval'" in script_src or "'unsafe-inline'" in script_src:
            findings.append(GeneratedSecurityFinding("csp", "<headers>", "unsafe-script-src"))
        if any(value.startswith("http://") for value in script_src):
            findings.append(GeneratedSecurityFinding("csp", "<headers>", "insecure-script-origin"))
    if connect_src is None:
        findings.append(GeneratedSecurityFinding("csp", "<headers>", "connect-src-required"))
    elif "*" in connect_src:
        findings.append(GeneratedSecurityFinding("csp", "<headers>", "unbounded-connect-src"))
    if object_src != ("'none'",):
        findings.append(GeneratedSecurityFinding("csp", "<headers>", "object-src-none-required"))
    if base_uri is None or not ({"'none'", "'self'"} & set(base_uri)):
        findings.append(GeneratedSecurityFinding("csp", "<headers>", "base-uri-restriction-required"))
    return findings
