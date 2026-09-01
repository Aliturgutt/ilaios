"""Bounded offline Android build executor for Phase 3.

The executor may run the repository-owned Gradle wrapper against an exact source SHA
with a sanitized environment and `--offline`. It never reads signing credentials,
calls Google Play, submits/publishes, or fabricates device/Store evidence. A successful
execution proves only that exact repository bytes produced exact APK/AAB bytes.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping

from services.mobile_android_release import (
    AndroidBuildPlan,
    AndroidBuildReceipt,
    AndroidReleaseError,
    validate_android_build_receipt,
)


class AndroidBuildExecutionError(AndroidReleaseError):
    """The bounded offline build could not be proven safely."""


class AndroidBuildExecutionPermissionError(PermissionError):
    """The requested operation exceeds repository-owned build authority."""


@dataclass(frozen=True, slots=True)
class AndroidBuildExecutionResult:
    receipt: AndroidBuildReceipt
    command_sha256: str
    stdout_sha256: str
    stderr_sha256: str


_GIT_SHA = re.compile(r"[0-9a-f]{40}")
_ALLOWED_ENV = ("PATH", "JAVA_HOME", "ANDROID_HOME", "ANDROID_SDK_ROOT")
_EXPECTED_ARTIFACT_PATH = {
    "apk": PurePosixPath("app/build/outputs/apk/release/app-release.apk"),
    "aab": PurePosixPath("app/build/outputs/bundle/release/app-release.aab"),
}


def execute_android_release_build(
    *,
    repository_root: Path,
    plan: AndroidBuildPlan,
    timeout_seconds: int = 900,
    environment: Mapping[str, str] | None = None,
) -> AndroidBuildExecutionResult:
    """Run one exact offline Gradle release task and bind the resulting artifact bytes."""
    repository = repository_root.resolve()
    if not repository.is_dir() or repository.is_symlink():
        raise AndroidBuildExecutionError("repository_root must be a regular directory")
    if timeout_seconds < 1 or timeout_seconds > 1800:
        raise AndroidBuildExecutionError("timeout_seconds is outside the bounded range")
    if _GIT_SHA.fullmatch(plan.source_sha) is None:
        raise AndroidBuildExecutionError("plan source SHA is invalid")
    actual_sha = _git_head(repository)
    if actual_sha != plan.source_sha:
        raise AndroidBuildExecutionError("repository HEAD does not match release plan source")
    if plan.signing_credential is not None:
        raise AndroidBuildExecutionPermissionError(
            "repository build executor cannot access signing credentials"
        )

    project_root = _bounded_project_root(repository, plan.project_root)
    gradlew = project_root / "gradlew"
    if not gradlew.is_file() or gradlew.is_symlink():
        raise AndroidBuildExecutionError("repository-owned Gradle wrapper is unavailable")

    expected_artifact = project_root.joinpath(*_EXPECTED_ARTIFACT_PATH[plan.artifact_kind].parts)
    if expected_artifact.exists():
        expected_artifact.unlink()

    command = (
        str(gradlew),
        plan.gradle_task,
        "--offline",
        "--no-daemon",
        "--stacktrace",
    )
    safe_env = _sanitized_environment(os.environ if environment is None else environment)
    completed = subprocess.run(
        command,
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=safe_env,
    )
    if completed.returncode != 0:
        raise AndroidBuildExecutionError(
            f"offline Gradle release task failed with exit code {completed.returncode}"
        )
    if not expected_artifact.is_file() or expected_artifact.is_symlink():
        raise AndroidBuildExecutionError("expected release artifact was not produced")

    artifact_bytes = expected_artifact.read_bytes()
    if not artifact_bytes:
        raise AndroidBuildExecutionError("release artifact is empty")
    artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
    command_sha256 = _sha256_text("\0".join(command))
    stdout_sha256 = _sha256_text(completed.stdout)
    stderr_sha256 = _sha256_text(completed.stderr)
    toolchain_receipt = f"offline-gradle:{command_sha256}:{stdout_sha256}:{stderr_sha256}"
    receipt = AndroidBuildReceipt(
        plan_sha256=plan.plan_sha256,
        source_sha=plan.source_sha,
        artifact_kind=plan.artifact_kind,
        artifact_path=expected_artifact.relative_to(project_root).as_posix(),
        artifact_sha256=artifact_sha256,
        version=plan.version,
        build_number=plan.build_number,
        toolchain_receipt=toolchain_receipt,
    )
    validate_android_build_receipt(plan, receipt)
    return AndroidBuildExecutionResult(
        receipt=receipt,
        command_sha256=command_sha256,
        stdout_sha256=stdout_sha256,
        stderr_sha256=stderr_sha256,
    )


def sign_or_submit_android_release() -> None:
    """Signing and Store operations remain behind separate credential/approval adapters."""
    raise AndroidBuildExecutionPermissionError(
        "signing, Google Play API access, Store submission and publication are outside build authority"
    )


def _bounded_project_root(repository: Path, project_root: str) -> Path:
    relative = PurePosixPath(project_root)
    if (
        relative.is_absolute()
        or not relative.parts
        or ".." in relative.parts
        or relative.parts[:3] != ("apps", "mobile", "android")
    ):
        raise AndroidBuildExecutionError("Android project root escapes the mobile app boundary")
    target = repository.joinpath(*relative.parts)
    resolved = target.resolve()
    if repository != resolved and repository not in resolved.parents:
        raise AndroidBuildExecutionError("Android project root escapes repository")
    if not resolved.is_dir() or resolved.is_symlink():
        raise AndroidBuildExecutionError("Android project root is unavailable")
    return resolved


def _sanitized_environment(environment: Mapping[str, str]) -> dict[str, str]:
    safe = {key: value for key in _ALLOWED_ENV if (value := environment.get(key))}
    safe["CI"] = "true"
    safe["GRADLE_OPTS"] = "-Dorg.gradle.daemon=false"
    return safe


def _git_head(repository: Path) -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env={"PATH": os.environ.get("PATH", "")},
    )
    sha = completed.stdout.strip()
    if completed.returncode != 0 or _GIT_SHA.fullmatch(sha) is None:
        raise AndroidBuildExecutionError("repository HEAD is unavailable")
    return sha


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
