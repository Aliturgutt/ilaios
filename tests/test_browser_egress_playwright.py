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


def _boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> PlaywrightDockerBrowserEgressBoundary:
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


def test_browser_container_gets_pinned_seccomp_and_only_sys_chroot(
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
    assert hardened[:5] == (
        "run",
        "-d",
        "--security-opt",
        f"seccomp={boundary._seccomp_profile}",
        "--cap-add=SYS_CHROOT",
    )
    assert hardened.count("--cap-add=SYS_CHROOT") == 1
    assert "--cap-drop=ALL" in hardened
    assert "--security-opt=no-new-privileges" in hardened
    assert "--privileged" not in hardened
    assert "--security-opt=seccomp=unconfined" not in hardened
    assert "--cap-add=SYS_ADMIN" not in hardened
    assert "--cap-add=NET_ADMIN" not in hardened
    assert "--cap-add=SYS_PTRACE" not in hardened


def test_proxy_container_does_not_receive_browser_seccomp_or_capability(
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
    assert "--cap-add=SYS_CHROOT" not in args


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
                "--cap-drop=ALL",
                "--privileged",
                "image-id",
            )
        )


def _assert_broad_capability_rejected(
    boundary: PlaywrightDockerBrowserEgressBoundary,
    forbidden_capability: str,
) -> None:
    with pytest.raises(BrowserToolError, match="weaken container isolation"):
        boundary._inject_browser_seccomp(
            (
                "run",
                "-d",
                "--name",
                boundary._browser_name,
                "--cap-drop=ALL",
                forbidden_capability,
                "image-id",
            )
        )


def test_hardening_rejects_sys_admin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_broad_capability_rejected(
        _boundary(tmp_path, monkeypatch), "--cap-add=SYS_ADMIN"
    )


def test_hardening_rejects_net_admin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_broad_capability_rejected(
        _boundary(tmp_path, monkeypatch), "--cap-add=NET_ADMIN"
    )


def test_hardening_rejects_sys_ptrace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_broad_capability_rejected(
        _boundary(tmp_path, monkeypatch), "--cap-add=SYS_PTRACE"
    )


def test_hardening_requires_ambient_capability_drop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary = _boundary(tmp_path, monkeypatch)
    with pytest.raises(BrowserToolError, match="drop ambient"):
        boundary._inject_browser_seccomp(
            (
                "run",
                "-d",
                "--name",
                boundary._browser_name,
                "image-id",
            )
        )
