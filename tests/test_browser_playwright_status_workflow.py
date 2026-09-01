from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "browser-skill-playwright-e2e.yml"
)


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_browser_e2e_status_uses_exact_source_sha_and_minimal_write_scope() -> None:
    text = _text()
    assert "contents: read" in text
    assert "statuses: write" in text
    assert "contents: write" not in text
    assert "pull-requests: write" not in text
    assert "SOURCE_SHA: ${{ github.event.pull_request.head.sha || github.sha }}" in text
    assert "BrowserQA source SHA is malformed" in text


def test_browser_e2e_status_is_fail_closed_and_auditable() -> None:
    text = _text()
    assert '"context": "ilaios/browser-playwright-e2e"' in text
    assert 'accepted = os.environ.get("JOB_STATUS") == "success"' in text
    assert '"state": "success" if accepted else "failure"' in text
    assert "Governed BrowserQA real Playwright E2E PASS" in text
    assert "Governed BrowserQA real Playwright E2E failed closed" in text
    assert '"target_url": os.environ["TARGET_URL"]' in text
    assert "assert response.status == 201" in text
