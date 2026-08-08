"""Deterministic configuration and policy models for ILAIOS Video Automation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


def _validate_text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")


class ExecutionMode(Enum):
    TEST = "test"
    PRODUCTION = "production"


class ApprovalMode(Enum):
    NONE = "none"
    BEFORE_RENDER = "before_render"
    BEFORE_PUBLISH = "before_publish"
    BEFORE_PAID_PROVIDER = "before_paid_provider"


@dataclass(frozen=True, slots=True)
class QualityRequirements:
    width: int
    height: int
    fps: float
    min_duration_seconds: float
    max_duration_seconds: float

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("width must be greater than 0")
        if self.height <= 0:
            raise ValueError("height must be greater than 0")
        if self.fps <= 0:
            raise ValueError("fps must be greater than 0")
        if self.min_duration_seconds <= 0:
            raise ValueError("min_duration_seconds must be greater than 0")
        if self.max_duration_seconds < self.min_duration_seconds:
            raise ValueError(
                "max_duration_seconds must be greater than or equal to "
                "min_duration_seconds"
            )


@dataclass(frozen=True, slots=True)
class BudgetPolicy:
    currency: str = "USD"
    max_cost_per_video: float = 0.0
    max_daily_cost: float = 0.0
    max_retry_cost: float = 0.0

    def __post_init__(self) -> None:
        _validate_text("currency", self.currency)
        for name in ("max_cost_per_video", "max_daily_cost", "max_retry_cost"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be >= 0")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 1
    initial_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.initial_backoff_seconds < 0:
            raise ValueError("initial_backoff_seconds must be >= 0")
        if self.max_backoff_seconds < self.initial_backoff_seconds:
            raise ValueError(
                "max_backoff_seconds must be greater than or equal to "
                "initial_backoff_seconds"
            )


@dataclass(frozen=True, slots=True)
class ProviderPolicy:
    allow_paid_providers: bool
    allowed_provider_names: tuple[str, ...] = ()
    blocked_provider_names: tuple[str, ...] = ()
    require_explicit_provider: bool = False

    def __post_init__(self) -> None:
        allowed: set[str] = set()
        for name in self.allowed_provider_names:
            _validate_text("allowed provider", name)
            if name in allowed:
                raise ValueError(f"duplicate allowed provider: {name}")
            allowed.add(name)

        blocked: set[str] = set()
        for name in self.blocked_provider_names:
            _validate_text("blocked provider", name)
            if name in blocked:
                raise ValueError(f"duplicate blocked provider: {name}")
            blocked.add(name)

        overlap = allowed.intersection(blocked)
        if overlap:
            provider = min(overlap)
            raise ValueError(f"provider cannot be both allowed and blocked: {provider}")

    def is_provider_allowed(self, provider_name: str, *, is_paid: bool) -> bool:
        _validate_text("provider_name", provider_name)
        if provider_name in self.blocked_provider_names:
            return False
        if self.allowed_provider_names and provider_name not in self.allowed_provider_names:
            return False
        return not (is_paid and not self.allow_paid_providers)


@dataclass(frozen=True, slots=True)
class PlatformPolicy:
    enabled_platforms: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.enabled_platforms:
            raise ValueError("enabled_platforms must not be empty")
        seen: set[str] = set()
        for platform in self.enabled_platforms:
            _validate_text("platform", platform)
            if platform in seen:
                raise ValueError(f"duplicate platform: {platform}")
            seen.add(platform)

    def is_enabled(self, platform: str) -> bool:
        _validate_text("platform", platform)
        return platform in self.enabled_platforms


@dataclass(frozen=True, slots=True)
class VideoAutomationPolicy:
    mode: ExecutionMode
    provider: ProviderPolicy
    budget: BudgetPolicy
    retry: RetryPolicy
    approval: ApprovalMode
    platform: PlatformPolicy
    quality: QualityRequirements

    def __post_init__(self) -> None:
        if self.mode is ExecutionMode.TEST and self.provider.allow_paid_providers:
            raise ValueError("TEST mode must not allow paid providers")

    @classmethod
    def test_default(cls) -> VideoAutomationPolicy:
        return cls(
            mode=ExecutionMode.TEST,
            provider=ProviderPolicy(
                allow_paid_providers=False,
                allowed_provider_names=("local-test",),
                require_explicit_provider=True,
            ),
            budget=BudgetPolicy(),
            retry=RetryPolicy(max_attempts=1),
            approval=ApprovalMode.BEFORE_PUBLISH,
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

    @classmethod
    def production_default(cls) -> VideoAutomationPolicy:
        return cls(
            mode=ExecutionMode.PRODUCTION,
            provider=ProviderPolicy(
                allow_paid_providers=False,
                require_explicit_provider=True,
            ),
            budget=BudgetPolicy(),
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

    def can_use_provider(self, provider_name: str, *, is_paid: bool) -> bool:
        if self.mode is ExecutionMode.TEST and is_paid:
            return False
        return self.provider.is_provider_allowed(provider_name, is_paid=is_paid)

    def requires_approval_for_paid_provider(self) -> bool:
        return self.approval is ApprovalMode.BEFORE_PAID_PROVIDER

    def requires_approval_before_publish(self) -> bool:
        return self.approval is ApprovalMode.BEFORE_PUBLISH
