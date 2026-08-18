"""Hardened Playwright-specific Docker egress boundary.

The generic Docker BrowserEgressBoundary owns network isolation and evidence. This
adapter adds the upstream Playwright seccomp profile required for Chromium's Linux
user-namespace sandbox. The profile is never fetched implicitly at runtime: callers
must provision the pinned file, and its Git blob hash is verified before any Docker
command can run.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from services.runtime.browser_egress_docker import DockerBrowserEgressBoundary
from services.runtime.browser_tool_adapter import BrowserToolError

PLAYWRIGHT_SECCOMP_SOURCE_COMMIT = "5f8e7eac83052e2602faec430adf54dd55d63611"
PLAYWRIGHT_SECCOMP_GIT_BLOB_SHA1 = "fddc05fb520affb145404e6f6f647ca96af8087d"


class PlaywrightDockerBrowserEgressBoundary(DockerBrowserEgressBoundary):
    """Docker boundary that preserves Chromium sandboxing with pinned seccomp."""

    def __init__(
        self,
        *,
        runtime_image: str,
        proxy_script: Path,
        seccomp_profile: Path,
        docker_executable: str = "docker",
        proxy_port: int = 18080,
    ) -> None:
        profile = seccomp_profile.resolve()
        if not profile.is_file():
            raise BrowserToolError("Playwright seccomp profile is unavailable")
        if _git_blob_sha1(profile) != PLAYWRIGHT_SECCOMP_GIT_BLOB_SHA1:
            raise BrowserToolError("Playwright seccomp profile provenance mismatch")
        self._seccomp_profile = profile
        super().__init__(
            runtime_image=runtime_image,
            proxy_script=proxy_script,
            docker_executable=docker_executable,
            proxy_port=proxy_port,
        )

    def _docker_run(
        self, args: tuple[str, ...], *, timeout_seconds: int
    ) -> subprocess.CompletedProcess[str]:
        return super()._docker_run(
            self._inject_browser_seccomp(args),
            timeout_seconds=timeout_seconds,
        )

    def _inject_browser_seccomp(self, args: tuple[str, ...]) -> tuple[str, ...]:
        if args[:2] != ("run", "-d") or "--name" not in args:
            return args
        name_index = args.index("--name") + 1
        if name_index >= len(args) or args[name_index] != self._browser_name:
            return args
        if any(arg == "--privileged" or arg == "--security-opt=seccomp=unconfined" for arg in args):
            raise BrowserToolError("browser runtime attempted to weaken container isolation")
        return (
            args[:2]
            + ("--security-opt", f"seccomp={self._seccomp_profile}")
            + args[2:]
        )


def _git_blob_sha1(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()
