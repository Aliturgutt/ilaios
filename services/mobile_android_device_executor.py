"""Bounded Android APK device/emulator E2E executor.

This Phase 3 layer verifies exact APK bytes through a caller-supplied adb binary and
produces an immutable AndroidDeviceReceipt. It has no signing, Google Play, Store,
credential, publication, provider, or paid-operation authority. AAB execution remains
fail-closed until a separately evidenced bundletool-derived APK chain exists.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from services.mobile_android_release import (
    AndroidBuildPlan,
    AndroidBuildReceipt,
    AndroidDeviceReceipt,
    AndroidReleaseError,
    AndroidReleasePermissionError,
    validate_android_build_receipt,
)

_DEVICE_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}")
_APP_ID = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+")


class AndroidDeviceExecutionError(AndroidReleaseError):
    """Device execution cannot be proven safely."""


class AndroidDeviceExecutionPermissionError(AndroidReleasePermissionError):
    """Requested operation exceeds the device-test boundary."""


def execute_android_apk_device_e2e(
    *,
    plan: AndroidBuildPlan,
    build_receipt: AndroidBuildReceipt,
    repository_root: Path,
    adb_path: Path,
    device_id: str,
    timeout_seconds: int = 60,
) -> AndroidDeviceReceipt:
    """Install, launch and smoke-check exact APK bytes on one explicit adb target."""
    validate_android_build_receipt(plan, build_receipt)
    if plan.artifact_kind != "apk" or build_receipt.artifact_kind != "apk":
        raise AndroidDeviceExecutionError(
            "direct device E2E requires APK; AAB needs a separately evidenced APK derivation"
        )
    if not repository_root.is_absolute() or not repository_root.is_dir():
        raise AndroidDeviceExecutionError("repository_root must be an existing absolute directory")
    if not adb_path.is_absolute() or not adb_path.is_file() or adb_path.is_symlink():
        raise AndroidDeviceExecutionError("adb_path must be an existing absolute regular file")
    if _DEVICE_ID.fullmatch(device_id) is None:
        raise AndroidDeviceExecutionError("device_id is invalid")
    if _APP_ID.fullmatch(plan.application_id) is None:
        raise AndroidDeviceExecutionError("application_id is invalid")
    if timeout_seconds < 1 or timeout_seconds > 300:
        raise AndroidDeviceExecutionError("timeout_seconds must be between 1 and 300")

    project_root = _bounded_existing_directory(repository_root, plan.project_root)
    artifact = _bounded_existing_file(project_root, build_receipt.artifact_path)
    artifact_sha256 = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if artifact_sha256 != build_receipt.artifact_sha256:
        raise AndroidDeviceExecutionError("APK bytes do not match the build receipt")

    commands = (
        (str(adb_path), "-s", device_id, "install", "-r", str(artifact)),
        (
            str(adb_path), "-s", device_id, "shell", "monkey", "-p",
            plan.application_id, "-c", "android.intent.category.LAUNCHER", "1",
        ),
        (str(adb_path), "-s", device_id, "shell", "pm", "path", plan.application_id),
        (str(adb_path), "-s", device_id, "shell", "getprop", "ro.build.version.release"),
    )
    outputs: list[dict[str, object]] = []
    for command in commands:
        completed = _run(command, timeout_seconds)
        outputs.append(
            {
                "command_sha256": hashlib.sha256("\0".join(command).encode()).hexdigest(),
                "returncode": completed.returncode,
                "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
                "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
            }
        )
        if completed.returncode != 0:
            raise AndroidDeviceExecutionError("adb install/launch/smoke command failed")

    platform_version = _run(
        (str(adb_path), "-s", device_id, "shell", "getprop", "ro.build.version.release"),
        timeout_seconds,
    ).stdout.strip()
    if not platform_version:
        raise AndroidDeviceExecutionError("Android platform version evidence is missing")

    canonical = {
        "artifact_sha256": artifact_sha256,
        "device_id": device_id,
        "platform_version": platform_version,
        "install_passed": True,
        "launch_passed": True,
        "smoke_passed": True,
        "commands": outputs,
    }
    receipt_sha256 = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return AndroidDeviceReceipt(
        artifact_sha256=artifact_sha256,
        device_id=device_id,
        platform_version=platform_version,
        install_passed=True,
        launch_passed=True,
        smoke_passed=True,
        receipt_sha256=receipt_sha256,
    )


def execute_aab_derivation_signing_or_google_play() -> None:
    raise AndroidDeviceExecutionPermissionError(
        "AAB derivation, signing, Google Play API, submission and publication are outside this executor"
    )


def _run(command: tuple[str, ...], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env={"PATH": os.environ.get("PATH", "")},
    )


def _bounded_existing_directory(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    resolved_root = root.resolve()
    if resolved_root != target and resolved_root not in target.parents:
        raise AndroidDeviceExecutionError("project root escapes repository")
    if not target.is_dir() or target.is_symlink():
        raise AndroidDeviceExecutionError("Android project root is unavailable")
    return target


def _bounded_existing_file(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    resolved_root = root.resolve()
    if resolved_root != target.parent and resolved_root not in target.parents:
        raise AndroidDeviceExecutionError("artifact path escapes Android project")
    if not target.is_file() or target.is_symlink():
        raise AndroidDeviceExecutionError("APK artifact is unavailable")
    return target
