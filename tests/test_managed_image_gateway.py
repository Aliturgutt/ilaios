from __future__ import annotations

from pathlib import Path

import pytest

from src.image_automation.managed_image_gateway import (
    ManagedImageGateway,
    ManagedImageGatewayError,
)
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
from src.video_automation.managed_credit_store import ManagedCreditLedgerStore
from src.video_automation.managed_credits import ManagedCreditAccount, ProviderCostQuote
from src.video_automation.models import ProviderRequest, ProviderResult
from src.video_automation.providers import ImageGenerationProvider, ProviderCapabilities


class _PaidImageProvider(ImageGenerationProvider):
    def __init__(self) -> None:
        self.calls = 0
        super().__init__(
            ProviderCapabilities(
                provider_name="managed-image-provider",
                operations=("generate_image",),
                is_paid=True,
            )
        )

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self._validate_request(request)
        self.calls += 1
        return ProviderResult(
            request_id=request.request_id,
            provider_name=self.capabilities.provider_name,
            success=True,
            external_id="provider-job-001",
        )


def _policy() -> VideoAutomationPolicy:
    return VideoAutomationPolicy(
        mode=ExecutionMode.PRODUCTION,
        provider=ProviderPolicy(
            allow_paid_providers=True,
            allowed_provider_names=("managed-image-provider",),
            require_explicit_provider=True,
        ),
        budget=BudgetPolicy(),
        retry=RetryPolicy(max_attempts=1),
        approval=ApprovalMode.BEFORE_PAID_PROVIDER,
        platform=PlatformPolicy(enabled_platforms=("youtube",)),
        quality=QualityRequirements(
            width=1024,
            height=1024,
            fps=1.0,
            min_duration_seconds=1.0,
            max_duration_seconds=1.0,
        ),
    )


def _request() -> ProviderRequest:
    return ProviderRequest(
        request_id="image-paid-request-001",
        job_id="image-job-001",
        provider_name="managed-image-provider",
        operation="generate_image",
        payload={
            "model_id": "managed/image-premium",
            "routing_decision_id": "route-image-001",
        },
    )


def _account() -> ManagedCreditAccount:
    return ManagedCreditAccount(
        tenant_id="tenant-001",
        user_id="user-001",
        available_microusd=2_000_000,
    )


def _quote() -> ProviderCostQuote:
    return ProviderCostQuote(
        provider_name="managed-image-provider",
        model_id="managed/image-premium",
        estimated_cost_microusd=100_000,
        max_cost_microusd=150_000,
    )


def test_managed_image_fallback_reuses_durable_credit_and_side_effect_ledgers(
    tmp_path: Path,
) -> None:
    store = ManagedCreditLedgerStore(tmp_path)
    account = store.seed_account(_account())
    provider = _PaidImageProvider()
    gateway = ManagedImageGateway(policy=_policy(), credit_store=store)

    result = gateway.submit(
        account=account,
        request=_request(),
        quote=_quote(),
        routing_decision_id="route-image-001",
        provider=provider,
    )

    assert result.success
    assert result.external_id == "provider-job-001"
    assert provider.calls == 1
    persisted = store.get_account(tenant_id="tenant-001", user_id="user-001")
    assert persisted.reserved_microusd == 150_000


def test_same_paid_image_request_is_never_blindly_submitted_twice(tmp_path: Path) -> None:
    store = ManagedCreditLedgerStore(tmp_path)
    account = store.seed_account(_account())
    provider = _PaidImageProvider()
    gateway = ManagedImageGateway(policy=_policy(), credit_store=store)
    request = _request()

    gateway.submit(
        account=account,
        request=request,
        quote=_quote(),
        routing_decision_id="route-image-001",
        provider=provider,
    )

    with pytest.raises(ManagedImageGatewayError, match="side-effect history"):
        gateway.submit(
            account=store.get_account(tenant_id="tenant-001", user_id="user-001"),
            request=request,
            quote=_quote(),
            routing_decision_id="route-image-001",
            provider=provider,
        )

    assert provider.calls == 1
