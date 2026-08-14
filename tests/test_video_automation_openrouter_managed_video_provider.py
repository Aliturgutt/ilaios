from __future__ import annotations

import json
from collections.abc import Mapping

import pytest

from src.video_automation.managed_credit_policy import (
    managed_credit_production_policy,
)
from src.video_automation.managed_credits import (
    ManagedCreditAccount,
    ProviderCostQuote,
)
from src.video_automation.managed_provider_execution import (
    ManagedPaidVideoExecutionCoordinator,
    ManagedPaidVideoExecutionError,
)
from src.video_automation.models import ProviderRequest
from src.video_automation.openrouter_managed_video_provider import (
    OPENROUTER_MANAGED_PROVIDER_NAME,
    SEEDANCE_MANAGED_MODEL_IDS,
    OpenRouterManagedVideoGenerationProvider,
)
from src.video_automation.openrouter_video_provider import (
    OpenRouterByteResponse,
    OpenRouterJsonResponse,
    OpenRouterTransport,
)


class _Transport(OpenRouterTransport):
    def __init__(self) -> None:
        self.post_calls: list[
            tuple[str, Mapping[str, str], Mapping[str, object], float]
        ] = []

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        self.post_calls.append((url, headers, body, timeout_seconds))
        # Regression guard for the previously observed MappingProxyType body bug.
        json.dumps(body)
        return OpenRouterJsonResponse(
            202,
            {"id": "video-job-001", "status": "pending"},
        )

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        raise AssertionError("polling is outside submit-provider unit scope")

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        raise AssertionError("asset retrieval is outside submit-provider unit scope")


def _request(
    *,
    model_id: str = "bytedance/seedance-2.0-fast",
) -> ProviderRequest:
    item = {
        "request_id": "request-001",
        "shot_id": "shot-001",
        "prompt_text": "cinematic original product scene",
        "duration_seconds": 4,
        "aspect_ratio": "16:9",
        "output_count": 1,
        "resolution": "480p",
        "generate_audio": False,
    }
    return ProviderRequest(
        request_id="request-001",
        job_id="job-001",
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        operation="video.generate",
        payload={
            "model_id": model_id,
            "request_count": 1,
            "items_json": json.dumps([item], separators=(",", ":")),
        },
    )


def _policy():
    return managed_credit_production_policy(
        max_cost_per_video=5.0,
        max_daily_cost=50.0,
        max_retry_cost=1.0,
    )


def test_managed_provider_is_paid_and_server_credential_owned() -> None:
    provider = OpenRouterManagedVideoGenerationProvider("server-secret", transport=_Transport())
    assert provider.capabilities.is_paid
    assert provider.capabilities.provider_name == OPENROUTER_MANAGED_PROVIDER_NAME
    assert provider.capabilities.metadata["credential_owner"] == "ILAIOS"
    assert provider.capabilities.metadata["billing_authority"] == "managed_credits"


def test_all_governed_seedance_paid_models_are_available_to_managed_provider() -> None:
    assert SEEDANCE_MANAGED_MODEL_IDS == (
        "bytedance/seedance-1-5-pro",
        "bytedance/seedance-2.0-fast",
        "bytedance/seedance-2.0",
    )


def test_raw_paid_provider_request_without_credit_authorization_fails_before_network() -> None:
    transport = _Transport()
    result = OpenRouterManagedVideoGenerationProvider(
        "server-secret", transport=transport
    ).execute(_request())
    assert not result.success
    assert result.error_code == "invalid_request"
    assert "credit_authorization_id" in (result.error_message or "")
    assert transport.post_calls == []


def test_credit_coordinator_binds_tenant_user_and_reservation_before_network() -> None:
    account = ManagedCreditAccount(
        tenant_id="tenant-001",
        user_id="user-001",
        available_microusd=5_000_000,
    )
    request = _request()
    quote = ProviderCostQuote(
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        model_id="bytedance/seedance-2.0-fast",
        estimated_cost_microusd=600_000,
        max_cost_microusd=1_000_000,
    )
    plan = ManagedPaidVideoExecutionCoordinator(policy=_policy()).authorize(
        account=account,
        request=request,
        quote=quote,
    )

    assert plan.account.available_microusd == 4_000_000
    assert plan.account.reserved_microusd == 1_000_000
    assert plan.request.payload["tenant_id"] == "tenant-001"
    assert plan.request.payload["user_id"] == "user-001"
    assert plan.request.payload["credit_reserved_microusd"] == 1_000_000
    authorization_id = plan.request.payload["credit_authorization_id"]
    assert isinstance(authorization_id, str)
    assert len(authorization_id) == 64


def test_authorized_request_submits_serializable_seedance_body() -> None:
    transport = _Transport()
    provider = OpenRouterManagedVideoGenerationProvider(
        "server-secret",
        transport=transport,
    )
    account = ManagedCreditAccount(
        tenant_id="tenant-001",
        user_id="user-001",
        available_microusd=5_000_000,
    )
    quote = ProviderCostQuote(
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        model_id="bytedance/seedance-2.0-fast",
        estimated_cost_microusd=600_000,
        max_cost_microusd=1_000_000,
    )
    coordinator = ManagedPaidVideoExecutionCoordinator(policy=_policy())
    plan = coordinator.authorize(account=account, request=_request(), quote=quote)
    result = coordinator.execute(provider=provider, plan=plan)

    assert result.success
    assert result.external_id == "video-job-001"
    assert result.metadata["credit_authorization_id"] == plan.authorization.authorization_id
    assert "server-secret" not in str(result.metadata)
    assert len(transport.post_calls) == 1
    url, headers, body, timeout = transport.post_calls[0]
    assert url == "https://openrouter.ai/api/v1/videos"
    assert headers["Authorization"] == "Bearer server-secret"
    assert body["model"] == "bytedance/seedance-2.0-fast"
    assert body["duration"] == 4
    assert timeout > 0


def test_unknown_or_free_suffix_seedance_model_is_not_in_managed_paid_allowlist() -> None:
    transport = _Transport()
    provider = OpenRouterManagedVideoGenerationProvider(
        "server-secret", transport=transport
    )
    account = ManagedCreditAccount(
        tenant_id="tenant-001",
        user_id="user-001",
        available_microusd=5_000_000,
    )
    request = _request(model_id="bytedance/seedance-2.0-fast:free")
    quote = ProviderCostQuote(
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        model_id="bytedance/seedance-2.0-fast:free",
        estimated_cost_microusd=600_000,
        max_cost_microusd=1_000_000,
    )
    plan = ManagedPaidVideoExecutionCoordinator(policy=_policy()).authorize(
        account=account,
        request=request,
        quote=quote,
    )
    result = provider.execute(plan.request)
    assert not result.success
    assert "allowlist" in (result.error_message or "")
    assert transport.post_calls == []


def test_default_production_policy_still_cannot_be_used_as_paid_credit_policy() -> None:
    from src.video_automation.configuration import VideoAutomationPolicy

    coordinator = ManagedPaidVideoExecutionCoordinator(
        policy=VideoAutomationPolicy.production_default()
    )
    account = ManagedCreditAccount(
        tenant_id="tenant-001",
        user_id="user-001",
        available_microusd=5_000_000,
    )
    quote = ProviderCostQuote(
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        model_id="bytedance/seedance-2.0-fast",
        estimated_cost_microusd=600_000,
        max_cost_microusd=1_000_000,
    )
    with pytest.raises(ManagedPaidVideoExecutionError, match="not permitted"):
        coordinator.authorize(account=account, request=_request(), quote=quote)
