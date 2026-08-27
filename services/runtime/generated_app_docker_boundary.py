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
import threading
import uuid
from pathlib import Path

from services.software_factory import ExecutionPolicy, SoftwareFactoryError
from services.software_factory_runtime import RuntimeCommand, RuntimeStepResult

_SHA256_IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
_CONTAINER_NAME = re.compile(r"^ilaios-web-sandbox-[0-9a-f]{32}$")


class DockerSecureCommandBoundary:
    """Run generated/imported project commands in a bounded Linux container.

    Security properties are enforced by Docker rather than by the generated
    command itself: no network, read-only container root, no added capabilities,
    no-new-privileges, bounded pids/memory/CPU, isolated tmpfs, no Docker socket,
    no host environment/secret inheritance, bounded host-side output capture,
    and only the governed workspace bind.
    """

    def __init__(
        self,
        *,
        runtime_image: str,
        docker_executable: str = "docker",
        memory_limit: str = "1024m",
        cpu_limit: str = "1.0",
        pids_limit: int = 256,
        output_limit_bytes: int = 1_048_576,
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
        if output_limit_bytes < 16_384 or output_limit_bytes > 16_777_216:
            raise SoftwareFactoryError("generated sandbox output limit is invalid")
        self._runtime_image = runtime_image
        self._docker = docker_executable
        self._memory_limit = memory_limit
        self._cpu_limit = cpu_limit
        self._pids_limit = pids_limit
        self._output_limit_bytes = output_limit_bytes

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
        container_name = f"ilaios-web-sandbox-{uuid.uuid4().hex}"
        relative_working = working.relative_to(root).as_posix()
        container_working = "/workspace" if relative_working == "." else f"/workspace/{relative_working}"
        docker_args = (
            "run",
            "--rm",
            "--name",
            container_name,
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
            completed = self._docker_run(
                docker_args,
                timeout_seconds=policy.timeout_seconds,
                cleanup_container_name=container_name,
            )
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
        cleanup_container_name: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        process = subprocess.Popen(
            (self._docker, *args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"PATH": os.environ.get("PATH", "")},
        )
        if process.stdout is None or process.stderr is None:
            process.kill()
            self._cleanup_container_or_fail(cleanup_container_name, timeout_seconds)
            raise SoftwareFactoryError("generated sandbox output capture is unavailable")

        overflow = threading.Event()
        stdout_buffer = bytearray()
        stderr_buffer = bytearray()

        def drain(stream: object, target: bytearray) -> None:
            reader = getattr(stream, "read", None)
            if reader is None:
                overflow.set()
                process.kill()
                return
            while True:
                chunk = reader(65_536)
                if not chunk:
                    return
                remaining = self._output_limit_bytes - len(target)
                if remaining > 0:
                    target.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    overflow.set()
                    process.kill()
                    return

        stdout_thread = threading.Thread(target=drain, args=(process.stdout, stdout_buffer), daemon=True)
        stderr_thread = threading.Thread(target=drain, args=(process.stderr, stderr_buffer), daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        timed_out = False
        try:
            returncode = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait()
            returncode = process.returncode
        finally:
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)

        drain_failed = stdout_thread.is_alive() or stderr_thread.is_alive()
        bounded_failure = timed_out or drain_failed or overflow.is_set()
        if bounded_failure:
            process.kill()
            self._cleanup_container_or_fail(cleanup_container_name, timeout_seconds)
        if timed_out:
            raise subprocess.TimeoutExpired((self._docker, *args), timeout_seconds)
        if drain_failed:
            raise SoftwareFactoryError("generated sandbox output drain failed closed")
        if overflow.is_set():
            raise SoftwareFactoryError("generated sandbox output exceeds bounded capture limit")

        return subprocess.CompletedProcess(
            (self._docker, *args),
            returncode,
            stdout_buffer.decode("utf-8", errors="replace"),
            stderr_buffer.decode("utf-8", errors="replace"),
        )

    def _cleanup_container_or_fail(
        self,
        container_name: str | None,
        timeout_seconds: int,
    ) -> None:
        if container_name is None:
            return
        if _CONTAINER_NAME.fullmatch(container_name) is None:
            raise SoftwareFactoryError("generated sandbox cleanup identity is invalid")
        if not self._force_remove_container(container_name, timeout_seconds):
            raise SoftwareFactoryError("generated sandbox container cleanup could not be verified")

    def _force_remove_container(self, container_name: str, timeout_seconds: int) -> bool:
        cleanup_timeout = min(max(timeout_seconds, 1), 10)
        env = {"PATH": os.environ.get("PATH", "")}
        try:
            removed = subprocess.run(
                (self._docker, "rm", "--force", container_name),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=cleanup_timeout,
                env=env,
            )
        except (subprocess.TimeoutExpired, OSError):
            return False
        if removed.returncode == 0:
            return True
        if self._is_missing_container_error(removed.stderr):
            return True
        try:
            inspected = subprocess.run(
                (self._docker, "container", "inspect", container_name),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=cleanup_timeout,
                env=env,
            )
        except (subprocess.TimeoutExpired, OSError):
            return False
        return inspected.returncode != 0 and self._is_missing_container_error(inspected.stderr)

    @staticmethod
    def _is_missing_container_error(stderr: str | None) -> bool:
        message = (stderr or "").lower()
        return "no such container" in message or "no such object" in message
