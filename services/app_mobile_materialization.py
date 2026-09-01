"""Flutter-first App Factory materialization binding for the canonical Android executor.

This module closes the planning-to-source gap without creating a second App Factory,
mobile runtime, build executor, or Store authority. It binds one immutable ProductSpec
and one approved Android AppFactory projection to the existing governed Android source
executor, and it binds the resulting repository-owned Flutter Android project to the
existing offline Gradle release-plan contract.

It does not execute source mutation, Flutter/Gradle, signing, device actions, Store API
calls, submission, publication, or external network/provider operations.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from services.app_factory import AppRequestProjection
from services.app_product_spec import ProductSpec
from services.mobile_android_executor import (
    AndroidImplementationPlan,
    AndroidSourceChange,
    build_android_implementation_plan,
)
from services.mobile_android_release import (
    AndroidArtifactKind,
    AndroidBuildPlan,
    build_android_release_plan,
)


class AppMobileMaterializationError(ValueError):
    """A mobile project cannot be bound safely to the admitted App Factory lineage."""


_REQUIRED_FLUTTER_ANDROID_PATHS = frozenset(
    {
        "pubspec.yaml",
        "lib/main.dart",
        "android/settings.gradle.kts",
        "android/app/build.gradle.kts",
        "android/app/src/main/AndroidManifest.xml",
        "android/gradlew",
        "android/gradle/wrapper/gradle-wrapper.properties",
        "android/gradle/wrapper/gradle-wrapper.jar",
    }
)


@dataclass(frozen=True, slots=True)
class FlutterAndroidMaterializationPlan:
    project_id: str
    spec_sha256: str
    app_id: str
    application_id: str
    framework: str
    implementation_plan: AndroidImplementationPlan
    repository_project_root: str
    gradle_project_root: str
    materialization_sha256: str


def build_flutter_android_materialization_plan(
    *,
    spec: ProductSpec,
    projection: AppRequestProjection,
    app_id: str,
    application_id: str,
    source_changes: tuple[AndroidSourceChange, ...],
) -> FlutterAndroidMaterializationPlan:
    """Bind a real Flutter project source set to the incumbent Android executor contract."""
    if "android" not in spec.platforms:
        raise AppMobileMaterializationError("ProductSpec does not admit Android")
    if projection["platform"] != "android":
        raise AppMobileMaterializationError("materialization requires an Android AppFactory projection")
    if projection["action"] != "client_change_request":
        raise AppMobileMaterializationError("materialization requires client_change_request authority")
    if projection["approved_for_review"] is not True or not projection["approver"].strip():
        raise AppMobileMaterializationError("AppFactory projection is not approved for review")
    if projection["client_mutated"] is not False:
        raise AppMobileMaterializationError("AppFactory direct client mutation must remain false")
    if projection["objective"].strip() != spec.objective:
        raise AppMobileMaterializationError("AppFactory objective is not bound to the ProductSpec")

    paths = frozenset(change.relative_path for change in source_changes)
    missing = sorted(_REQUIRED_FLUTTER_ANDROID_PATHS - paths)
    if missing:
        raise AppMobileMaterializationError(
            "Flutter Android materialization is missing required project files: "
            + ", ".join(missing)
        )
    for change in source_changes:
        if change.relative_path in _REQUIRED_FLUTTER_ANDROID_PATHS:
            if change.operation != "create":
                raise AppMobileMaterializationError(
                    "initial Flutter Android materialization requires create operations"
                )
            if not change.content:
                raise AppMobileMaterializationError(
                    f"required Flutter Android project file is empty: {change.relative_path}"
                )

    implementation = build_android_implementation_plan(
        projection=projection,
        app_id=app_id,
        application_id=application_id,
        source_changes=source_changes,
    )
    repository_project_root = f"apps/mobile/android/{app_id}"
    gradle_project_root = f"{repository_project_root}/android"
    canonical: dict[str, object] = {
        "application_id": application_id,
        "app_id": app_id,
        "framework": "flutter",
        "gradle_project_root": gradle_project_root,
        "implementation_plan_sha256": implementation.plan_sha256,
        "project_id": spec.project_id,
        "repository_project_root": repository_project_root,
        "spec_sha256": spec.spec_sha256,
    }
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return FlutterAndroidMaterializationPlan(
        project_id=spec.project_id,
        spec_sha256=spec.spec_sha256,
        app_id=app_id,
        application_id=application_id,
        framework="flutter",
        implementation_plan=implementation,
        repository_project_root=repository_project_root,
        gradle_project_root=gradle_project_root,
        materialization_sha256=digest,
    )


def build_flutter_android_release_plan(
    *,
    materialization: FlutterAndroidMaterializationPlan,
    source_sha: str,
    artifact_kind: AndroidArtifactKind,
    version: str,
    build_number: str,
) -> AndroidBuildPlan:
    """Bind the materialized Flutter ``android/`` subproject to the existing build layer."""
    if materialization.framework != "flutter":
        raise AppMobileMaterializationError("unsupported mobile project framework")
    if materialization.implementation_plan.app_id != materialization.app_id:
        raise AppMobileMaterializationError("implementation plan app_id binding is inconsistent")
    if materialization.implementation_plan.application_id != materialization.application_id:
        raise AppMobileMaterializationError(
            "implementation plan application_id binding is inconsistent"
        )
    return build_android_release_plan(
        app_id=materialization.app_id,
        application_id=materialization.application_id,
        source_sha=source_sha,
        artifact_kind=artifact_kind,
        version=version,
        build_number=build_number,
        signing_mode="google-play-app-signing",
        signing_credential=None,
        project_layout="flutter",
    )
