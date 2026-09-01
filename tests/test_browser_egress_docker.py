from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from services.runtime.browser_egress_docker import (
    DockerBrowserEgressBoundary,
    _canonical_origins,
)
from services.runtime.browser_tool_adapter import BrowserToolError

_IMAGE_ID = "sha256:" + ("a" * 64)
_SESSION = "-s=ilaios-0123456789abcdef01234567"


class _FakeDockerBoundary(DockerBrowserEgressBoundary):
    def __init__(self, proxy_script: Path, *, version: str = "28.3.1") -> None:
        super().__init__(
            runtime_image="ilaios-browser-e2e:test",
            proxy_script=proxy_script,
        )
        self.version = version
        self.calls: list[tuple[str, ...]] = []

    def _docker_run(
        self, args: tuple[str, ...], *, timeout_seconds: int
    ) -> subprocess.CompletedProcess[str]:
        del timeout_seconds
        self.calls.append(args)
        if args[:2] == ("version", "--format"):
            return _completed(args, self.version + "\n")
        if args[:2] == ("info", "--format"):
            return _completed(args, "linux\n")
        if args[:3] == ("image", "inspect", "--format"):
            return _completed(args, _IMAGE_ID + "\n")
        if args[:2] == ("network", "create"):
            return _completed(args, "network-id\n")
        if args[:2] == ("network", "inspect"):
            return _completed(
                args,
                json.dumps(
                    [
                        {
                            "Internal": True,
                            "Options": {
                                "com.docker.network.bridge.gateway_mode_ipv4": "isolated"
                            },
                        }
                    ]
                ),
            )
        if args[:2] == ("network", "connect"):
            return _completed(args, "")
        if args[0] == "inspect":
            container = args[1]
            networks: dict[str, dict[str, str]]
            if "proxy" in container:
                networks = {
                    "bridge": {"IPAddress": "172.17.0.2"},
                    self._network_name: {"IPAddress": "172.30.0.2"},
                }
            else:
                networks = {self._network_name: {"IPAddress": "172.30.0.3"}}
            return _completed(
                args,
                json.dumps([{"NetworkSettings": {"Networks": networks}}]),
            )
        if args[:2] == ("run", "-d"):
            name_index = args.index("--name") + 1
            name = args[name_index]
            return _completed(args, f"{name}-id\n")
        if args[0] == "exec":
            return _completed(
                args,
                "### Page\n- Page URL: https://example.com/\n",
            )
        if args[:2] == ("rm", "-f") or args[:2] == ("network", "rm"):
            return _completed(args, "")
        raise AssertionError(f"unexpected Docker invocation: {args!r}")


def _completed(
    args: tuple[str, ...], stdout: str, stderr: str = "", returncode: int = 0
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


def _proxy_script(tmp_path: Path) -> Path:
    path = tmp_path / "allowlist_proxy.py"
    path.write_text("print('proxy')\n", encoding="utf-8")
    return path


def test_docker_boundary_builds_isolated_single_homed_browser(tmp_path: Path) -> None:
    boundary = _FakeDockerBoundary(_proxy_script(tmp_path))
    evidence = tmp_path / "evidence"
    result = boundary.run(
        allowed_origins=("https://example.com",),
        argv=("playwright-cli", _SESSION, "open", "https://example.com"),
        cwd=evidence,
        timeout_seconds=30,
    )
    assert result.returncode == 0
    assert result.boundary_evidence_id.startswith("sha256:")

    create = next(
        call for call in boundary.calls if call[:2] == ("network", "create")
    )
    assert "--internal" in create
    isolated_index = create.index(
        "com.docker.network.bridge.gateway_mode_ipv4=isolated"
    )
    assert isolated_index > create.index("--internal")

    browser_run = next(
        call
        for call in boundary.calls
        if call[:2] == ("run", "-d") and boundary._browser_name in call
    )
    assert browser_run[browser_run.index("--network") + 1] == boundary._network_name
    assert "--network=host" not in browser_run
    assert "-p" not in browser_run
    assert "--publish" not in browser_run
    assert "--dns=127.0.0.1" in browser_run
    assert "--cap-drop=ALL" in browser_run
    assert "--security-opt=no-new-privileges" in browser_run

    config = json.loads(
        next(evidence.glob(".ilaios-browser-egress-*.json")).read_text(
            encoding="utf-8"
        )
    )
    assert config["browser"]["contextOptions"]["javaScriptEnabled"] is False
    assert config["browser"]["contextOptions"]["serviceWorkers"] == "block"
    assert config["browser"]["launchOptions"]["chromiumSandbox"] is True
    assert config["network"]["allowedOrigins"] == ["https://example.com"]

    receipts = list((evidence / "browser-egress-evidence").glob("*.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert receipt["network_internal"] is True
    assert receipt["gateway_mode_ipv4"] == "isolated"
    assert receipt["runtime_image_id"] == _IMAGE_ID
    boundary.shutdown()


def test_isolation_probe_requires_public_ip_block(tmp_path: Path) -> None:
    boundary = _FakeDockerBoundary(_proxy_script(tmp_path))
    evidence = tmp_path / "evidence"
    boundary.run(
        allowed_origins=("https://example.com",),
        argv=("playwright-cli", _SESSION, "open", "https://example.com"),
        cwd=evidence,
        timeout_seconds=30,
    )
    receipt = boundary.verify_isolation(cwd=evidence)
    assert receipt.startswith("sha256:")
    assert any(
        call[0] == "exec" and "proxy-reachable/public-egress-blocked" not in call
        for call in boundary.calls
    )
    boundary.shutdown()


def test_boundary_rejects_unpinned_execution_surface(tmp_path: Path) -> None:
    boundary = _FakeDockerBoundary(_proxy_script(tmp_path))
    with pytest.raises(BrowserToolError, match="only the pinned Playwright CLI"):
        boundary.run(
            allowed_origins=("https://example.com",),
            argv=("bash", _SESSION, "-c", "true"),
            cwd=tmp_path / "evidence",
            timeout_seconds=30,
        )
    assert not boundary.calls


def test_boundary_requires_docker_28_isolated_gateway_mode(tmp_path: Path) -> None:
    boundary = _FakeDockerBoundary(_proxy_script(tmp_path), version="27.5.1")
    with pytest.raises(BrowserToolError, match="Docker Engine 28"):
        boundary.run(
            allowed_origins=("https://example.com",),
            argv=("playwright-cli", _SESSION, "close"),
            cwd=tmp_path / "evidence",
            timeout_seconds=30,
        )


def test_live_sandbox_rejects_policy_drift(tmp_path: Path) -> None:
    boundary = _FakeDockerBoundary(_proxy_script(tmp_path))
    evidence = tmp_path / "evidence"
    boundary.run(
        allowed_origins=("https://example.com",),
        argv=("playwright-cli", _SESSION, "open", "https://example.com"),
        cwd=evidence,
        timeout_seconds=30,
    )
    with pytest.raises(BrowserToolError, match="policy changed"):
        boundary.run(
            allowed_origins=("https://www.iana.org",),
            argv=("playwright-cli", _SESSION, "goto", "https://www.iana.org"),
            cwd=evidence,
            timeout_seconds=30,
        )
    boundary.shutdown()


def test_origin_policy_is_canonical_and_explicit() -> None:
    assert _canonical_origins(
        ("https://EXAMPLE.com:443", "https://example.com")
    ) == ("https://example.com",)
    with pytest.raises(BrowserToolError, match="explicit origins"):
        _canonical_origins(())
