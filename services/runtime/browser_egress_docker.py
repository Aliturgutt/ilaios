"""OS-enforced Docker egress boundary for governed BrowserQA execution.

The browser container is attached only to an internal bridge created with Docker's
isolated gateway mode. A separate allowlist proxy container is dual-homed on that
internal network and the normal Docker bridge. The browser receives no Docker
socket, no host network, no published ports, and no usable DNS resolver. External
traffic therefore has one path only: the policy proxy.

This module intentionally stays outside Playwright's own origin filtering. The
Playwright filter remains defense in depth; Docker network isolation is the egress
security boundary.
"""
from __future__ import annotations

import atexit
import hashlib
import json
import os
import re
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from services.runtime.browser_tool_adapter import (
    BrowserProcessResult,
    BrowserToolError,
)

_DOCKER_VERSION_RE = re.compile(r"^(\d+)\.(\d+)(?:\.|$)")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class DockerBrowserEgressBoundary:
    """Concrete BrowserEgressBoundary backed by an isolated Docker topology.

    The supplied runtime image is resolved to its immutable local image ID before
    either container starts. The image must contain ``playwright-cli``, ``python3``
    and the browser binaries expected by that CLI release.
    """

    def __init__(
        self,
        *,
        runtime_image: str,
        proxy_script: Path,
        docker_executable: str = "docker",
        proxy_port: int = 18080,
    ) -> None:
        if not runtime_image.strip() or any(char in runtime_image for char in "\r\n\x00"):
            raise BrowserToolError("browser egress runtime image is invalid")
        if not docker_executable.strip() or any(
            char in docker_executable for char in "\r\n\x00"
        ):
            raise BrowserToolError("browser egress Docker executable is invalid")
        if proxy_port < 1024 or proxy_port > 65535:
            raise BrowserToolError("browser egress proxy port is invalid")
        proxy = proxy_script.resolve()
        if not proxy.is_file():
            raise BrowserToolError("browser egress proxy implementation is unavailable")
        self._runtime_image = runtime_image
        self._proxy_script = proxy
        self._docker = docker_executable
        self._proxy_port = proxy_port
        self._instance = uuid.uuid4().hex[:16]
        self._network_name = f"ilaios-browser-{self._instance}"
        self._proxy_name = f"ilaios-browser-proxy-{self._instance}"
        self._browser_name = f"ilaios-browser-runtime-{self._instance}"
        self._policy: tuple[str, ...] | None = None
        self._policy_sha256: str | None = None
        self._cwd: Path | None = None
        self._image_id: str | None = None
        self._proxy_ip: str | None = None
        self._started = False
        self._lock = threading.RLock()
        atexit.register(self.shutdown)

    def run(
        self,
        *,
        allowed_origins: tuple[str, ...],
        argv: tuple[str, ...],
        cwd: Path,
        timeout_seconds: int,
    ) -> BrowserProcessResult:
        with self._lock:
            if timeout_seconds < 1 or timeout_seconds > 300:
                raise BrowserToolError("browser egress timeout is invalid")
            self._validate_cli_argv(argv)
            policy = _canonical_origins(allowed_origins)
            evidence_root = cwd.resolve()
            evidence_root.mkdir(parents=True, exist_ok=True)
            self._ensure_started(policy, evidence_root, timeout_seconds)
            assert self._proxy_ip is not None
            config_path = self._write_cli_config(evidence_root, self._proxy_ip, policy)
            container_config = f"/evidence/{config_path.name}"
            command = (
                "exec",
                "--env",
                f"PLAYWRIGHT_MCP_CONFIG={container_config}",
                "--env",
                "HOME=/tmp/ilaios-home",
                self._browser_name,
                *argv,
            )
            try:
                completed = self._docker_run(command, timeout_seconds=timeout_seconds)
            except (subprocess.TimeoutExpired, OSError) as error:
                self.shutdown()
                raise BrowserToolError("browser egress execution failed closed") from error
            evidence_id = self._write_receipt(
                evidence_root,
                kind="browser-command",
                argv=argv,
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
            if completed.returncode != 0:
                self.shutdown()
            return BrowserProcessResult(
                completed.returncode,
                completed.stdout,
                completed.stderr,
                evidence_id,
            )

    def verify_isolation(self, *, cwd: Path, timeout_seconds: int = 15) -> str:
        """Prove the browser container can reach the proxy but not public IP egress."""
        with self._lock:
            if not self._started or self._proxy_ip is None or self._policy is None:
                raise BrowserToolError("browser egress boundary is not started")
            if cwd.resolve() != self._cwd:
                raise BrowserToolError("browser egress evidence root drifted")
            script = (
                "import socket,sys; "
                f"p=socket.create_connection(('{self._proxy_ip}',{self._proxy_port}),2); p.close(); "
                "blocked=False; "
                "\ntry:\n socket.create_connection(('1.1.1.1',443),2).close()\n"
                "except OSError:\n blocked=True\n"
                "sys.exit(0 if blocked else 9)"
            )
            completed = self._docker_run(
                ("exec", self._browser_name, "python3", "-c", script),
                timeout_seconds=timeout_seconds,
            )
            evidence_id = self._write_receipt(
                cwd.resolve(),
                kind="isolation-probe",
                argv=("python3", "-c", "proxy-reachable/public-egress-blocked"),
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
            if completed.returncode != 0:
                self.shutdown()
                raise BrowserToolError("browser Docker isolation probe failed closed")
            return evidence_id

    def shutdown(self) -> None:
        """Best-effort removal of the transient containers and internal network."""
        with self._lock:
            if not self._started:
                return
            for name in (self._browser_name, self._proxy_name):
                try:
                    self._docker_run(("rm", "-f", name), timeout_seconds=20)
                except (subprocess.SubprocessError, OSError):
                    pass
            try:
                self._docker_run(("network", "rm", self._network_name), timeout_seconds=20)
            except (subprocess.SubprocessError, OSError):
                pass
            self._started = False
            self._proxy_ip = None

    def _ensure_started(
        self,
        policy: tuple[str, ...],
        cwd: Path,
        timeout_seconds: int,
    ) -> None:
        if self._started:
            if policy != self._policy:
                raise BrowserToolError("browser egress policy changed inside a live sandbox")
            if cwd != self._cwd:
                raise BrowserToolError("browser egress evidence root changed inside a live sandbox")
            return
        self._assert_docker_prerequisites(timeout_seconds)
        image_id = self._resolve_image_id(timeout_seconds)
        policy_json = json.dumps(policy, separators=(",", ":"), ensure_ascii=True)
        policy_sha = hashlib.sha256(policy_json.encode("utf-8")).hexdigest()
        try:
            self._docker_checked(
                (
                    "network",
                    "create",
                    "--driver=bridge",
                    "--internal",
                    "--opt",
                    "com.docker.network.bridge.gateway_mode_ipv4=isolated",
                    "--label",
                    "ilaios.browser-egress=true",
                    "--label",
                    f"ilaios.browser-egress.instance={self._instance}",
                    self._network_name,
                ),
                timeout_seconds,
            )
            self._assert_internal_network(timeout_seconds)
            proxy_id = self._docker_checked(
                (
                    "run",
                    "-d",
                    "--name",
                    self._proxy_name,
                    "--network=bridge",
                    "--read-only",
                    "--cap-drop=ALL",
                    "--security-opt=no-new-privileges",
                    "--pids-limit=128",
                    "--memory=256m",
                    "--cpus=0.50",
                    "--tmpfs",
                    "/tmp:rw,nosuid,nodev,size=64m",
                    "--label",
                    "ilaios.browser-egress=true",
                    "--label",
                    f"ilaios.browser-egress.instance={self._instance}",
                    "--env",
                    f"ILAIOS_ALLOWED_ORIGINS_JSON={policy_json}",
                    "--env",
                    f"ILAIOS_PROXY_PORT={self._proxy_port}",
                    "--mount",
                    f"type=bind,src={self._proxy_script},dst=/opt/ilaios/allowlist_proxy.py,readonly",
                    image_id,
                    "python3",
                    "/opt/ilaios/allowlist_proxy.py",
                ),
                timeout_seconds,
            ).strip()
            if not proxy_id:
                raise BrowserToolError("browser egress proxy container did not start")
            self._docker_checked(
                ("network", "connect", self._network_name, self._proxy_name),
                timeout_seconds,
            )
            proxy_ip = self._container_network_ip(
                self._proxy_name, self._network_name, timeout_seconds
            )
            self._assert_proxy_ready(timeout_seconds)
            browser_args: list[str] = [
                "run",
                "-d",
                "--name",
                self._browser_name,
                "--network",
                self._network_name,
                "--dns=127.0.0.1",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--pids-limit=512",
                "--memory=1536m",
                "--cpus=2.0",
                "--shm-size=512m",
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,size=768m",
                "--label",
                "ilaios.browser-egress=true",
                "--label",
                f"ilaios.browser-egress.instance={self._instance}",
                "--env",
                "HOME=/tmp/ilaios-home",
                "--mount",
                f"type=bind,src={cwd},dst=/evidence",
                "--workdir",
                "/evidence",
            ]
            if hasattr(os, "getuid") and hasattr(os, "getgid"):
                uid = os.getuid()
                gid = os.getgid()
                if uid == 0:
                    raise BrowserToolError("browser egress refuses a root host identity")
                browser_args.extend(("--user", f"{uid}:{gid}"))
            browser_args.extend((image_id, "sleep", "infinity"))
            browser_id = self._docker_checked(tuple(browser_args), timeout_seconds).strip()
            if not browser_id:
                raise BrowserToolError("browser runtime container did not start")
            self._assert_browser_network_membership(timeout_seconds)
        except Exception:
            self._started = True
            self.shutdown()
            raise
        self._policy = policy
        self._policy_sha256 = policy_sha
        self._cwd = cwd
        self._image_id = image_id
        self._proxy_ip = proxy_ip
        self._started = True

    def _assert_docker_prerequisites(self, timeout_seconds: int) -> None:
        version = self._docker_checked(
            ("version", "--format", "{{.Server.Version}}"), timeout_seconds
        ).strip()
        match = _DOCKER_VERSION_RE.match(version)
        if match is None or int(match.group(1)) < 28:
            raise BrowserToolError(
                "browser egress requires Docker Engine 28+ isolated gateway mode"
            )
        os_type = self._docker_checked(
            ("info", "--format", "{{.OSType}}"), timeout_seconds
        ).strip()
        if os_type != "linux":
            raise BrowserToolError("browser egress requires a Linux Docker Engine")

    def _resolve_image_id(self, timeout_seconds: int) -> str:
        image_id = self._docker_checked(
            ("image", "inspect", "--format", "{{.Id}}", self._runtime_image),
            timeout_seconds,
        ).strip()
        if _SHA256_RE.fullmatch(image_id) is None:
            raise BrowserToolError("browser egress runtime image is not content-addressed")
        return image_id

    def _assert_internal_network(self, timeout_seconds: int) -> None:
        raw = self._docker_checked(
            ("network", "inspect", self._network_name), timeout_seconds
        )
        parsed = cast(list[dict[str, Any]], json.loads(raw))
        if len(parsed) != 1:
            raise BrowserToolError("browser egress network inspection is ambiguous")
        network = parsed[0]
        options = network.get("Options")
        if network.get("Internal") is not True or not isinstance(options, dict):
            raise BrowserToolError("browser egress network is not internal")
        if options.get("com.docker.network.bridge.gateway_mode_ipv4") != "isolated":
            raise BrowserToolError("browser egress network lacks isolated gateway mode")

    def _container_network_ip(
        self, container: str, network: str, timeout_seconds: int
    ) -> str:
        raw = self._docker_checked(("inspect", container), timeout_seconds)
        parsed = cast(list[dict[str, Any]], json.loads(raw))
        if len(parsed) != 1:
            raise BrowserToolError("browser egress container inspection is ambiguous")
        settings = parsed[0].get("NetworkSettings")
        if not isinstance(settings, dict):
            raise BrowserToolError("browser egress container network state is missing")
        networks = settings.get("Networks")
        if not isinstance(networks, dict):
            raise BrowserToolError("browser egress container networks are missing")
        entry = networks.get(network)
        if not isinstance(entry, dict):
            raise BrowserToolError("browser egress internal network attachment is missing")
        address = entry.get("IPAddress")
        if not isinstance(address, str) or not address:
            raise BrowserToolError("browser egress proxy has no internal address")
        return address

    def _assert_proxy_ready(self, timeout_seconds: int) -> None:
        script = (
            "import socket; "
            f"s=socket.create_connection(('127.0.0.1',{self._proxy_port}),2); s.close()"
        )
        last_error: subprocess.CompletedProcess[str] | None = None
        for _ in range(20):
            completed = self._docker_run(
                ("exec", self._proxy_name, "python3", "-c", script),
                timeout_seconds=min(timeout_seconds, 5),
            )
            if completed.returncode == 0:
                return
            last_error = completed
            time.sleep(0.1)
        detail = "" if last_error is None else last_error.stderr[:200]
        raise BrowserToolError(f"browser egress proxy did not become ready: {detail}")

    def _assert_browser_network_membership(self, timeout_seconds: int) -> None:
        raw = self._docker_checked(("inspect", self._browser_name), timeout_seconds)
        parsed = cast(list[dict[str, Any]], json.loads(raw))
        if len(parsed) != 1:
            raise BrowserToolError("browser runtime inspection is ambiguous")
        settings = parsed[0].get("NetworkSettings")
        if not isinstance(settings, dict):
            raise BrowserToolError("browser runtime network state is missing")
        networks = settings.get("Networks")
        if not isinstance(networks, dict) or set(networks) != {self._network_name}:
            raise BrowserToolError("browser runtime has an unauthorized network attachment")

    def _write_cli_config(
        self, cwd: Path, proxy_ip: str, policy: tuple[str, ...]
    ) -> Path:
        config = {
            "browser": {
                "isolated": True,
                "launchOptions": {
                    "proxy": {"server": f"http://{proxy_ip}:{self._proxy_port}"},
                    "chromiumSandbox": True,
                },
                "contextOptions": {
                    "proxy": {"server": f"http://{proxy_ip}:{self._proxy_port}"},
                    "javaScriptEnabled": False,
                    "serviceWorkers": "block",
                },
            },
            "network": {"allowedOrigins": list(policy)},
            "allowUnrestrictedFileAccess": False,
            "codegen": "none",
        }
        path = cwd / f".ilaios-browser-egress-{self._instance}.json"
        path.write_text(
            json.dumps(config, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        path.chmod(0o600)
        return path

    def _write_receipt(
        self,
        cwd: Path,
        *,
        kind: str,
        argv: tuple[str, ...],
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> str:
        if self._policy is None or self._policy_sha256 is None or self._image_id is None:
            raise BrowserToolError("browser egress cannot emit evidence before initialization")
        evidence_dir = cwd / "browser-egress-evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        receipt = {
            "schema_version": 1,
            "kind": kind,
            "boundary": "docker-internal-isolated-proxy-v1",
            "instance": self._instance,
            "runtime_image_id": self._image_id,
            "network_internal": True,
            "gateway_mode_ipv4": "isolated",
            "browser_network_count": 1,
            "policy_sha256": self._policy_sha256,
            "allowed_origins": list(self._policy),
            "argv_sha256": hashlib.sha256(
                json.dumps(argv, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "returncode": returncode,
            "stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr.encode("utf-8")).hexdigest(),
            "observed_at_unix_ns": time.time_ns(),
        }
        payload = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        digest = hashlib.sha256(payload).hexdigest()
        path = evidence_dir / f"{digest}.json"
        path.write_bytes(payload)
        return f"sha256:{digest}"

    def _docker_checked(self, args: tuple[str, ...], timeout_seconds: int) -> str:
        completed = self._docker_run(args, timeout_seconds=timeout_seconds)
        if completed.returncode != 0:
            raise BrowserToolError(
                f"browser egress Docker operation failed: {completed.stderr[:240]}"
            )
        return completed.stdout

    def _docker_run(
        self, args: tuple[str, ...], *, timeout_seconds: int
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            (self._docker, *args),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )

    @staticmethod
    def _validate_cli_argv(argv: tuple[str, ...]) -> None:
        if len(argv) < 3 or argv[0] != "playwright-cli":
            raise BrowserToolError("browser egress accepts only the pinned Playwright CLI")
        if not argv[1].startswith("-s=ilaios-"):
            raise BrowserToolError("browser egress requires an ILAIOS browser session")
        if any("\x00" in arg or "\r" in arg or "\n" in arg for arg in argv):
            raise BrowserToolError("browser egress argv is malformed")


def _canonical_origins(origins: tuple[str, ...]) -> tuple[str, ...]:
    if not origins:
        raise BrowserToolError("browser egress requires explicit origins")
    canonical: set[str] = set()
    for origin in origins:
        parsed = urlsplit(origin)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise BrowserToolError("browser egress origin is invalid")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise BrowserToolError("browser egress origin contains forbidden URL components")
        if parsed.path not in {"", "/"}:
            raise BrowserToolError("browser egress policy must contain origins, not paths")
        try:
            port = parsed.port
        except ValueError as error:
            raise BrowserToolError("browser egress origin port is invalid") from error
        scheme = parsed.scheme.lower()
        host = parsed.hostname.lower()
        default_port = 443 if scheme == "https" else 80
        rendered = f"{scheme}://{host}"
        if port is not None and port != default_port:
            rendered = f"{rendered}:{port}"
        canonical.add(rendered)
    return tuple(sorted(canonical))
