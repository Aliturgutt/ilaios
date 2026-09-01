"""Tests for ILAIOS Video Automation configuration and policy."""

import pytest

from src.video_automation.configuration import (
    ApprovalMode,
    BudgetPolicy,
    ExecutionMode,
    PlatformPolicy,
    ProviderPolicy,
    QualityRequirements,
    RetryPolicy,
    VideoAutomationPolicy,
)


def test_test_default_blocks_paid_providers() -> None:
    policy = VideoAutomationPolicy.test_default()
    assert policy.mode is ExecutionMode.TEST
    assert policy.provider.allow_paid_providers is False
    assert policy.can_use_provider("local-test", is_paid=False) is True
    assert policy.can_use_provider("seedance", is_paid=True) is False


def test_test_mode_rejects_paid_provider_policy() -> None:
    with pytest.raises(ValueError, match="TEST mode must not allow paid providers"):
        VideoAutomationPolicy(
            mode=ExecutionMode.TEST,
            provider=ProviderPolicy(allow_paid_providers=True),
            budget=BudgetPolicy(),
            retry=RetryPolicy(),
            approval=ApprovalMode.NONE,
            platform=PlatformPolicy(enabled_platforms=("youtube",)),
            quality=QualityRequirements(
                width=1080,
                height=1920,
                fps=30,
                min_duration_seconds=1,
                max_duration_seconds=60,
            ),
        )


def test_provider_policy_blocks_named_provider() -> None:
    policy = ProviderPolicy(
        allow_paid_providers=True,
        blocked_provider_names=("runway",),
    )
    assert policy.is_provider_allowed("runway", is_paid=False) is False
    assert policy.is_provider_allowed("seedance", is_paid=True) is True


def test_provider_policy_respects_allowlist() -> None:
    policy = ProviderPolicy(
        allow_paid_providers=False,
        allowed_provider_names=("local-test",),
    )
    assert policy.is_provider_allowed("local-test", is_paid=False) is True
    assert policy.is_provider_allowed("other-local", is_paid=False) is False


def test_provider_cannot_be_allowed_and_blocked() -> None:
    with pytest.raises(ValueError, match="both allowed and blocked"):
        ProviderPolicy(
            allow_paid_providers=False,
            allowed_provider_names=("provider-a",),
            blocked_provider_names=("provider-a",),
        )


def test_provider_policy_rejects_duplicate_names() -> None:
    with pytest.raises(ValueError, match="duplicate allowed provider"):
        ProviderPolicy(
            allow_paid_providers=False,
            allowed_provider_names=("provider-a", "provider-a"),
        )


def test_budget_policy_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="max_cost_per_video"):
        BudgetPolicy(max_cost_per_video=-0.01)


def test_retry_policy_is_bounded() -> None:
    policy = RetryPolicy(
        max_attempts=3,
        initial_backoff_seconds=2,
        max_backoff_seconds=10,
    )
    assert policy.max_attempts == 3
    assert policy.max_backoff_seconds == 10


def test_retry_policy_rejects_invalid_backoff_range() -> None:
    with pytest.raises(ValueError, match="max_backoff_seconds"):
        RetryPolicy(
            max_attempts=2,
            initial_backoff_seconds=10,
            max_backoff_seconds=5,
        )


def test_platform_policy_requires_unique_platforms() -> None:
    with pytest.raises(ValueError, match="duplicate platform"):
        PlatformPolicy(enabled_platforms=("youtube", "youtube"))


def test_platform_policy_checks_enabled_platform() -> None:
    policy = PlatformPolicy(enabled_platforms=("youtube", "tiktok"))
    assert policy.is_enabled("youtube") is True
    assert policy.is_enabled("instagram") is False


def test_quality_requirements_validate_duration_range() -> None:
    with pytest.raises(ValueError, match="max_duration_seconds"):
        QualityRequirements(
            width=1080,
            height=1920,
            fps=30,
            min_duration_seconds=60,
            max_duration_seconds=30,
        )


def test_production_default_disables_paid_providers_by_default() -> None:
    policy = VideoAutomationPolicy.production_default()
    assert policy.mode is ExecutionMode.PRODUCTION
    assert policy.provider.allow_paid_providers is False
    assert policy.requires_approval_for_paid_provider() is True


def test_before_publish_approval_is_reported() -> None:
    policy = VideoAutomationPolicy.test_default()
    assert policy.requires_approval_before_publish() is True
