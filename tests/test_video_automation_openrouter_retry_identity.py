from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from src.video_automation.commercial_admission import (
    CommercialAdmissionEngine,
    CommercialPricingPolicy,
    PaymentAuthorization,
    ProviderPricingSnapshot,
    TaxProfile,
    VideoCostEnvelope,
)
from src.video_automation.commercial_store import CommercialAuthorityStore
from src.video_automation.managed_credit_policy import managed_credit_production_policy
from src.video_automation.managed_credit_store import ManagedCreditLedgerStore
from src.video_automation.managed_credits import ManagedCreditAccount, ProviderCostQuote
from src.video_automation.models import ProviderRequest
from src.video_automation.openrouter_managed_video_gateway import (
    OpenRouterManagedVideoGateway,
    OpenRouterManagedVideoGatewayError,
)
from src.video_automation.openrouter_managed_video_provider import (
    OPENROUTER_MANAGED_PROVIDER_NAME,
)
from src.video_automation.openrouter_video_catalog import OpenRouterVideoCatalogClient
from src.video_automation.openrouter_video_provider import (
    OpenRouterByteResponse,
    OpenRouterJsonResponse,
    OpenRouterTransport,
)

_NOW = 1_000_000


class _RejectedTransport(OpenRouterTransport):
    def __init__(self) -> None:
        self.posts = 0
        self.gets = 0

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        self.posts += 1
        return OpenRouterJsonResponse(
            400,
            {"error": {"code": "invalid_request", "message": "provider rejected"}},
        )

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        self.gets += 1
        return OpenRouterJsonResponse(
            200,
            {
                "data": [
                    {
                        "id": "bytedance/seedance-2.0",
                        "canonical_slug": "bytedance/seedance-2.0",
                        "name": "Seedance 2.0",
                        "generate_audio": False,
                        "supported_aspect_ratios": ["16:9"],
                        "supported_durations": [4],
                        "supported_frame_images": [],
                        "supported_resolutions": ["480p"],
                        "supported_sizes": None,
                        "allowed_passthrough_parameters": [],
                        "pricing_skus": {"generate": "0.50"},
                    }
                ]
            },
        )

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        raise AssertionError("retry identity test must not download content")


def _request() -> ProviderRequest:
    return ProviderRequest(
        request_id="request-single-use",
        job_id="job-001",
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        operation="video.generate",
        payload={
            "model_id": "bytedance/seedance-2.0",
            "request_count": 1,
            "items_json": json.dumps(
                [
                    {
                        "request_id": "request-single-use",
                        "shot_id": "shot-001",
                        "prompt_text": "governed scene",
                        "duration_seconds": 4,
                        "aspect_ratio": "16:9",
                        "output_count": 1,
                        "resolution": "480p",
                        "generate_audio": False,
                    }
                ],
                separators=(",", ":"),
            ),
        },
    )


def test_failed_paid_request_requires_new_governed_retry_identity(tmp_path: Path) -> None:
    def clock() -> float:
        return float(_NOW)

    transport = _RejectedTransport()
    credit_store = ManagedCreditLedgerStore(tmp_path / "credits")
    commercial_store = CommercialAuthorityStore(tmp_path / "commercial")
    catalog = OpenRouterVideoCatalogClient(
        "server-secret", transport=transport, clock=clock
    )
    catalog.paid_eligible_models()
    snapshot = catalog.last_good_snapshot
    assert snapshot is not None

    provider_quote = ProviderCostQuote(
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        model_id="bytedance/seedance-2.0",
        estimated_cost_microusd=400_000,
        max_cost_microusd=500_000,
    )
    pricing = ProviderPricingSnapshot(
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        model_id="bytedance/seedance-2.0",
        pricing_fingerprint=snapshot.catalog_digest,
        observed_at_epoch_s=_NOW - 1,
        expires_at_epoch_s=_NOW + 300,
        estimated_job_cost_microusd=400_000,
        max_job_cost_microusd=500_000,
    )
    engine = CommercialAdmissionEngine(CommercialPricingPolicy())
    locked_quote = engine.create_locked_quote(
        quote_id="quote-retry-identity",
        now_epoch_s=_NOW,
        tax_profile=TaxProfile.turkey_general_vat(),
        pricing=pricing,
        costs=VideoCostEnvelope(provider_generation_microusd=500_000),
        duration_seconds=4,
        aggregate_generated_seconds=4,
        resolution="480p",
        shot_count=1,
    )
    payment = PaymentAuthorization(
        payment_authorization_id="payment-retry-identity",
        quote_id=locked_quote.quote_id,
        secured_amount_microusd=locked_quote.gross_customer_price_microusd,
        secured_at_epoch_s=_NOW,
    )
    authority = engine.authorize_paid_dispatch(
        now_epoch_s=_NOW,
        quote=locked_quote,
        payment=payment,
        current_pricing=pricing,
        provider_quote=provider_quote,
    )
    commercial_store.record_quote(locked_quote)
    commercial_store.record_payment(payment)
    commercial_store.record_authority(authority)

    gateway = OpenRouterManagedVideoGateway(
        api_key="server-secret",
        policy=managed_credit_production_policy(
            max_cost_per_video=5.0,
            max_daily_cost=50.0,
            max_retry_cost=1.0,
        ),
        credit_store=credit_store,
        commercial_store=commercial_store,
        catalog=catalog,
        transport=transport,
        clock=clock,
    )
    account = ManagedCreditAccount(
        tenant_id="tenant-001",
        user_id="user-001",
        available_microusd=2_000_000,
    )

    first = gateway.submit(
        account=account,
        request=_request(),
        quote=provider_quote,
        routing_decision_id="route-001",
        commercial_authority=authority,
    )
    assert not first.success
    assert transport.posts == 1

    with pytest.raises(
        OpenRouterManagedVideoGatewayError,
        match="create a new governed retry request",
    ):
        gateway.submit(
            account=account,
            request=_request(),
            quote=provider_quote,
            routing_decision_id="route-001",
            commercial_authority=authority,
        )

    assert transport.posts == 1
