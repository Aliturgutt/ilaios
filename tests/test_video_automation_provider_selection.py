"""Tests for deterministic ILAIOS provider selection."""

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
from src.video_automation.models import ProviderRequest, ProviderResult
from src.video_automation.provider_registry import ProviderRegistry
from src.video_automation.provider_selection import (
    ProviderSelectionEngine,
    ProviderSelectionError,
    ProviderSelectionRequest,
)
from src.video_automation.providers import BaseProvider, ProviderCapabilities


class FakeProvider(BaseProvider):
    """Deterministic provider for selection tests."""

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self._validate_request(request)
        return ProviderResult(
            request_id=request.request_id,
            provider_name=self.capabilities.provider_name,
            success=True,
            external_id="result",
        )


def make_provider(
    name: str,
    *,
    operation: str = "generate_video",
    is_paid: bool = False,
) -> FakeProvider:
    return FakeProvider(
        ProviderCapabilities(
            provider_name=name,
            operations=(operation,),
            is_paid=is_paid,
        )
    )


def make_policy(
    *,
    mode: ExecutionMode = ExecutionMode.PRODUCTION,
    allow_paid: bool = False,
    allowed: tuple[str, ...] = (),
    blocked: tuple[str, ...] = (),
    require_explicit: bool = False,
) -> VideoAutomationPolicy:
    return VideoAutomationPolicy(
        mode=mode,
        provider=ProviderPolicy(
            allow_paid_providers=allow_paid,
            allowed_provider_names=allowed,
            blocked_provider_names=blocked,
            require_explicit_provider=require_explicit,
        ),
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


def test_selects_preferred_provider_when_allowed() -> None:
    preferred = make_provider("provider-b")
    registry = ProviderRegistry((make_provider("provider-a"), preferred))
    engine = ProviderSelectionEngine(
        registry=registry,
        policy=make_policy(),
    )

    result = engine.select(
        ProviderSelectionRequest(
            operation="generate_video",
            preferred_provider_name="provider-b",
        )
    )

    assert result.provider is preferred
    assert result.used_fallback is False


def test_selects_first_eligible_provider_in_sorted_order() -> None:
    provider_b = make_provider("provider-b")
    provider_a = make_provider("provider-a")
    registry = ProviderRegistry((provider_b, provider_a))
    engine = ProviderSelectionEngine(
        registry=registry,
        policy=make_policy(),
    )

    result = engine.select(
        ProviderSelectionRequest(operation="generate_video")
    )

    assert result.provider is provider_a
    assert result.used_fallback is False


def test_test_mode_never_selects_paid_provider() -> None:
    free_provider = make_provider("local-test", is_paid=False)
    paid_provider = make_provider("seedance", is_paid=True)
    registry = ProviderRegistry((paid_provider, free_provider))
    engine = ProviderSelectionEngine(
        registry=registry,
        policy=make_policy(mode=ExecutionMode.TEST, allow_paid=False),
    )

    result = engine.select(
        ProviderSelectionRequest(operation="generate_video")
    )

    assert result.provider is free_provider


def test_paid_provider_requires_paid_policy() -> None:
    paid_provider = make_provider("seedance", is_paid=True)
    registry = ProviderRegistry((paid_provider,))
    engine = ProviderSelectionEngine(
        registry=registry,
        policy=make_policy(allow_paid=False),
    )

    with pytest.raises(ProviderSelectionError, match="no eligible provider"):
        engine.select(
            ProviderSelectionRequest(operation="generate_video")
        )


def test_paid_provider_can_be_selected_in_production_when_allowed() -> None:
    paid_provider = make_provider("seedance", is_paid=True)
    registry = ProviderRegistry((paid_provider,))
    engine = ProviderSelectionEngine(
        registry=registry,
        policy=make_policy(allow_paid=True),
    )

    result = engine.select(
        ProviderSelectionRequest(operation="generate_video")
    )

    assert result.provider is paid_provider


def test_allowlist_filters_candidates() -> None:
    provider_a = make_provider("provider-a")
    provider_b = make_provider("provider-b")
    registry = ProviderRegistry((provider_a, provider_b))
    engine = ProviderSelectionEngine(
        registry=registry,
        policy=make_policy(allowed=("provider-b",)),
    )

    result = engine.select(
        ProviderSelectionRequest(operation="generate_video")
    )

    assert result.provider is provider_b


def test_blocklist_filters_candidates() -> None:
    provider_a = make_provider("provider-a")
    provider_b = make_provider("provider-b")
    registry = ProviderRegistry((provider_a, provider_b))
    engine = ProviderSelectionEngine(
        registry=registry,
        policy=make_policy(blocked=("provider-a",)),
    )

    result = engine.select(
        ProviderSelectionRequest(operation="generate_video")
    )

    assert result.provider is provider_b


def test_explicit_provider_policy_requires_preferred_name() -> None:
    registry = ProviderRegistry((make_provider("provider-a"),))
    engine = ProviderSelectionEngine(
        registry=registry,
        policy=make_policy(require_explicit=True),
    )

    with pytest.raises(
        ProviderSelectionError,
        match="requires explicit provider",
    ):
        engine.select(
            ProviderSelectionRequest(operation="generate_video")
        )


def test_explicit_provider_policy_rejects_disallowed_preferred_provider() -> None:
    registry = ProviderRegistry((make_provider("provider-a"),))
    engine = ProviderSelectionEngine(
        registry=registry,
        policy=make_policy(
            blocked=("provider-a",),
            require_explicit=True,
        ),
    )

    with pytest.raises(
        ProviderSelectionError,
        match="unavailable or disallowed",
    ):
        engine.select(
            ProviderSelectionRequest(
                operation="generate_video",
                preferred_provider_name="provider-a",
            )
        )


def test_fallback_selects_next_eligible_provider() -> None:
    provider_b = make_provider("provider-b")
    registry = ProviderRegistry((provider_b,))
    engine = ProviderSelectionEngine(
        registry=registry,
        policy=make_policy(),
    )

    result = engine.select(
        ProviderSelectionRequest(
            operation="generate_video",
            preferred_provider_name="missing-provider",
            allow_fallback=True,
        )
    )

    assert result.provider is provider_b
    assert result.used_fallback is True


def test_disabled_fallback_rejects_missing_preferred_provider() -> None:
    registry = ProviderRegistry((make_provider("provider-b"),))
    engine = ProviderSelectionEngine(
        registry=registry,
        policy=make_policy(),
    )

    with pytest.raises(
        ProviderSelectionError,
        match="could not satisfy request",
    ):
        engine.select(
            ProviderSelectionRequest(
                operation="generate_video",
                preferred_provider_name="missing-provider",
                allow_fallback=False,
            )
        )


def test_unsupported_operation_is_rejected() -> None:
    registry = ProviderRegistry(
        (make_provider("image-provider", operation="generate_image"),)
    )
    engine = ProviderSelectionEngine(
        registry=registry,
        policy=make_policy(),
    )

    with pytest.raises(ProviderSelectionError, match="no eligible provider"):
        engine.select(
            ProviderSelectionRequest(operation="generate_video")
        )
