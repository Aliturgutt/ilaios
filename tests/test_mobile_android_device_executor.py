from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from services.mobile_android_device_executor import (
    AndroidDeviceExecutionError,
    AndroidDeviceExecutionPermissionError,
    execute_aab_derivation_signing_or_google_play,
    execute_android_apk_device_e2e,
)
from services.mobile_android_release import (
    AndroidArtifactKind,
    AndroidBuildPlan,
    AndroidBuildReceipt,
    build_android_release_plan,
    validate_android_device_receipt,
)


def _plan(*, artifact_kind: AndroidArtifactKind = "apk") -> AndroidBuildPlan:
    return build_android_release_plan(
        app_id="ilaios-mobile",
        application_id="com.ilaios.mobile",
        source_sha="a" * 40,
        artifact_kind=artifact_kind,
        version="1.0.0",
        build_number="1",
        signing_mode="google-play-app-signing",
        signing_credential=None,
    )


def _project(tmp_path: Path, artifact_kind: AndroidArtifactKind = "apk") -> tuple[Path, Path, bytes]:
    root = tmp_path / "repo"
    project = root / "apps/mobile/android/ilaios-mobile"
    suffix = "apk/release/app-release.apk" if artifact_kind == "apk" else "bundle/release/app-release.aab"
    artifact = project / "app/build/outputs" / suffix
    artifact.parent.mkdir(parents=True)
    content = b"real-test-artifact-bytes"
    artifact.write_bytes(content)
    return root, artifact, content


def _receipt(
    plan: AndroidBuildPlan, artifact: Path, content: bytes, project_root: Path
) -> AndroidBuildReceipt:
    return AndroidBuildReceipt(
        plan_sha256=plan.plan_sha256,
        source_sha=plan.source_sha,
        artifact_kind=plan.artifact_kind,
        artifact_path=artifact.relative_to(project_root).as_posix(),
        artifact_sha256=hashlib.sha256(content).hexdigest(),
        version=plan.version,
        build_number=plan.build_number,
        toolchain_receipt="toolchain-receipt",
    )


def _adb(tmp_path: Path, *, fail_install: bool = False) -> Path:
    script = tmp_path / "adb"
    script.write_text(
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        + ("  *\" install \"*) exit 7 ;;\n" if fail_install else "")
        + "  *\"getprop ro.build.version.release\"*) echo '35' ;;\n"
        "  *\"pm path\"*) echo 'package:/data/app/com.ilaios.mobile/base.apk' ;;\n"
        "  *) echo 'OK' ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script.resolve()


def test_device_executor_produces_bound_receipt_for_exact_apk(tmp_path: Path) -> None:
    plan = _plan()
    root, artifact, content = _project(tmp_path)
    project_root = root / plan.project_root
    receipt = _receipt(plan, artifact, content, project_root)
    result = execute_android_apk_device_e2e(
        plan=plan,
        build_receipt=receipt,
        repository_root=root.resolve(),
        adb_path=_adb(tmp_path),
        device_id="emulator-5554",
    )
    assert result.artifact_sha256 == hashlib.sha256(content).hexdigest()
    assert result.platform_version == "35"
    assert result.install_passed and result.launch_passed and result.smoke_passed
    validate_android_device_receipt(artifact_sha256=result.artifact_sha256, receipt=result)


def test_device_executor_rejects_aab_without_evidenced_derivation(tmp_path: Path) -> None:
    plan = _plan(artifact_kind="aab")
    root, artifact, content = _project(tmp_path, "aab")
    receipt = _receipt(plan, artifact, content, root / plan.project_root)
    with pytest.raises(AndroidDeviceExecutionError, match="requires APK"):
        execute_android_apk_device_e2e(
            plan=plan,
            build_receipt=receipt,
            repository_root=root.resolve(),
            adb_path=_adb(tmp_path),
            device_id="emulator-5554",
        )


def test_device_executor_rejects_artifact_tampering(tmp_path: Path) -> None:
    plan = _plan()
    root, artifact, content = _project(tmp_path)
    receipt = _receipt(plan, artifact, content, root / plan.project_root)
    artifact.write_bytes(b"tampered")
    with pytest.raises(AndroidDeviceExecutionError, match="do not match"):
        execute_android_apk_device_e2e(
            plan=plan,
            build_receipt=receipt,
            repository_root=root.resolve(),
            adb_path=_adb(tmp_path),
            device_id="emulator-5554",
        )


def test_device_executor_fails_closed_on_adb_failure(tmp_path: Path) -> None:
    plan = _plan()
    root, artifact, content = _project(tmp_path)
    receipt = _receipt(plan, artifact, content, root / plan.project_root)
    with pytest.raises(AndroidDeviceExecutionError, match="adb install/launch/smoke"):
        execute_android_apk_device_e2e(
            plan=plan,
            build_receipt=receipt,
            repository_root=root.resolve(),
            adb_path=_adb(tmp_path, fail_install=True),
            device_id="emulator-5554",
        )


def test_device_executor_rejects_invalid_device_and_timeout(tmp_path: Path) -> None:
    plan = _plan()
    root, artifact, content = _project(tmp_path)
    receipt = _receipt(plan, artifact, content, root / plan.project_root)
    adb = _adb(tmp_path)
    with pytest.raises(AndroidDeviceExecutionError, match="device_id"):
        execute_android_apk_device_e2e(
            plan=plan,
            build_receipt=receipt,
            repository_root=root.resolve(),
            adb_path=adb,
            device_id="bad device",
        )
    with pytest.raises(AndroidDeviceExecutionError, match="timeout_seconds"):
        execute_android_apk_device_e2e(
            plan=plan,
            build_receipt=receipt,
            repository_root=root.resolve(),
            adb_path=adb,
            device_id="emulator-5554",
            timeout_seconds=0,
        )


def test_device_executor_never_owns_aab_signing_or_play_operations() -> None:
    with pytest.raises(AndroidDeviceExecutionPermissionError, match="outside this executor"):
        execute_aab_derivation_signing_or_google_play()
