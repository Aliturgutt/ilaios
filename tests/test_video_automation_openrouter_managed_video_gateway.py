from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from src.video_automation.commercial_quote import CommercialDispatchAuthority
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
from src.video_automation.openrouter_video_webhook import OpenRouterVideoWebhookStore

_NOW = 1_000_000


class _Transport(OpenRouterTransport):
    def __init__(self, catalog_payload: Mapping[str, object]) -> None:
        self.catalog_payload = catalog_payload
        self.get_calls = 0
        self.post_bodies: list[Mapping[str, object]] = []

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        self.post_bodies.append(body)
        return OpenRouterJsonResponse(202, {"id": "provider-job-001", "status": "pending"})

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        self.get_calls += 1
        return OpenRouterJsonResponse(200, self.catalog_payload)

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        raise AssertionError("gateway submit must not download content")


def _catalog(
    *,
    model_id: str = "kwaivgi/kling-v3.0-pro",
    pricing: Mapping[str, str] | None = None,
) -> dict[str, object]:
    return {
        "data": [
            {
                "id": model_id,
                "canonical_slug": model_id,
                "name": "managed model",
                "generate_audio": True,
                "supported_aspect_ratios": ["16:9"],
                "supported_durations": [4, 8],
                "supported_frame_images": ["first_frame", "last_frame"],
                "supported_resolutions": ["720p"],
                "supported_sizes": None,
                "allowed_passthrough_parameters": [],
                "pricing_skus": {"generate": "0.50"} if pricing is None else pricing,
            }
        ]
    }


def _request(
    *,
    model_id: str = "kwaivgi/kling-v3.0-pro",
    duration: int = 4,
    resolution: str = "720p",
) -> ProviderRequest:
    return ProviderRequest(
        request_id="request-001",
        job_id="job-001",
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        operation="video.generate",
        payload={
            "model_id": model_id,
            "request_count": 1,
            "items_json": json.dumps(
                [
                    {
                        "request_id": "request-001",
                        "shot_id": "shot-001",
                        "prompt_text": "cinematic governed scene",
                        "duration_seconds": duration,
                        "aspect_ratio": "16:9",
                        "output_count": 1,
                        "resolution": resolution,
                        "generate_audio": True,
                    }
                ],
                separators=(",", ":"),
            ),
        },
    )


def _account() -> ManagedCreditAccount:
    return ManagedCreditAccount(
        tenant_id="tenant-001",
        user_id="user-001",
        available_microusd=2_000_000,
    )


def _quote(model_id: str = "kwaivgi/kling-v3.0-pro") -> ProviderCostQuote:
    return ProviderCostQuote(
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        model_id=model_id,
        estimated_cost_microusd=400_000,
        max_cost_microusd=500_000,
    )


def _gateway(
    tmp_path: Path,
    transport: _Transport,
) -> tuple[OpenRouterManagedVideoGateway, OpenRouterVideoCatalogClient]:
    clock = lambda: float(_NOW)
    catalog = OpenRouterVideoCatalogClient(
        "server-secret",
        transport=transport,
        clock=clock,
    )
    return (
        OpenRouterManagedVideoGateway(
            api_key="server-secret",
            policy=managed_credit_production_policy(
                max_cost_per_video=5.0,
                max_daily_cost=50.0,
                max_retry_cost=1.0,
            ),
            credit_store=ManagedCreditLedgerStore(tmp_path / "credits"),
            catalog=catalog,
            transport=transport,
            webhook_store=OpenRouterVideoWebhookStore(tmp_path / "webhooks"),
            callback_url="https://ilaios.example/openrouter/video-webhook",
            clock=clock,
        ),
        catalog,
    )


def _authority(
    *,
    model_id: str = "kwaivgi/kling-v3.0-pro",
    pricing_fingerprint: str,
    max_cost_microusd: int = 500_000,
    expires_at: int = _NOW + 300,
) -> CommercialDispatchAuthority:
    return CommercialDispatchAuthority(
        authority_sha256="authority-evidence",
        quote_id="customer-quote-001",
        quote_sha256="quote-evidence",
        payment_authorization_id="payment-auth-001",
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        model_id=model_id,
        pricing_fingerprint=pricing_fingerprint,
        provider_cost_ceiling_microusd=max_cost_microusd,
        issued_at_epoch_s=_NOW - 1,
        expires_at_epoch_s=expires_at,
    )


def _catalog_bound_authority(
    catalog: OpenRouterVideoCatalogClient,
    *,
    model_id: str = "kwaivgi/kling-v3.0-pro",
) -> CommercialDispatchAuthority:
    catalog.paid_eligible_models()
    snapshot = catalog.last_good_snapshot
    assert snapshot is not None
    return _authority(
        model_id=model_id,
        pricing_fingerprint=snapshot.catalog_digest,
    )


def test_missing_commercial_authority_blocks_before_any_network(tmp_path: Path) -> None:
    transport = _Transport(_catalog())
    gateway, _catalog_client = _gateway(tmp_path, transport)

    with pytest.raises(OpenRouterManagedVideoGatewayError, match="authority is required"):
        gateway.submit(
            account=_account(),
            request=_request(),
            quote=_quote(),
            routing_decision_id="route-001",
            commercial_authority=None,  # type: ignore[arg-type]
        )

    assert transport.get_calls == 0
    assert transport.post_bodies == []


def test_live_kling_catalog_can_pass_governed_paid_dispatch(tmp_path: Path) -> None:
    transport = _Transport(_catalog())
    gateway, catalog = _gateway(tmp_path, transport)
    authority = _catalog_bound_authority(catalog)

    result = gateway.submit(
        account=_account(),
        request=_request(),
        quote=_quote(),
        routing_decision_id="route-001",
        commercial_authority=authority,
    )

    assert result.success
    assert result.external_id == "provider-job-001"
    assert len(transport.post_bodies) == 1
    body = transport.post_bodies[0]
    assert body["model"] == "kwaivgi/kling-v3.0-pro"
    assert body["callback_url"] == "https://ilaios.example/openrouter/video-webhook"
    assert result.metadata["routing_decision_id"] == "route-001"
    assert result.metadata["catalog_digest"] == authority.pricing_fingerprint


def test_capability_mismatch_blocks_before_paid_post(tmp_path: Path) -> None:
    transport = _Transport(_catalog())
    gateway, catalog = _gateway(tmp_path, transport)
    authority = _catalog_bound_authority(catalog)

    with pytest.raises(OpenRouterManagedVideoGatewayError, match="duration"):
        gateway.submit(
            account=_account(),
            request=_request(duration=5),
            quote=_quote(),
            routing_decision_id="route-001",
            commercial_authority=authority,
        )

    assert transport.post_bodies == []


def test_unknown_pricing_blocks_before_paid_network_side_effect(tmp_path: Path) -> None:
    transport = _Transport(_catalog(pricing={}))
    gateway, _catalog_client = _gateway(tmp_path, transport)

    with pytest.raises(OpenRouterManagedVideoGatewayError, match="valid pricing"):
        gateway.submit(
            account=_account(),
            request=_request(),
            quote=_quote(),
            routing_decision_id="route-001",
            commercial_authority=_authority(pricing_fingerprint="unverified"),
        )

    assert transport.post_bodies == []


def test_catalog_change_after_quote_blocks_before_paid_post(tmp_path: Path) -> None:
    transport = _Transport(_catalog())
    gateway, _catalog_client = _gateway(tmp_path, transport)

    with pytest.raises(OpenRouterManagedVideoGatewayError, match="catalog changed"):
        gateway.submit(
            account=_account(),
            request=_request(),
            quote=_quote(),
            routing_decision_id="route-001",
            commercial_authority=_authority(pricing_fingerprint="stale-catalog-digest"),
        )

    assert transport.post_bodies == []


def test_expired_commercial_authority_blocks_before_catalog_network(tmp_path: Path) -> None:
    transport = _Transport(_catalog())
    gateway, _catalog_client = _gateway(tmp_path, transport)

    with pytest.raises(OpenRouterManagedVideoGatewayError, match="expired"):
        gateway.submit(
            account=_account(),
            request=_request(),
            quote=_quote(),
            routing_decision_id="route-001",
            commercial_authority=_authority(
                pricing_fingerprint="unused",
                expires_at=_NOW,
            ),
        )

    assert transport.get_calls == 0
    assert transport.post_bodies == []


def test_commercial_cost_ceiling_blocks_before_catalog_network(tmp_path: Path) -> None:
    transport = _Transport(_catalog())
    gateway, _catalog_client = _gateway(tmp_path, transport)

    with pytest.raises(OpenRouterManagedVideoGatewayError, match="cost exceeds"):
        gateway.submit(
            account=_account(),
            request=_request(),
            quote=_quote(),
            routing_decision_id="route-001",
            commercial_authority=_authority(
                pricing_fingerprint="unused",
                max_cost_microusd=499_999,
            ),
        )

    assert transport.get_calls == 0
    assert transport.post_bodies == []


def test_catalog_model_does_not_override_governed_family_policy(tmp_path: Path) -> None:
    model_id = "google/veo-3.1"
    transport = _Transport(_catalog(model_id=model_id))
    gateway, _catalog_client = _gateway(tmp_path, transport)

    with pytest.raises(OpenRouterManagedVideoGatewayError, match="paid-eligible"):
        gateway.submit(
            account=_account(),
            request=_request(model_id=model_id),
            quote=_quote(model_id),
            routing_decision_id="route-001",
            commercial_authority=_authority(
                model_id=model_id,
                pricing_fingerprint="unused",
            ),
        )

    assert transport.post_bodies == []
