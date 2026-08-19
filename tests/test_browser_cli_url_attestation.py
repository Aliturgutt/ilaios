from __future__ import annotations

from pathlib import Path

import pytest

from services.runtime.browser_tool_adapter import (
    BrowserProcessResult,
    BrowserToolError,
    PlaywrightCliAdapter,
    browser_session_id,
)


class _ArtifactOnlyScreenshotEgress:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def run(
        self,
        *,
        allowed_origins: tuple[str, ...],
        argv: tuple[str, ...],
        cwd: Path,
        timeout_seconds: int,
    ) -> BrowserProcessResult:
        assert allowed_origins == ("https://example.com",)
        assert timeout_seconds == 60
        self.calls.append(argv)
        for arg in argv:
            if arg.startswith("--filename="):
                path = cwd / arg.split("=", 1)[1]
                if argv[2] == "screenshot":
                    path.write_bytes(b"\x89PNG\r\n\x1a\nreal-pixels")
                else:
                    path.write_text("- document: example\n", encoding="utf-8")
        if argv[2] == "screenshot":
            return BrowserProcessResult(
                0,
                "### Result\n- [Screenshot](./screen.png)\n",
                "",
                "sha256:screenshot-boundary",
            )
        if argv[2] == "snapshot":
            return BrowserProcessResult(
                0,
                "### Page\n- Page URL: https://example.com/\n- Page Title: Example Domain\n",
                "",
                "sha256:attestation-boundary",
            )
        raise AssertionError(f"unexpected command: {argv!r}")


def test_screenshot_without_page_url_is_attested_in_same_session(tmp_path: Path) -> None:
    egress = _ArtifactOnlyScreenshotEgress()
    cli = PlaywrightCliAdapter(egress, tmp_path)
    session_id = browser_session_id("u", "t", "w")

    result = cli.execute(
        ("https://example.com",),
        session_id,
        "screenshot",
        None,
    )

    assert result["observed_url"] == "https://example.com/"
    assert result["boundary_evidence_id"] == "sha256:screenshot-boundary"
    assert result["observation_boundary_evidence_id"] == "sha256:attestation-boundary"
    assert isinstance(result["artifact_sha256"], str)
    artifact_size = result["artifact_size"]
    assert isinstance(artifact_size, int)
    assert artifact_size > 0
    assert isinstance(result["observation_artifact_sha256"], str)
    observation_artifact_size = result["observation_artifact_size"]
    assert isinstance(observation_artifact_size, int)
    assert observation_artifact_size > 0
    assert len(egress.calls) == 2
    assert egress.calls[0][1] == egress.calls[1][1] == f"-s={session_id}"
    assert egress.calls[0][2] == "screenshot"
    assert egress.calls[1][2] == "snapshot"


class _MissingUrlAttestationEgress(_ArtifactOnlyScreenshotEgress):
    def run(
        self,
        *,
        allowed_origins: tuple[str, ...],
        argv: tuple[str, ...],
        cwd: Path,
        timeout_seconds: int,
    ) -> BrowserProcessResult:
        result = super().run(
            allowed_origins=allowed_origins,
            argv=argv,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )
        if argv[2] == "snapshot":
            return BrowserProcessResult(
                0,
                "### Snapshot\n- no page url\n",
                "",
                "sha256:attestation-boundary",
            )
        return result


def test_screenshot_fails_closed_when_attestation_still_has_no_url(tmp_path: Path) -> None:
    cli = PlaywrightCliAdapter(_MissingUrlAttestationEgress(), tmp_path)
    with pytest.raises(BrowserToolError, match="attestation returned no Page URL"):
        cli.execute(
            ("https://example.com",),
            browser_session_id("u", "t", "w"),
            "screenshot",
            None,
        )
