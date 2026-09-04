from __future__ import annotations

from services.web_app_generated_security_gate import evaluate_generated_web_product


_SAFE_CSP = "default-src 'self'; script-src 'self'; connect-src 'self' https://api.example.com; object-src 'none'; base-uri 'none'"
_SSRF_SOURCES = (
    'axios.get("http://127.0.0.1:8080/admin")',
    'axios.post("http://localhost/internal")',
    'requests.get("http://169.254.169.254/latest/meta-data")',
    'fetch("http://metadata.google.internal/computeMetadata/v1/")',
    'fetch("http://[::1]/admin")',
    'fetch("file:///etc/passwd")',
)


def test_generated_web_gate_blocks_loopback_metadata_and_file_fetches() -> None:
    for source in _SSRF_SOURCES:
        result = evaluate_generated_web_product(
            {"app/page.tsx": source},
            content_security_policy=_SAFE_CSP,
        )

        assert result.verdict == "FAIL", source
        assert any(
            finding.category == "ssrf" and finding.rule == "metadata-or-loopback-fetch"
            for finding in result.findings
        ), source


def test_generated_web_gate_does_not_misclassify_allowlisted_public_api_fetch_as_ssrf() -> None:
    result = evaluate_generated_web_product(
        {"app/page.tsx": 'fetch("https://api.example.com/v1/status")'},
        content_security_policy=_SAFE_CSP,
    )

    assert result.verdict == "PASS"
    assert not any(finding.category == "ssrf" for finding in result.findings)
