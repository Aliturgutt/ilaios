from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from services.mobile_android_build_executor import (
    AndroidBuildExecutionError,
    AndroidBuildExecutionPermissionError,
    execute_android_release_build,
    sign_or_submit_android_release,
)
from services.mobile_android_release import (
    AndroidArtifactKind,
    AndroidBuildPlan,
    build_android_release_plan,
)


def _repository(tmp_path: Path, *, artifact_kind: AndroidArtifactKind = "aab") -> tuple[Path, str]:
    repository = tmp_path / "repo"
    project = repository / "apps" / "mobile" / "android" / "ilaios-mobile"
    project.mkdir(parents=True)
    subprocess.run(("git", "init", "-q"), cwd=repository, check=True)
    subprocess.run(("git", "config", "user.email", "ci@ilaios.test"), cwd=repository, check=True)
    subprocess.run(("git", "config", "user.name", "ILAIOS CI"), cwd=repository, check=True)

    if artifact_kind == "aab":
        output = "app/build/outputs/bundle/release/app-release.aab"
        payload = "real-aab-test-bytes"
    else:
        output = "app/build/outputs/apk/release/app-release.apk"
        payload = "real-apk-test-bytes"
    gradlew = project / "gradlew"
    gradlew.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        "case \" $* \" in *\" --offline \"*) ;; *) exit 41 ;; esac\n"
        "case \" $* \" in *\" --no-daemon \"*) ;; *) exit 42 ;; esac\n"
        f"mkdir -p \"$(dirname '{output}')\"\n"
        f"printf '%s' '{payload}' > '{output}'\n"
        "printf '%s' 'bounded-offline-build'\n",
        encoding="utf-8",
    )
    gradlew.chmod(0o755)
    (project / "settings.gradle.kts").write_text('rootProject.name = "ILAIOSMobile"\n', encoding="utf-8")
    subprocess.run(("git", "add", "."), cwd=repository, check=True)
    subprocess.run(("git", "commit", "-q", "-m", "fixture"), cwd=repository, check=True)
    sha = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return repository, sha


def _plan(source_sha: str, *, artifact_kind: AndroidArtifactKind = "aab") -> AndroidBuildPlan:
    return build_android_release_plan(
        app_id="ilaios-mobile",
        application_id="com.ilaios.mobile",
        source_sha=source_sha,
        artifact_kind=artifact_kind,
        version="1.0.0",
        build_number="1",
        signing_mode="google-play-app-signing",
        signing_credential=None,
    )


def test_offline_executor_produces_exact_aab_receipt(tmp_path: Path) -> None:
    repository, sha = _repository(tmp_path)
    result = execute_android_release_build(
        repository_root=repository,
        plan=_plan(sha),
        environment={"PATH": os.environ.get("PATH", ""), "SECRET_TOKEN": "must-not-propagate"},
    )

    expected = hashlib.sha256(b"real-aab-test-bytes").hexdigest()
    assert result.receipt.source_sha == sha
    assert result.receipt.artifact_kind == "aab"
    assert result.receipt.artifact_path == "app/build/outputs/bundle/release/app-release.aab"
    assert result.receipt.artifact_sha256 == expected
    assert len(result.command_sha256) == 64
    assert result.receipt.toolchain_receipt.startswith("offline-gradle:")


def test_offline_executor_produces_exact_apk_receipt(tmp_path: Path) -> None:
    repository, sha = _repository(tmp_path, artifact_kind="apk")
    result = execute_android_release_build(
        repository_root=repository,
        plan=_plan(sha, artifact_kind="apk"),
    )
    assert result.receipt.artifact_path == "app/build/outputs/apk/release/app-release.apk"
    assert result.receipt.artifact_sha256 == hashlib.sha256(b"real-apk-test-bytes").hexdigest()


def test_executor_rejects_stale_source_sha(tmp_path: Path) -> None:
    repository, sha = _repository(tmp_path)
    plan = _plan(sha)
    marker = repository / "marker.txt"
    marker.write_text("advance", encoding="utf-8")
    subprocess.run(("git", "add", "."), cwd=repository, check=True)
    subprocess.run(("git", "commit", "-q", "-m", "advance"), cwd=repository, check=True)

    with pytest.raises(AndroidBuildExecutionError, match="HEAD does not match"):
        execute_android_release_build(repository_root=repository, plan=plan)


def test_executor_rejects_missing_gradle_wrapper(tmp_path: Path) -> None:
    repository, sha = _repository(tmp_path)
    (repository / "apps/mobile/android/ilaios-mobile/gradlew").unlink()
    with pytest.raises(AndroidBuildExecutionError, match="Gradle wrapper"):
        execute_android_release_build(repository_root=repository, plan=_plan(sha))


def test_executor_fails_when_gradle_does_not_produce_expected_artifact(tmp_path: Path) -> None:
    repository, sha = _repository(tmp_path)
    gradlew = repository / "apps/mobile/android/ilaios-mobile/gradlew"
    gradlew.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    gradlew.chmod(0o755)
    with pytest.raises(AndroidBuildExecutionError, match="artifact was not produced"):
        execute_android_release_build(repository_root=repository, plan=_plan(sha))


def test_executor_does_not_accept_signing_credentials(tmp_path: Path) -> None:
    repository, sha = _repository(tmp_path)
    from services.store_release_certification import CredentialReference

    plan = build_android_release_plan(
        app_id="ilaios-mobile",
        application_id="com.ilaios.mobile",
        source_sha=sha,
        artifact_kind="aab",
        version="1.0.0",
        build_number="1",
        signing_mode="external-upload-key",
        signing_credential=CredentialReference("tenant-1", "cred-1", ("android.sign",)),
    )
    with pytest.raises(AndroidBuildExecutionPermissionError, match="cannot access signing"):
        execute_android_release_build(repository_root=repository, plan=plan)


def test_executor_rejects_unbounded_timeout(tmp_path: Path) -> None:
    repository, sha = _repository(tmp_path)
    with pytest.raises(AndroidBuildExecutionError, match="timeout_seconds"):
        execute_android_release_build(repository_root=repository, plan=_plan(sha), timeout_seconds=0)


def test_signing_and_store_operations_remain_denied() -> None:
    with pytest.raises(AndroidBuildExecutionPermissionError, match="submission"):
        sign_or_submit_android_release()
