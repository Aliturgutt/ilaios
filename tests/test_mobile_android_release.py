from __future__ import annotations

from dataclasses import replace

import pytest

from services.mobile_android_release import (
    AndroidBuildPlan,
    AndroidBuildReceipt,
    AndroidDeviceReceipt,
    AndroidReleaseError,
    AndroidReleasePermissionError,
    GooglePlayCertificationInput,
    build_android_release_plan,
    execute_gradle_or_google_play_operation,
    validate_android_build_receipt,
    validate_android_device_receipt,
    validate_google_play_certification_input,
)
from services.store_release_certification import (
    build_artifact_identity,
    build_credential_reference,
    build_submission_profile,
)


SHA = "a" * 64
SOURCE = "b" * 40


def _plan() -> AndroidBuildPlan:
    return build_android_release_plan(
        app_id="ilaios-mobile",
        application_id="com.ilaios.mobile",
        source_sha=SOURCE,
        artifact_kind="aab",
        version="1.0.0",
        build_number="100",
        signing_mode="google-play-app-signing",
        signing_credential=None,
    )


def test_release_plan_is_deterministic_and_uses_fixed_release_task() -> None:
    first = _plan()
    second = _plan()
    assert first == second
    assert first.project_root == "apps/mobile/android/ilaios-mobile"
    assert first.gradle_task == ":app:bundleRelease"
    assert first.artifact_kind == "aab"
    assert len(first.plan_sha256) == 64


def test_external_upload_key_requires_opaque_scoped_reference() -> None:
    with pytest.raises(AndroidReleaseError, match="opaque credential"):
        build_android_release_plan(
            app_id="ilaios-mobile",
            application_id="com.ilaios.mobile",
            source_sha=SOURCE,
            artifact_kind="aab",
            version="1.0.0",
            build_number="100",
            signing_mode="external-upload-key",
            signing_credential=None,
        )

    wrong_scope = build_credential_reference(
        tenant_id="tenant-a", credential_id="cred-a", scopes=("google.play.read",)
    )
    with pytest.raises(AndroidReleaseError, match="android.sign"):
        build_android_release_plan(
            app_id="ilaios-mobile",
            application_id="com.ilaios.mobile",
            source_sha=SOURCE,
            artifact_kind="aab",
            version="1.0.0",
            build_number="100",
            signing_mode="external-upload-key",
            signing_credential=wrong_scope,
        )


def test_build_receipt_reconciles_exact_plan_source_version_and_extension() -> None:
    plan = _plan()
    receipt = AndroidBuildReceipt(
        plan_sha256=plan.plan_sha256,
        source_sha=plan.source_sha,
        artifact_kind="aab",
        artifact_path="outputs/ilaios-release.aab",
        artifact_sha256=SHA,
        version=plan.version,
        build_number=plan.build_number,
        toolchain_receipt="gha://android-build/123",
    )
    validate_android_build_receipt(plan, receipt)

    with pytest.raises(AndroidReleaseError, match="artifact kind"):
        validate_android_build_receipt(
            plan,
            replace(receipt, artifact_kind="apk", artifact_path="outputs/ilaios-release.apk"),
        )
    with pytest.raises(AndroidReleaseError, match="not bound"):
        validate_android_build_receipt(plan, replace(receipt, plan_sha256="9" * 64))


def test_device_receipt_requires_exact_artifact_and_all_smoke_gates() -> None:
    receipt = AndroidDeviceReceipt(
        artifact_sha256=SHA,
        device_id="emulator-5554",
        platform_version="android-35",
        install_passed=True,
        launch_passed=True,
        smoke_passed=True,
        receipt_sha256="c" * 64,
    )
    validate_android_device_receipt(artifact_sha256=SHA, receipt=receipt)

    with pytest.raises(AndroidReleaseError, match="not fully passing"):
        validate_android_device_receipt(
            artifact_sha256=SHA, receipt=replace(receipt, launch_passed=False)
        )
    with pytest.raises(AndroidReleaseError, match="different artifact bytes"):
        validate_android_device_receipt(artifact_sha256="d" * 64, receipt=receipt)


def test_google_play_input_requires_android_profile_and_bound_evidence() -> None:
    plan = _plan()
    build_receipt = AndroidBuildReceipt(
        plan_sha256=plan.plan_sha256,
        source_sha=plan.source_sha,
        artifact_kind="aab",
        artifact_path="outputs/ilaios-release.aab",
        artifact_sha256=SHA,
        version=plan.version,
        build_number=plan.build_number,
        toolchain_receipt="gha://android-build/123",
    )
    device = AndroidDeviceReceipt(
        artifact_sha256=SHA,
        device_id="emulator-5554",
        platform_version="android-35",
        install_passed=True,
        launch_passed=True,
        smoke_passed=True,
        receipt_sha256="c" * 64,
    )
    profile = build_submission_profile(
        app_id="ilaios-mobile",
        platform="android",
        store="google-play",
        territories=("TR",),
    )
    artifact = build_artifact_identity(
        source_sha=SOURCE,
        build_id="android-build-123",
        binary_sha256=SHA,
        version="1.0.0",
        build_number="100",
    )
    value = GooglePlayCertificationInput(
        profile=profile,
        artifact=artifact,
        build_plan=plan,
        build_receipt=build_receipt,
        device_receipts=(device,),
        reviewer_access_receipt="reviewer-access://public-flow",
        privacy_receipt_sha256="d" * 64,
        listing_receipt_sha256="e" * 64,
        policy_snapshot_sha256="f" * 64,
    )
    validate_google_play_certification_input(value)

    ios_profile = build_submission_profile(
        app_id="ilaios-mobile",
        platform="ios",
        store="apple-app-store",
        territories=("TR",),
    )
    with pytest.raises(AndroidReleaseError, match="Android/google-play"):
        validate_google_play_certification_input(replace(value, profile=ios_profile))

    with pytest.raises(AndroidReleaseError, match="differs from build receipt"):
        validate_google_play_certification_input(
            replace(value, artifact=replace(artifact, binary_sha256="1" * 64))
        )

    rebound_plan = build_android_release_plan(
        app_id="other-app",
        application_id="com.ilaios.other",
        source_sha=SOURCE,
        artifact_kind="aab",
        version="1.0.0",
        build_number="100",
        signing_mode="google-play-app-signing",
        signing_credential=None,
    )
    with pytest.raises(AndroidReleaseError, match="app id differs"):
        validate_google_play_certification_input(replace(value, build_plan=rebound_plan))


def test_contract_layer_cannot_execute_gradle_sign_or_store_operations() -> None:
    with pytest.raises(AndroidReleasePermissionError, match="not owned"):
        execute_gradle_or_google_play_operation()
