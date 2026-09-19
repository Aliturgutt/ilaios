from __future__ import annotations

from pathlib import Path

from services.github_workflow_security_audit import audit_repository


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_p0_live_workflow_publishes_only_sanitized_exact_sha_status() -> None:
    root = _repository_root()
    path = root / ".github" / "workflows" / "agent-p0-live-certification.yml"
    text = path.read_text(encoding="utf-8")

    assert "  contents: read\n  statuses: write\n" in text
    assert "pull_request:" not in text
    assert "environment: Production" in text
    assert "ref: ${{ github.sha }}" in text
    assert "receipt['revision_sha'] == os.environ['GITHUB_SHA']" in text
    assert "ILAIOS Agent P0 Live Certification" in text
    assert "P0 live receipt accepted: 21/21 VERIFIED" in text
    assert "P0 live certification failed closed" in text
    assert "P0_COMMIT_STATUS=" in text
    assert "/statuses/{os.environ['GITHUB_SHA']}" in text
    assert "contents: write" not in text


def test_p0_live_status_workflow_preserves_repository_security_policy() -> None:
    root = _repository_root()
    findings = [
        finding
        for finding in audit_repository(root)
        if finding.path == ".github/workflows/agent-p0-live-certification.yml"
    ]
    assert findings == []
