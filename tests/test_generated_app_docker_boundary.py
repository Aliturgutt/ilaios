from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from services.runtime.generated_app_docker_boundary import DockerSecureCommandBoundary
from services.software_factory import ExecutionPolicy, SoftwareFactoryError
from services.software_factory_runtime import RuntimeCommand

_IMAGE_ID = "sha256:" + "a" * 64


class _RecordingBoundary(DockerSecureCommandBoundary):
    def __init__(self) -> None:
        super().__init__(runtime_image="ilaios/generated-runtime:test")
        self.calls: list[tuple[str, ...]] = []
        self.next_result = subprocess.CompletedProcess(("docker",), 0, "", "")

    def _host_identity(self) -> tuple[int, int]:
        return 1000, 1000

    def _resolve_image_id(self, timeout_seconds: int) -> str:
        assert timeout_seconds == 45
        return _IMAGE_ID

    def _docker_run(
        self,
        args: tuple[str, ...],
        *,
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[str]:
        assert timeout_seconds == 45
        self.calls.append(args)
        return self.next_result


def _policy(**overrides: object) -> ExecutionPolicy:
    values: dict[str, object] = {
        "allowed_roots": frozenset({"."}),
        "network_allowed": False,
        "secrets_allowed": False,
        "secure_mode": True,
        "timeout_seconds": 45,
    }
    values.update(overrides)
    return ExecutionPolicy(**values)  # type: ignore[arg-type]


def test_boundary_builds_fail_closed_docker_isolation_command(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    app = workspace / "app"
    app.mkdir(parents=True)
    boundary = _RecordingBoundary()
    boundary.next_result = subprocess.CompletedProcess(("docker",), 0, "ok\n", "warn\n")

    result = boundary.execute(
        workspace,
        RuntimeCommand("build", ("pnpm", "run", "build"), "app"),
        _policy(),
    )

    assert result.passed is True
    assert result.command == ("pnpm", "run", "build")
    assert result.stdout_sha256 == hashlib.sha256(b"ok\n").hexdigest()
    assert result.stderr_sha256 == hashlib.sha256(b"warn\n").hexdigest()
    assert len(boundary.calls) == 1
    argv = boundary.calls[0]
    assert argv[:5] == ("run", "--rm", "--network=none", "--read-only", "--cap-drop=ALL")
    assert "--security-opt=no-new-privileges" in argv
    assert "--pids-limit=256" in argv
    assert "--memory=1024m" in argv
    assert "--cpus=1.0" in argv
    assert "HOME=/tmp/ilaios-home" in argv
    assert "1000:1000" in argv
    assert f"type=bind,src={workspace.resolve()},dst=/workspace" in argv
    assert "/workspace/app" in argv
    assert _IMAGE_ID in argv
    assert argv[-3:] == ("pnpm", "run", "build")
    assert all("docker.sock" not in item for item in argv)


def test_boundary_rejects_non_secure_policy(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    cases: tuple[ExecutionPolicy, ...] = (
        _policy(network_allowed=True, secure_mode=False),
        _policy(secrets_allowed=True, secure_mode=False),
        _policy(secure_mode=False),
    )

    for policy in cases:
        boundary = _RecordingBoundary()
        with pytest.raises(SoftwareFactoryError, match="secure no-network no-secret"):
            boundary.execute(workspace, RuntimeCommand("test", ("pytest",), "."), policy)
        assert boundary.calls == []


def test_boundary_rejects_working_directory_escape(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    boundary = _RecordingBoundary()

    with pytest.raises(SoftwareFactoryError, match="escapes workspace"):
        boundary.execute(
            workspace,
            RuntimeCommand("build", ("pnpm", "run", "build"), "../outside"),
            _policy(),
        )


def test_boundary_keeps_failed_command_as_failed_evidence(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    boundary = _RecordingBoundary()
    boundary.next_result = subprocess.CompletedProcess(("docker",), 9, "", "blocked")

    result = boundary.execute(
        workspace,
        RuntimeCommand("test", ("pnpm", "test"), "."),
        _policy(),
    )

    assert result.passed is False
    assert result.exit_code == 9
    assert result.stderr_sha256 == hashlib.sha256(b"blocked").hexdigest()


def test_boundary_kills_host_output_flood_before_control_plane_memory_growth(
    tmp_path: Path,
) -> None:
    executable = tmp_path / "fake-docker"
    executable.write_text(
        "#!/bin/sh\n"
        "i=0\n"
        "while [ \"$i\" -lt 20000 ]; do\n"
        "  printf x\n"
        "  i=$((i + 1))\n"
        "done\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    boundary = DockerSecureCommandBoundary(
        runtime_image="ilaios/generated-runtime:test",
        docker_executable=str(executable),
        output_limit_bytes=16_384,
    )

    with pytest.raises(SoftwareFactoryError, match="output exceeds bounded capture limit"):
        boundary._docker_run(("run",), timeout_seconds=5)
