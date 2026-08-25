from __future__ import annotations

from dataclasses import replace

import pytest

from services.app_factory import AppRequestProjection
from services.app_mobile_materialization import (
    AppMobileMaterializationError,
    build_flutter_android_materialization_plan,
    build_flutter_android_release_plan,
)
from services.app_product_spec import admit_project, build_product_spec
from services.mobile_android_executor import AndroidSourceChange


OBJECTIVE = "Materialize the governed ILAIOS mobile client"


def _spec(*, platforms: tuple[str, ...] = ("android",)):
    admission = admit_project(
        project_id="project-mobile",
        intent="new",
        objective=OBJECTIVE,
        platforms=platforms,  # type: ignore[arg-type]
    )
    return build_product_spec(
        admission=admission,
        product_name="ILAIOSMobile",
        actors=("owner",),
        screens=("home", "settings"),
        capabilities=("authentication", "files"),
        offline_required=True,
    )


def _projection(**overrides: object) -> AppRequestProjection:
    value: AppRequestProjection = {
        "request_id": "appreq-mobile-materialization",
        "platform": "android",
        "action": "client_change_request",
        "objective": OBJECTIVE,
        "request_sha256": "a" * 64,
        "approved_for_review": True,
        "approver": "owner-review",
        "client_mutated": False,
    }
    value.update(overrides)  # type: ignore[typeddict-item]
    return value


def _changes() -> tuple[AndroidSourceChange, ...]:
    return (
        AndroidSourceChange("create", "pubspec.yaml", b"name: ilaios_mobile\n"),
        AndroidSourceChange("create", "lib/main.dart", b"void main() {}\n"),
        AndroidSourceChange(
            "create",
            "android/settings.gradle.kts",
            b'rootProject.name = "ILAIOSMobile"\n',
        ),
        AndroidSourceChange(
            "create",
            "android/app/build.gradle.kts",
            b'plugins { id("com.android.application") }\n',
        ),
        AndroidSourceChange(
            "create",
            "android/app/src/main/AndroidManifest.xml",
            b'<manifest package="com.ilaios.mobile" />\n',
        ),
        AndroidSourceChange("create", "android/gradlew", b"#!/bin/sh\n"),
        AndroidSourceChange(
            "create",
            "android/gradle/wrapper/gradle-wrapper.properties",
            b"distributionUrl=https\\://services.gradle.org/distributions/gradle.zip\n",
        ),
        AndroidSourceChange(
            "create",
            "android/gradle/wrapper/gradle-wrapper.jar",
            b"repository-owned-wrapper-bytes",
        ),
    )


def test_flutter_android_materialization_is_deterministic_and_lineage_bound() -> None:
    spec = _spec()
    first = build_flutter_android_materialization_plan(
        spec=spec,
        projection=_projection(),
        app_id="ilaios-mobile",
        application_id="com.ilaios.mobile",
        source_changes=_changes(),
    )
    second = build_flutter_android_materialization_plan(
        spec=spec,
        projection=_projection(),
        app_id="ilaios-mobile",
        application_id="com.ilaios.mobile",
        source_changes=_changes(),
    )

    assert first == second
    assert first.spec_sha256 == spec.spec_sha256
    assert first.framework == "flutter"
    assert first.repository_project_root == "apps/mobile/android/ilaios-mobile"
    assert first.gradle_project_root == "apps/mobile/android/ilaios-mobile/android"
    assert len(first.materialization_sha256) == 64
    assert first.implementation_plan.app_request_id == "appreq-mobile-materialization"


def test_materialization_requires_android_and_exact_spec_objective() -> None:
    with pytest.raises(AppMobileMaterializationError, match="does not admit Android"):
        build_flutter_android_materialization_plan(
            spec=_spec(platforms=("ios",)),
            projection=_projection(),
            app_id="ilaios-mobile",
            application_id="com.ilaios.mobile",
            source_changes=_changes(),
        )

    with pytest.raises(AppMobileMaterializationError, match="not bound to the ProductSpec"):
        build_flutter_android_materialization_plan(
            spec=_spec(),
            projection=_projection(objective="different objective"),
            app_id="ilaios-mobile",
            application_id="com.ilaios.mobile",
            source_changes=_changes(),
        )


def test_materialization_fails_closed_on_incomplete_or_mutating_initial_project() -> None:
    changes = _changes()
    with pytest.raises(AppMobileMaterializationError, match="missing required project files"):
        build_flutter_android_materialization_plan(
            spec=_spec(),
            projection=_projection(),
            app_id="ilaios-mobile",
            application_id="com.ilaios.mobile",
            source_changes=changes[:-1],
        )

    modified_manifest = replace(
        changes[4], operation="modify", expected_sha256="b" * 64
    )
    with pytest.raises(AppMobileMaterializationError, match="requires create operations"):
        build_flutter_android_materialization_plan(
            spec=_spec(),
            projection=_projection(),
            app_id="ilaios-mobile",
            application_id="com.ilaios.mobile",
            source_changes=changes[:4] + (modified_manifest,) + changes[5:],
        )


def test_flutter_release_plan_uses_existing_gradle_executor_at_android_subproject() -> None:
    materialization = build_flutter_android_materialization_plan(
        spec=_spec(),
        projection=_projection(),
        app_id="ilaios-mobile",
        application_id="com.ilaios.mobile",
        source_changes=_changes(),
    )
    plan = build_flutter_android_release_plan(
        materialization=materialization,
        source_sha="c" * 40,
        artifact_kind="aab",
        version="1.0.0",
        build_number="100",
    )

    assert plan.project_layout == "flutter"
    assert plan.project_root == "apps/mobile/android/ilaios-mobile/android"
    assert plan.gradle_task == ":app:bundleRelease"
    assert plan.signing_credential is None
