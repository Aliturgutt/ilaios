from __future__ import annotations

from pathlib import Path

import pytest

import services.runtime.browser_egress_playwright as playwright_egress
from services.runtime.browser_egress_playwright import (
    PLAYWRIGHT_SECCOMP_GIT_BLOB_SHA1,
    PlaywrightDockerBrowserEgressBoundary,
)
from services.runtime.browser_tool_adapter import BrowserToolError


def _file(path: Path, content: str = "x") -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> PlaywrightDockerBrowserEgressBoundary:
    proxy = _file(tmp_path / "proxy.py")
    profile = _file(tmp_path / "seccomp.json", "{}")
    monkeypatch.setattr(
        playwright_egress,
        "_git_blob_sha1",
        lambda _path: PLAYWRIGHT_SECCOMP_GIT_BLOB_SHA1,
    )
    return PlaywrightDockerBrowserEgressBoundary(
        runtime_image="ilaios-browser:test",
        proxy_script=proxy,
        seccomp_profile=profile,
    )


def test_seccomp_profile_provenance_mismatch_fails_closed(
    tmp_path: Path,
) -> None:
    proxy = _file(tmp_path / "proxy.py")
    profile = _file(tmp_path / "seccomp.json", "{}")
    with pytest.raises(BrowserToolError, match="provenance mismatch"):
        PlaywrightDockerBrowserEgressBoundary(
            runtime_image="ilaios-browser:test",
            proxy_script=proxy,
            seccomp_profile=profile,
        )


def test_browser_container_gets_only_pinned_seccomp_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary = _boundary(tmp_path, monkeypatch)
    args = (
        "run",
        "-d",
        "--name",
        boundary._browser_name,
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "image-id",
        "sleep",
        "infinity",
    )
    hardened = boundary._inject_browser_seccomp(args)
    assert hardened[:4] == (
        "run",
        "-d",
        "--security-opt",
        f"seccomp={boundary._seccomp_profile}",
    )
    assert "--cap-drop=ALL" in hardened
    assert "--security-opt=no-new-privileges" in hardened
    assert "--privileged" not in hardened
    assert "--security-opt=seccomp=unconfined" not in hardened


def test_proxy_container_does_not_receive_browser_seccomp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary = _boundary(tmp_path, monkeypatch)
    args = (
        "run",
        "-d",
        "--name",
        boundary._proxy_name,
        "image-id",
        "python3",
        "proxy.py",
    )
    assert boundary._inject_browser_seccomp(args) == args


def test_hardening_rejects_privileged_browser_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary = _boundary(tmp_path, monkeypatch)
    with pytest.raises(BrowserToolError, match="weaken container isolation"):
        boundary._inject_browser_seccomp(
            (
                "run",
                "-d",
                "--name",
                boundary._browser_name,
                "--privileged",
                "image-id",
            )
        )
