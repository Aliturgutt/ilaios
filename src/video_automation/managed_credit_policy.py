"""Production policy factory for ILAIOS-managed paid video credits."""

from __future__ import annotations

from .configuration import (
    ApprovalMode,
    BudgetPolicy,
    ExecutionMode,
    PlatformPolicy,
    ProviderPolicy,
    QualityRequirements,
    RetryPolicy,
    VideoAutomationPolicy,
)
from .openrouter_managed_video_provider import OPENROUTER_MANAGED_PROVIDER_NAME


def managed_credit_production_policy(
    *,
    max_cost_per_video: float,
    max_daily_cost: float,
    max_retry_cost: float,
) -> VideoAutomationPolicy:
    """Return a production policy that permits only the managed paid video path.

    Paid-provider permission is intentionally narrow: the only allowed paid
    provider is the ILAIOS-managed OpenRouter video adapter, and the existing
    BEFORE_PAID_PROVIDER boundary remains required. The managed-credit
    coordinator satisfies that boundary by reserving user/tenant ILAIOS credits
    before dispatch.
    """

    if max_cost_per_video <= 0:
        raise ValueError("max_cost_per_video must be greater than zero")
    if max_daily_cost <= 0:
        raise ValueError("max_daily_cost must be greater than zero")
    if max_retry_cost < 0:
        raise ValueError("max_retry_cost must be >= 0")
    if max_retry_cost > max_cost_per_video:
        raise ValueError("max_retry_cost cannot exceed max_cost_per_video")

    return VideoAutomationPolicy(
        mode=ExecutionMode.PRODUCTION,
        provider=ProviderPolicy(
            allow_paid_providers=True,
            allowed_provider_names=(OPENROUTER_MANAGED_PROVIDER_NAME,),
            require_explicit_provider=True,
        ),
        budget=BudgetPolicy(
            currency="USD",
            max_cost_per_video=max_cost_per_video,
            max_daily_cost=max_daily_cost,
            max_retry_cost=max_retry_cost,
        ),
        retry=RetryPolicy(max_attempts=2),
        approval=ApprovalMode.BEFORE_PAID_PROVIDER,
        platform=PlatformPolicy(
            enabled_platforms=("youtube", "tiktok", "instagram", "facebook")
        ),
        quality=QualityRequirements(
            width=1080,
            height=1920,
            fps=30.0,
            min_duration_seconds=1.0,
            max_duration_seconds=180.0,
        ),
    )
