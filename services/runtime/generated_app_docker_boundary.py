"""OS-enforced Docker boundary for hostile generated Web App build/test commands.

This is a concrete implementation of the canonical ``SecureCommandBoundary``
protocol used by Software Factory runtime adapters. It deliberately provides a
strict no-network/no-secret build boundary. Preview/browser egress remains a
separate governed concern and is not granted here.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path

from services.software_factory import ExecutionPolicy, SoftwareFactoryError
from services.software_factory_runtime import RuntimeCommand, RuntimeStepResult

_SHA256_IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")


class DockerSecureCommandBoundary:
    """Run generated/imported project commands in a bounded Linux container.

    Security properties are enforced by Docker rather than by the generated
    command itself: no network, read-only container root, no added capabilities,
    no-new-privileges, bounded pids/memory/CPU, isolated tmpfs, no Docker socket,
    no host environment/secret inheritance, and only the governed workspace bind.
    """

    def __init__(
        self,
        *,
        runtime_image: str,
        docker_executable: str = "docker",
        memory_limit: str = "1024m",
        cpu_limit: str = "1.0",
        pids_limit: int = 256,
    ) -> None:
        if not runtime_image.strip() or any(char in runtime_image for char in "\r\n\x00"):
            raise SoftwareFactoryError("generated sandbox runtime image is invalid")
        if not docker_executable.strip() or any(
            char in docker_executable for char in "\r\n\x00"
        ):
            raise SoftwareFactoryError("generated sandbox Docker executable is invalid")
        if not memory_limit.strip() or any(char in memory_limit for char in "\r\n\x00"):
            raise SoftwareFactoryError("generated sandbox memory limit is invalid")
        if not cpu_limit.strip() or any(char in cpu_limit for char in "\r\n\x00"):
            raise SoftwareFactoryError("generated sandbox CPU limit is invalid")
        if pids_limit < 16 or pids_limit > 4096:
            raise SoftwareFactoryError("generated sandbox pids limit is invalid")
        self._runtime_image = runtime_image
        self._docker = docker_executable
        self._memory_limit = memory_limit
        self._cpu_limit = cpu_limit
        self._pids_limit = pids_limit

    def execute(
        self,
        workspace: Path,
        command: RuntimeCommand,
        policy: ExecutionPolicy,
    ) -> RuntimeStepResult:
        root = workspace.resolve()
        if not root.is_dir():
            raise SoftwareFactoryError("generated sandbox workspace is unavailable")
        if not policy.secure_mode or policy.network_allowed or policy.secrets_allowed:
            raise SoftwareFactoryError("generated sandbox requires secure no-network no-secret policy")
        if policy.timeout_seconds < 1 or policy.timeout_seconds > 600:
            raise SoftwareFactoryError("generated sandbox timeout is invalid")
        if any(not part or any(char in part for char in "\r\n\x00") for part in command.argv):
            raise SoftwareFactoryError("generated sandbox command is invalid")

        working = (root / command.working_directory).resolve()
        if root != working and root not in working.parents:
            raise SoftwareFactoryError("generated sandbox working directory escapes workspace")
        if not working.is_dir():
            raise SoftwareFactoryError("generated sandbox working directory is unavailable")

        uid, gid = self._host_identity()
        image_id = self._resolve_image_id(policy.timeout_seconds)
        relative_working = working.relative_to(root).as_posix()
        container_working = "/workspace" if relative_working == "." else f"/workspace/{relative_working}"
        docker_args = (
            "run",
            "--rm",
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            f"--pids-limit={self._pids_limit}",
            f"--memory={self._memory_limit}",
            f"--cpus={self._cpu_limit}",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,noexec,size=256m",
            "--env",
            "HOME=/tmp/ilaios-home",
            "--user",
            f"{uid}:{gid}",
            "--mount",
            f"type=bind,src={root},dst=/workspace",
            "--workdir",
            container_working,
            image_id,
            *command.argv,
        )
        try:
            completed = self._docker_run(docker_args, timeout_seconds=policy.timeout_seconds)
        except (subprocess.TimeoutExpired, OSError) as error:
            raise SoftwareFactoryError("generated sandbox execution failed closed") from error

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        return RuntimeStepResult(
            stage=command.stage,
            command=command.argv,
            exit_code=completed.returncode,
            stdout_sha256=hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
            stderr_sha256=hashlib.sha256(stderr.encode("utf-8")).hexdigest(),
            passed=completed.returncode == 0,
        )

    def _host_identity(self) -> tuple[int, int]:
        if not hasattr(os, "getuid") or not hasattr(os, "getgid"):
            raise SoftwareFactoryError("generated sandbox requires a Linux/POSIX host identity")
        uid = os.getuid()
        gid = os.getgid()
        if uid == 0:
            raise SoftwareFactoryError("generated sandbox refuses a root host identity")
        return uid, gid

    def _resolve_image_id(self, timeout_seconds: int) -> str:
        try:
            completed = self._docker_run(
                ("image", "inspect", "--format", "{{.Id}}", self._runtime_image),
                timeout_seconds=timeout_seconds,
            )
        except (subprocess.TimeoutExpired, OSError) as error:
            raise SoftwareFactoryError("generated sandbox runtime image is unavailable") from error
        image_id = (completed.stdout or "").strip()
        if completed.returncode != 0 or _SHA256_IMAGE_ID.fullmatch(image_id) is None:
            raise SoftwareFactoryError("generated sandbox runtime image is not immutable")
        return image_id

    def _docker_run(
        self,
        args: tuple[str, ...],
        *,
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            (self._docker, *args),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env={"PATH": os.environ.get("PATH", "")},
        )
