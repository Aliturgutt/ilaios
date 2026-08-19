from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from services.app_factory import AppRequestProjection
from services.mobile_android_executor import (
    AndroidImplementationError,
    AndroidImplementationPermissionError,
    AndroidSourceChange,
    GovernedAndroidImplementationExecutor,
    build_android_implementation_plan,
    build_android_software_factory_request,
)
from services.software_factory import (
    FactoryGovernanceContext,
    FactoryJob,
    FactoryJobState,
    SoftwareFactoryRequest,
)


def _projection(
    *,
    platform: str = "android",
    action: str = "client_change_request",
    request_sha256: str = "a" * 64,
    approved_for_review: bool = True,
    approver: str = "owner-review",
) -> AppRequestProjection:
    return {
        "request_id": "appreq-android-1",
        "platform": platform,
        "action": action,
        "objective": "Build the approved Android client surface",
        "request_sha256": request_sha256,
        "approved_for_review": approved_for_review,
        "approver": approver,
        "client_mutated": False,
    }


def _changes() -> tuple[AndroidSourceChange, ...]:
    return (
        AndroidSourceChange("create", "settings.gradle.kts", b'rootProject.name = "ILAIOSMobile"\n'),
        AndroidSourceChange(
            "create",
            "app/src/main/AndroidManifest.xml",
            b"<manifest package=\"com.ilaios.mobile\" />\n",
        ),
    )


def test_plan_is_deterministic_and_bound_to_approved_projection() -> None:
    projection = _projection()
    first = build_android_implementation_plan(
        projection=projection,
        app_id="ilaios-mobile",
        application_id="com.ilaios.mobile",
        source_changes=_changes(),
    )
    second = build_android_implementation_plan(
        projection=projection,
        app_id="ilaios-mobile",
        application_id="com.ilaios.mobile",
        source_changes=_changes(),
    )

    assert first == second
    assert first.app_request_id == projection["request_id"]
    assert first.app_request_sha256 == projection["request_sha256"]
    assert len(first.plan_sha256) == 64


def test_plan_rejects_non_android_or_unapproved_projection() -> None:
    with pytest.raises(AndroidImplementationError, match="only Android"):
        build_android_implementation_plan(
            projection=_projection(platform="ios"),
            app_id="ilaios-mobile",
            application_id="com.ilaios.mobile",
            source_changes=_changes(),
        )

    with pytest.raises(AndroidImplementationError, match="approved for review"):
        build_android_implementation_plan(
            projection=_projection(approved_for_review=False, approver=""),
            app_id="ilaios-mobile",
            application_id="com.ilaios.mobile",
            source_changes=_changes(),
        )


def test_plan_rejects_build_plan_as_source_mutation_authority() -> None:
    with pytest.raises(AndroidImplementationError, match="client_change_request"):
        build_android_implementation_plan(
            projection=_projection(action="build_plan"),
            app_id="ilaios-mobile",
            application_id="com.ilaios.mobile",
            source_changes=_changes(),
        )


def test_plan_rejects_escape_duplicate_and_unsafe_modify() -> None:
    projection = _projection()
    with pytest.raises(AndroidImplementationError, match="app root"):
        build_android_implementation_plan(
            projection=projection,
            app_id="ilaios-mobile",
            application_id="com.ilaios.mobile",
            source_changes=(AndroidSourceChange("create", "../escape.kt", b"x"),),
        )

    duplicate = AndroidSourceChange("create", "app/src/main/Main.kt", b"x")
    with pytest.raises(AndroidImplementationError, match="duplicate"):
        build_android_implementation_plan(
            projection=projection,
            app_id="ilaios-mobile",
            application_id="com.ilaios.mobile",
            source_changes=(duplicate, duplicate),
        )

    with pytest.raises(AndroidImplementationError, match="expected_sha256"):
        build_android_implementation_plan(
            projection=projection,
            app_id="ilaios-mobile",
            application_id="com.ilaios.mobile",
            source_changes=(AndroidSourceChange("modify", "app/src/main/Main.kt", b"x"),),
        )


def test_software_factory_request_is_apps_mobile_android_bounded_and_zero_secret_network() -> None:
    plan = build_android_implementation_plan(
        projection=_projection(),
        app_id="ilaios-mobile",
        application_id="com.ilaios.mobile",
        source_changes=_changes(),
    )
    request = build_android_software_factory_request(
        plan=plan,
        repository_root=Path("/repo"),
        base_sha="b" * 40,
    )

    assert request.request_id.startswith("android-implementation-")
    assert request.policy.allowed_roots == frozenset({"apps"})
    assert request.policy.secure_mode is True
    assert request.policy.network_allowed is False
    assert request.policy.secrets_allowed is False
    assert request.validation_plan.commands == ()
    assert all(
        change.path.startswith("apps/mobile/android/ilaios-mobile/")
        for change in request.changeset.changes
    )


class _RecordingGovernedFactory:
    def __init__(self) -> None:
        self.request: SoftwareFactoryRequest | None = None
        self.context: FactoryGovernanceContext | None = None

    def submit(
        self,
        request: SoftwareFactoryRequest,
        context: FactoryGovernanceContext,
    ) -> FactoryJob:
        self.request = request
        self.context = context
        return FactoryJob("factory-job", request.request_id, FactoryJobState.PROPOSED)


def test_executor_routes_only_through_governed_software_factory_port() -> None:
    projection = _projection()
    plan = build_android_implementation_plan(
        projection=projection,
        app_id="ilaios-mobile",
        application_id="com.ilaios.mobile",
        source_changes=_changes(),
    )
    governed = _RecordingGovernedFactory()
    executor = GovernedAndroidImplementationExecutor(governed)
    context = cast(FactoryGovernanceContext, object())

    job = executor.submit(
        plan=plan,
        projection=projection,
        repository_root=Path("/repo"),
        base_sha="c" * 40,
        context=context,
    )

    assert job.state is FactoryJobState.PROPOSED
    assert governed.request is not None
    assert governed.context is context
    assert governed.request.policy.network_allowed is False
    assert governed.request.policy.secrets_allowed is False


def test_executor_rejects_projection_rebinding() -> None:
    projection = _projection()
    plan = build_android_implementation_plan(
        projection=projection,
        app_id="ilaios-mobile",
        application_id="com.ilaios.mobile",
        source_changes=_changes(),
    )
    executor = GovernedAndroidImplementationExecutor(_RecordingGovernedFactory())
    changed = _projection(request_sha256="d" * 64)

    with pytest.raises(AndroidImplementationError, match="approved AppFactory request"):
        executor.submit(
            plan=plan,
            projection=changed,
            repository_root=Path("/repo"),
            base_sha="e" * 40,
            context=cast(FactoryGovernanceContext, object()),
        )


def test_phase2_executor_cannot_build_sign_submit_or_publish() -> None:
    executor = GovernedAndroidImplementationExecutor(_RecordingGovernedFactory())
    with pytest.raises(AndroidImplementationPermissionError, match="outside Phase 2"):
        executor.build_sign_submit_or_publish()
