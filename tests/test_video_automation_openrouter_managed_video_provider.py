from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from src.video_automation.configuration import VideoAutomationPolicy
from src.video_automation.managed_credit_policy import managed_credit_production_policy
from src.video_automation.managed_credit_store import (
    ManagedCreditLedgerStore,
    ProviderSideEffectLedger,
    ProviderSubmissionState,
    ReconciliationState,
)
from src.video_automation.managed_credits import ManagedCreditAccount, ProviderCostQuote
from src.video_automation.managed_provider_execution import (
    ManagedPaidVideoExecutionCoordinator,
    ManagedPaidVideoExecutionError,
)
from src.video_automation.models import ProviderRequest, ProviderResult
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
    def __init__(self, *, fail_transport: bool = False) -> None:
        self.fail_transport = fail_transport
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
        json.dumps(body)
        if self.fail_transport:
            raise TimeoutError("response lost after submit")
        return OpenRouterJsonResponse(202, {"id": "video-job-001", "status": "pending"})

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
    item_extra: Mapping[str, object] | None = None,
) -> ProviderRequest:
    item: dict[str, object] = {
        "request_id": "request-001",
        "shot_id": "shot-001",
        "prompt_text": "cinematic original product scene",
        "duration_seconds": 4,
        "aspect_ratio": "16:9",
        "output_count": 1,
        "resolution": "480p",
        "generate_audio": False,
    }
    if item_extra:
        item.update(item_extra)
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


def _policy() -> VideoAutomationPolicy:
    return managed_credit_production_policy(
        max_cost_per_video=5.0,
        max_daily_cost=50.0,
        max_retry_cost=1.0,
    )


def _account() -> ManagedCreditAccount:
    return ManagedCreditAccount(
        tenant_id="tenant-001",
        user_id="user-001",
        available_microusd=5_000_000,
    )


def _quote(*, model_id: str = "bytedance/seedance-2.0-fast") -> ProviderCostQuote:
    return ProviderCostQuote(
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        model_id=model_id,
        estimated_cost_microusd=600_000,
        max_cost_microusd=1_000_000,
    )


def _coordinator(root: Path) -> ManagedPaidVideoExecutionCoordinator:
    return ManagedPaidVideoExecutionCoordinator(
        policy=_policy(),
        store=ManagedCreditLedgerStore(root),
    )


def _execute_authorized(
    tmp_path: Path,
    request: ProviderRequest,
) -> tuple[_Transport, ProviderResult]:
    transport = _Transport()
    provider = OpenRouterManagedVideoGenerationProvider("server-secret", transport=transport)
    store = ManagedCreditLedgerStore(tmp_path)
    coordinator = ManagedPaidVideoExecutionCoordinator(policy=_policy(), store=store)
    plan = coordinator.authorize(
        account=_account(),
        request=request,
        quote=_quote(),
        routing_decision_id="route-001",
    )
    result = coordinator.execute(provider=provider, plan=plan)
    return transport, result


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


def test_credit_coordinator_persists_route_tenant_user_and_reservation_before_network(
    tmp_path: Path,
) -> None:
    store = ManagedCreditLedgerStore(tmp_path)
    plan = ManagedPaidVideoExecutionCoordinator(policy=_policy(), store=store).authorize(
        account=_account(),
        request=_request(),
        quote=_quote(),
        routing_decision_id="route-001",
    )

    assert plan.account.available_microusd == 4_000_000
    assert plan.account.reserved_microusd == 1_000_000
    assert plan.routing_decision_id == "route-001"
    assert plan.request.payload["tenant_id"] == "tenant-001"
    assert plan.request.payload["user_id"] == "user-001"
    assert plan.request.payload["routing_decision_id"] == "route-001"
    assert plan.request.payload["credit_reserved_microusd"] == 1_000_000
    authorization_id = plan.request.payload["credit_authorization_id"]
    assert isinstance(authorization_id, str)
    assert len(authorization_id) == 64
    restarted = ManagedCreditLedgerStore(tmp_path)
    assert restarted.get_account(
        tenant_id="tenant-001", user_id="user-001"
    ).reserved_microusd == 1_000_000


def test_authorized_request_submits_exactly_once_and_persists_external_job_id(
    tmp_path: Path,
) -> None:
    transport = _Transport()
    provider = OpenRouterManagedVideoGenerationProvider(
        "server-secret",
        transport=transport,
    )
    store = ManagedCreditLedgerStore(tmp_path)
    coordinator = ManagedPaidVideoExecutionCoordinator(policy=_policy(), store=store)
    plan = coordinator.authorize(
        account=_account(),
        request=_request(),
        quote=_quote(),
        routing_decision_id="route-001",
    )
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
    side_effect = ProviderSideEffectLedger(store).get("request-001")
    assert side_effect.submission_state is ProviderSubmissionState.ACCEPTED
    assert side_effect.external_job_id == "video-job-001"

    with pytest.raises(Exception, match="reconcile instead of redispatch"):
        coordinator.execute(provider=provider, plan=plan)
    assert len(transport.post_calls) == 1


def test_authorized_native_references_reach_openrouter_input_references(
    tmp_path: Path,
) -> None:
    reference = {
        "url": "https://relay.example/reference/product",
        "role": "product",
        "sha256": "a" * 64,
    }
    transport, result = _execute_authorized(
        tmp_path,
        _request(item_extra={"native_reference_images": [reference]}),
    )

    assert result.success
    body = transport.post_calls[0][2]
    assert body["input_references"] == [
        {
            "type": "image_url",
            "image_url": {"url": "https://relay.example/reference/product"},
        }
    ]
    assert "frame_images" not in body


def test_exact_frame_reference_takes_precedence_over_input_references(
    tmp_path: Path,
) -> None:
    transport, result = _execute_authorized(
        tmp_path,
        _request(
            item_extra={
                "first_frame_url": "https://relay.example/reference/frame",
                "native_reference_images": [
                    {
                        "url": "https://relay.example/reference/product",
                        "role": "product",
                        "sha256": "a" * 64,
                    }
                ],
            }
        ),
    )

    assert result.success
    body = transport.post_calls[0][2]
    assert body["frame_images"] == [
        {
            "type": "image_url",
            "image_url": {"url": "https://relay.example/reference/frame"},
            "frame_type": "first_frame",
        }
    ]
    assert "input_references" not in body


def test_transport_timeout_is_ambiguous_and_cannot_be_blindly_retried(
    tmp_path: Path,
) -> None:
    transport = _Transport(fail_transport=True)
    provider = OpenRouterManagedVideoGenerationProvider(
        "server-secret", transport=transport
    )
    store = ManagedCreditLedgerStore(tmp_path)
    coordinator = ManagedPaidVideoExecutionCoordinator(policy=_policy(), store=store)
    plan = coordinator.authorize(
        account=_account(),
        request=_request(),
        quote=_quote(),
        routing_decision_id="route-001",
    )

    result = coordinator.execute(provider=provider, plan=plan)
    assert not result.success
    assert result.error_code == "transport_error"
    ambiguous = ProviderSideEffectLedger(store).get("request-001")
    assert ambiguous.submission_state is ProviderSubmissionState.AMBIGUOUS
    assert ambiguous.reconciliation_state is ReconciliationState.PENDING

    with pytest.raises(Exception, match="reconcile instead of redispatch"):
        coordinator.execute(provider=provider, plan=plan)
    assert len(transport.post_calls) == 1


def test_unknown_or_free_suffix_seedance_model_is_not_in_managed_paid_allowlist(
    tmp_path: Path,
) -> None:
    transport = _Transport()
    provider = OpenRouterManagedVideoGenerationProvider(
        "server-secret", transport=transport
    )
    model_id = "bytedance/seedance-2.0-fast:free"
    coordinator = _coordinator(tmp_path)
    plan = coordinator.authorize(
        account=_account(),
        request=_request(model_id=model_id),
        quote=_quote(model_id=model_id),
        routing_decision_id="route-001",
    )
    result = coordinator.execute(provider=provider, plan=plan)
    assert not result.success
    assert "catalog" in (result.error_message or "")
    assert transport.post_calls == []


def test_default_production_policy_still_cannot_be_used_as_paid_credit_policy(
    tmp_path: Path,
) -> None:
    coordinator = ManagedPaidVideoExecutionCoordinator(
        policy=VideoAutomationPolicy.production_default(),
        store=ManagedCreditLedgerStore(tmp_path),
    )
    with pytest.raises(ManagedPaidVideoExecutionError, match="not permitted"):
        coordinator.authorize(
            account=_account(),
            request=_request(),
            quote=_quote(),
            routing_decision_id="route-001",
        )
