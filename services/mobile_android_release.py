"""Fail-closed Android release and Google Play certification contracts.

This module defines deterministic repository-side contracts for Phase 3 of the Mobile
Store Factory closure. It does not execute Gradle, access signing secrets, call Google
Play, submit/publish an application, or fabricate emulator/device evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

from services.store_release_certification import (
    ArtifactIdentity,
    CredentialReference,
    StoreCertificationError,
    SubmissionProfile,
)


AndroidArtifactKind = Literal["apk", "aab"]
AndroidSigningMode = Literal["google-play-app-signing", "external-upload-key"]
AndroidProjectLayout = Literal["android", "flutter"]


class AndroidReleaseError(StoreCertificationError):
    """Android release input is malformed or cannot be proven safely."""


class AndroidReleasePermissionError(PermissionError):
    """A requested Android/Play operation exceeds this bounded layer."""


@dataclass(frozen=True, slots=True)
class AndroidBuildPlan:
    app_id: str
    application_id: str
    source_sha: str
    project_root: str
    project_layout: AndroidProjectLayout
    artifact_kind: AndroidArtifactKind
    gradle_task: str
    version: str
    build_number: str
    signing_mode: AndroidSigningMode
    signing_credential: CredentialReference | None
    plan_sha256: str


@dataclass(frozen=True, slots=True)
class AndroidBuildReceipt:
    plan_sha256: str
    source_sha: str
    artifact_kind: AndroidArtifactKind
    artifact_path: str
    artifact_sha256: str
    version: str
    build_number: str
    toolchain_receipt: str


@dataclass(frozen=True, slots=True)
class AndroidDeviceReceipt:
    artifact_sha256: str
    device_id: str
    platform_version: str
    install_passed: bool
    launch_passed: bool
    smoke_passed: bool
    receipt_sha256: str


@dataclass(frozen=True, slots=True)
class GooglePlayCertificationInput:
    profile: SubmissionProfile
    artifact: ArtifactIdentity
    build_plan: AndroidBuildPlan
    build_receipt: AndroidBuildReceipt
    device_receipts: tuple[AndroidDeviceReceipt, ...]
    reviewer_access_receipt: str
    privacy_receipt_sha256: str
    listing_receipt_sha256: str
    policy_snapshot_sha256: str


_GIT_SHA = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_APP_ID = re.compile(r"[a-z0-9][a-z0-9._-]{1,127}")
_APPLICATION_ID = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+")
_ALLOWED_TASKS: dict[AndroidArtifactKind, str] = {
    "apk": ":app:assembleRelease",
    "aab": ":app:bundleRelease",
}


def build_android_release_plan(
    *,
    app_id: str,
    application_id: str,
    source_sha: str,
    artifact_kind: AndroidArtifactKind,
    version: str,
    build_number: str,
    signing_mode: AndroidSigningMode,
    signing_credential: CredentialReference | None,
    project_layout: AndroidProjectLayout = "android",
) -> AndroidBuildPlan:
    """Build an immutable plan with a fixed Gradle release task and opaque signing ref.

    Native Android projects retain the historical repository root. Flutter-first mobile
    projects use their repository-owned ``android/`` subproject so the existing bounded
    Gradle build executor can build exact Flutter-generated Android source without
    introducing a second build authority.
    """
    if _APP_ID.fullmatch(app_id) is None:
        raise AndroidReleaseError("app_id must be a lowercase bounded path token")
    if _APPLICATION_ID.fullmatch(application_id) is None:
        raise AndroidReleaseError("application_id must be a dotted Android package id")
    if _GIT_SHA.fullmatch(source_sha) is None:
        raise AndroidReleaseError("source_sha must be a lowercase 40-character git SHA")
    _require_token(version, "version")
    _require_token(build_number, "build_number")
    if project_layout not in {"android", "flutter"}:
        raise AndroidReleaseError("unsupported Android project layout")
    if signing_mode == "external-upload-key" and signing_credential is None:
        raise AndroidReleaseError("external upload-key mode requires an opaque credential reference")
    if signing_credential is not None and "android.sign" not in signing_credential.scopes:
        raise AndroidReleaseError("signing credential is missing android.sign scope")

    app_root = f"apps/mobile/android/{app_id}"
    project_root = app_root if project_layout == "android" else f"{app_root}/android"
    gradle_task = _ALLOWED_TASKS[artifact_kind]
    canonical: dict[str, object] = {
        "app_id": app_id,
        "application_id": application_id,
        "artifact_kind": artifact_kind,
        "build_number": build_number,
        "gradle_task": gradle_task,
        "project_layout": project_layout,
        "project_root": project_root,
        "signing_credential_id": None if signing_credential is None else signing_credential.credential_id,
        "signing_credential_scopes": [] if signing_credential is None else list(signing_credential.scopes),
        "signing_credential_tenant": None if signing_credential is None else signing_credential.tenant_id,
        "signing_mode": signing_mode,
        "source_sha": source_sha,
        "version": version,
    }
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return AndroidBuildPlan(
        app_id=app_id,
        application_id=application_id,
        source_sha=source_sha,
        project_root=project_root,
        project_layout=project_layout,
        artifact_kind=artifact_kind,
        gradle_task=gradle_task,
        version=version,
        build_number=build_number,
        signing_mode=signing_mode,
        signing_credential=signing_credential,
        plan_sha256=digest,
    )


def validate_android_build_receipt(plan: AndroidBuildPlan, receipt: AndroidBuildReceipt) -> None:
    """Bind build evidence to the exact plan/source/version and expected output extension."""
    _require_sha256(plan.plan_sha256, "plan_sha256")
    _require_sha256(receipt.plan_sha256, "receipt.plan_sha256")
    _require_sha256(receipt.artifact_sha256, "artifact_sha256")
    _require_token(receipt.toolchain_receipt, "toolchain_receipt")
    if receipt.plan_sha256 != plan.plan_sha256 or receipt.source_sha != plan.source_sha:
        raise AndroidReleaseError("build receipt is not bound to the release plan/source")
    if receipt.artifact_kind != plan.artifact_kind:
        raise AndroidReleaseError("build receipt artifact kind differs from release plan")
    if receipt.version != plan.version or receipt.build_number != plan.build_number:
        raise AndroidReleaseError("build receipt version identity differs from release plan")
    path = PurePosixPath(receipt.artifact_path)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise AndroidReleaseError("artifact path must be a bounded relative path")
    expected_suffix = ".aab" if plan.artifact_kind == "aab" else ".apk"
    if path.suffix != expected_suffix:
        raise AndroidReleaseError("artifact extension does not match release artifact kind")


def validate_android_device_receipt(
    *, artifact_sha256: str, receipt: AndroidDeviceReceipt
) -> None:
    """Require install/launch/smoke evidence bound to exact release bytes."""
    _require_sha256(artifact_sha256, "artifact_sha256")
    _require_sha256(receipt.artifact_sha256, "device.artifact_sha256")
    _require_sha256(receipt.receipt_sha256, "device.receipt_sha256")
    _require_token(receipt.device_id, "device_id")
    _require_token(receipt.platform_version, "platform_version")
    if receipt.artifact_sha256 != artifact_sha256:
        raise AndroidReleaseError("device receipt is for different artifact bytes")
    if not (receipt.install_passed and receipt.launch_passed and receipt.smoke_passed):
        raise AndroidReleaseError("device install/launch/smoke evidence is not fully passing")


def validate_google_play_certification_input(value: GooglePlayCertificationInput) -> None:
    """Fail closed unless Play profile, artifact, build and device evidence reconcile."""
    if value.profile.platform != "android" or value.profile.store != "google-play":
        raise AndroidReleaseError("Google Play certification requires Android/google-play profile")
    if value.profile.app_id != value.build_plan.app_id:
        raise AndroidReleaseError("submission profile app id differs from build plan")
    if value.artifact.source_sha != value.build_plan.source_sha:
        raise AndroidReleaseError("certified artifact source differs from build plan")
    if value.artifact.version != value.build_plan.version or value.artifact.build_number != value.build_plan.build_number:
        raise AndroidReleaseError("certified artifact version differs from build plan")
    validate_android_build_receipt(value.build_plan, value.build_receipt)
    if value.artifact.binary_sha256 != value.build_receipt.artifact_sha256:
        raise AndroidReleaseError("certified artifact identity differs from build receipt")
    if not value.device_receipts:
        raise AndroidReleaseError("at least one emulator/device receipt is required")
    for receipt in value.device_receipts:
        validate_android_device_receipt(artifact_sha256=value.artifact.binary_sha256, receipt=receipt)
    _require_token(value.reviewer_access_receipt, "reviewer_access_receipt")
    _require_sha256(value.privacy_receipt_sha256, "privacy_receipt_sha256")
    _require_sha256(value.listing_receipt_sha256, "listing_receipt_sha256")
    _require_sha256(value.policy_snapshot_sha256, "policy_snapshot_sha256")


def execute_gradle_or_google_play_operation() -> None:
    """Execution belongs to governed build/tool adapters and explicit Store approval paths."""
    raise AndroidReleasePermissionError(
        "Gradle execution, signing, Google Play API calls, submission and publication are not owned by this contract layer"
    )


def _require_token(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise AndroidReleaseError(f"{field} must be non-blank and trimmed")


def _require_sha256(value: str, field: str) -> None:
    if _SHA256.fullmatch(value) is None:
        raise AndroidReleaseError(f"{field} must be a lowercase SHA-256")
