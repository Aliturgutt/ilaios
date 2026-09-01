"""Tests for the platform-side App Factory boundary."""

import pytest

from services.app_factory import AppFactory, AppFactoryError


def test_app_request_is_deterministic_and_review_only() -> None:
    first = AppFactory()
    first_request = first.propose(
        "request-1",
        platform="windows",
        action="client_change_request",
        objective="Describe a bounded client change for separate implementation review.",
        target_path="artifacts/app/windows/change-request.json",
    )
    approved = first.approve_for_review("request-1", approver="human-owner")
    projection = first.review_projection("request-1")

    second = AppFactory()
    second_request = second.propose(
        "request-1",
        platform="windows",
        action="client_change_request",
        objective="Describe a bounded client change for separate implementation review.",
        target_path="artifacts/app/windows/change-request.json",
    )

    assert first_request.request_sha256 == second_request.request_sha256
    assert approved.approved_for_review is True
    assert projection["client_mutated"] is False
    assert len(projection["request_sha256"]) == 64


def test_client_implementation_roots_fail_closed() -> None:
    factory = AppFactory()
    for target in (
        "apps/desktop/lib/main.dart",
        "desktop/client.dart",
        "mobile/android/app.kt",
        "website/src/page.tsx",
    ):
        with pytest.raises(AppFactoryError, match="client implementation paths"):
            factory.propose(
                f"request-{target.split('/', 1)[0]}",
                platform="windows",
                action="client_change_request",
                objective="Forbidden client mutation",
                target_path=target,
            )


def test_unsupported_platform_action_and_unsafe_path_fail_closed() -> None:
    factory = AppFactory()
    with pytest.raises(AppFactoryError, match="unsupported app platform"):
        factory.propose(
            "linux-request",
            platform="linux",
            action="build_plan",
            objective="Unsupported platform",
            target_path="artifacts/app/linux/plan.json",
        )
    with pytest.raises(AppFactoryError, match="unsupported app factory action"):
        factory.propose(
            "publish-request",
            platform="android",
            action="publish",
            objective="Unsafe publish",
            target_path="artifacts/app/android/plan.json",
        )
    with pytest.raises(AppFactoryError, match="bounded relative path"):
        factory.propose(
            "escape-request",
            platform="ios",
            action="test_plan",
            objective="Unsafe path",
            target_path="../outside.json",
        )


def test_approval_and_external_mutation_boundaries_fail_closed() -> None:
    factory = AppFactory()
    factory.propose(
        "request-1",
        platform="android",
        action="build_plan",
        objective="Prepare review-only build requirements.",
        target_path="artifacts/app/android/build-plan.json",
    )
    with pytest.raises(AppFactoryError, match="only approved app requests"):
        factory.review_projection("request-1")
    factory.approve_for_review("request-1", approver="human-owner")
    with pytest.raises(AppFactoryError, match="direct client implementation mutation is forbidden"):
        factory.mutate_client("request-1")
    with pytest.raises(AppFactoryError, match="deployment, signing and store submission are forbidden"):
        factory.deploy_or_submit("request-1")
