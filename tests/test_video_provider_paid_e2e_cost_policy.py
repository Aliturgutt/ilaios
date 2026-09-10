from __future__ import annotations

import inspect
from collections.abc import Mapping
from pathlib import Path

import pytest

from src.video_automation import provider_production_certification
from src.video_automation.generation_job_polling import ProviderJobStatus
from src.video_automation.managed_credit_store import ManagedCreditLedgerStore
from src.video_automation.managed_credits import ManagedCreditAccount, ProviderCostQuote
from src.video_automation.openrouter_managed_video_provider import OPENROUTER_MANAGED_PROVIDER_NAME
from src.video_automation.openrouter_managed_video_runtime import (
    OpenRouterManagedVideoGenerationJobPoller,
    actual_cost_microusd_from_observation,
)
from src.video_automation.openrouter_video_provider import (
    OpenRouterByteResponse,
    OpenRouterJsonResponse,
    OpenRouterTransport,
)


class _Transport(OpenRouterTransport):
    def __init__(self, payload: dict[str, object]) -> None:
        self._response = OpenRouterJsonResponse(200, payload)

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        return self._response

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        raise AssertionError("paid POST is outside this cost-policy unit test")

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        raise AssertionError("asset retrieval is outside this cost-policy unit test")


def test_paid_terminal_cost_may_be_positive() -> None:
    poller = OpenRouterManagedVideoGenerationJobPoller(
        "server-secret",
        transport=_Transport(
            {
                "id": "job-paid-001",
                "status": "completed",
                "usage": {"cost": "0.170000"},
            }
        ),
    )
    observation = poller.poll("job-paid-001")
    assert observation.status is ProviderJobStatus.SUCCEEDED
    assert actual_cost_microusd_from_observation(observation) == 170_000


def test_managed_credit_settlement_accepts_cost_within_reserved_ceiling(tmp_path: Path) -> None:
    store = ManagedCreditLedgerStore(tmp_path / "credits")
    account = ManagedCreditAccount(
        tenant_id="tenant",
        user_id="user",
        available_microusd=1_000_000,
    )
    quote = ProviderCostQuote(
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        model_id="paid-video-model",
        estimated_cost_microusd=170_000,
        max_cost_microusd=200_000,
    )
    outcome = store.reserve(
        account=account,
        request_id="request-1",
        routing_decision_id="route-1",
        quote=quote,
    )
    settled = store.settle(
        authorization_id=outcome.authorization.authorization_id,
        actual_cost_microusd=170_000,
        provider_job_id="job-1",
    )
    assert settled.settlement.actual_cost_microusd == 170_000


def test_managed_credit_settlement_fails_above_reserved_ceiling(tmp_path: Path) -> None:
    store = ManagedCreditLedgerStore(tmp_path / "credits")
    account = ManagedCreditAccount(
        tenant_id="tenant",
        user_id="user",
        available_microusd=1_000_000,
    )
    quote = ProviderCostQuote(
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        model_id="paid-video-model",
        estimated_cost_microusd=170_000,
        max_cost_microusd=200_000,
    )
    outcome = store.reserve(
        account=account,
        request_id="request-1",
        routing_decision_id="route-1",
        quote=quote,
    )
    with pytest.raises(Exception, match="exceeded authorized maximum"):
        store.settle(
            authorization_id=outcome.authorization.authorization_id,
            actual_cost_microusd=200_001,
            provider_job_id="job-1",
        )


def test_paid_certification_contains_no_legacy_customer_payment_flow() -> None:
    source = inspect.getsource(provider_production_certification)
    assert "OpenRouterManagedVideoGenerationJobPoller" in source
    assert "OpenRouterVideoGenerationJobPoller(" not in source
    assert '"cost_mode": "MANAGED_CREDIT_BOUNDED"' in source
    assert "PaymentAuthorization" not in source
    assert "gross_customer_price_microusd" not in source
    assert 'receipt["customer_quote"]' not in source
    assert "commercial_reconciliation" not in source
