"""Catalog-bound managed OpenRouter dispatch without a second routing authority."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from typing import cast

from .commercial_quote import CommercialDispatchAuthority
from .commercial_store import CommercialAuthorityStore
from .commercial_types import CommercialAdmissionError
from .configuration import VideoAutomationPolicy
from .managed_credit_store import ManagedCreditLedgerStore, ProviderSideEffectLedger
from .managed_credits import ManagedCreditAccount, ManagedCreditError, ProviderCostQuote
from .managed_provider_execution import ManagedPaidVideoExecutionCoordinator
from .models import ProviderRequest, ProviderResult
from .openrouter_frame_references import (
    FrameReferenceRoutingError,
    validate_bound_frame_fields,
)
from .openrouter_managed_video_provider import (
    OPENROUTER_MANAGED_PROVIDER_NAME,
    OpenRouterManagedVideoGenerationProvider,
)
from .openrouter_video_catalog import (
    OpenRouterCatalogError,
    OpenRouterVideoCatalogClient,
    OpenRouterVideoModel,
)
from .openrouter_video_provider import OpenRouterTransport
from .openrouter_video_webhook import OpenRouterVideoWebhookStore


class OpenRouterManagedVideoGatewayError(ValueError):
    """Raised before dispatch when live capability/economic evidence is insufficient."""


class OpenRouterManagedVideoGateway:
    """Bind commercial, catalog and managed-credit evidence to the paid POST boundary."""

    def __init__(
        self,
        *,
        api_key: str,
        policy: VideoAutomationPolicy,
        credit_store: ManagedCreditLedgerStore,
        commercial_store: CommercialAuthorityStore,
        catalog: OpenRouterVideoCatalogClient,
        transport: OpenRouterTransport | None = None,
        webhook_store: OpenRouterVideoWebhookStore | None = None,
        callback_url: str | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not api_key or not api_key.strip():
            raise OpenRouterManagedVideoGatewayError("api_key must not be blank")
        self._api_key = api_key
        self._policy = policy
        self._credit_store = credit_store
        self._commercial_store = commercial_store
        self._catalog = catalog
        self._transport = transport
        self._webhook_store = webhook_store
        self._callback_url = callback_url
        self._clock = clock

    def submit(
        self,
        *,
        account: ManagedCreditAccount,
        request: ProviderRequest,
        quote: ProviderCostQuote,
        routing_decision_id: str,
        commercial_authority: CommercialDispatchAuthority,
    ) -> ProviderResult:
        """Validate durable commercial/catalog facts, then perform at most one paid POST."""

        if request.provider_name != OPENROUTER_MANAGED_PROVIDER_NAME:
            raise OpenRouterManagedVideoGatewayError(
                "request is not bound to the managed OpenRouter provider"
            )
        model_id = _request_model_id(request)
        now_epoch_s = int(self._clock())
        _validate_commercial_authority_before_catalog(
            authority=commercial_authority,
            request=request,
            quote=quote,
            model_id=model_id,
            now_epoch_s=now_epoch_s,
        )
        try:
            self._commercial_store.verify_authority(
                commercial_authority, now_epoch_s=now_epoch_s
            )
        except CommercialAdmissionError as exc:
            raise OpenRouterManagedVideoGatewayError(str(exc)) from exc

        side_effect_ledger = ProviderSideEffectLedger(self._credit_store)
        try:
            side_effect_ledger.get(request.request_id)
        except ManagedCreditError as exc:
            if str(exc) != "provider side effect does not exist":
                raise OpenRouterManagedVideoGatewayError(
                    "paid side-effect history could not be validated"
                ) from exc
        else:
            raise OpenRouterManagedVideoGatewayError(
                "paid request_id already has side-effect history; "
                "create a new governed retry request"
            )

        try:
            eligible = self._catalog.paid_eligible_models()
        except OpenRouterCatalogError as exc:
            snapshot = self._catalog.last_good_snapshot
            if snapshot is not None and not any(
                model.family is not None for model in snapshot.models
            ):
                raise OpenRouterManagedVideoGatewayError(
                    "paid dispatch blocked: no governed paid-eligible candidate"
                ) from exc
            raise OpenRouterManagedVideoGatewayError(str(exc)) from exc
        model_by_id = {model.model_id: model for model in eligible}
        model = model_by_id.get(model_id)
        if model is None:
            raise OpenRouterManagedVideoGatewayError(
                "requested model is not currently paid-eligible"
            )
        _validate_capabilities(request, model)
        snapshot = self._catalog.last_good_snapshot
        if snapshot is None:
            raise OpenRouterManagedVideoGatewayError(
                "catalog lost last-known-good snapshot before dispatch"
            )
        if commercial_authority.pricing_fingerprint != snapshot.catalog_digest:
            raise OpenRouterManagedVideoGatewayError(
                "live pricing/capability catalog changed after quote; requote required"
            )
        now_epoch_s = int(self._clock())
        try:
            commercial_authority.require_valid(now_epoch_s)
            self._commercial_store.verify_authority(
                commercial_authority, now_epoch_s=now_epoch_s
            )
            self._commercial_store.reserve_request(
                authority=commercial_authority,
                request_id=request.request_id,
                provider_quote=quote,
                now_epoch_s=now_epoch_s,
            )
        except CommercialAdmissionError as exc:
            raise OpenRouterManagedVideoGatewayError(str(exc)) from exc

        provider = OpenRouterManagedVideoGenerationProvider(
            self._api_key,
            transport=self._transport,
            approved_model_ids=tuple(sorted(model_by_id)),
            catalog_digest=snapshot.catalog_digest,
            callback_url=self._callback_url,
        )
        coordinator = ManagedPaidVideoExecutionCoordinator(
            policy=self._policy,
            store=self._credit_store,
            side_effect_ledger=side_effect_ledger,
        )
        try:
            plan = coordinator.authorize(
                account=account,
                request=request,
                quote=quote,
                routing_decision_id=routing_decision_id,
            )
        except Exception:
            self._commercial_store.release_request(request.request_id)
            raise
        result = coordinator.execute(provider=provider, plan=plan)
        if result.success:
            if result.external_id is None:
                raise OpenRouterManagedVideoGatewayError(
                    "successful provider result requires external job id"
                )
            if self._webhook_store is not None:
                self._webhook_store.register_job(
                    request_id=request.request_id,
                    provider_job_id=result.external_id,
                )
        return result


def _validate_commercial_authority_before_catalog(
    *,
    authority: CommercialDispatchAuthority,
    request: ProviderRequest,
    quote: ProviderCostQuote,
    model_id: str,
    now_epoch_s: int,
) -> None:
    if not isinstance(authority, CommercialDispatchAuthority):
        raise OpenRouterManagedVideoGatewayError(
            "commercial dispatch authority is required before paid generation"
        )
    try:
        authority.require_valid(now_epoch_s)
    except CommercialAdmissionError as exc:
        raise OpenRouterManagedVideoGatewayError(str(exc)) from exc
    if authority.provider_name != request.provider_name:
        raise OpenRouterManagedVideoGatewayError(
            "commercial authority provider does not match request"
        )
    if authority.provider_name != quote.provider_name:
        raise OpenRouterManagedVideoGatewayError(
            "commercial authority provider does not match provider quote"
        )
    if authority.model_id != model_id or quote.model_id != model_id:
        raise OpenRouterManagedVideoGatewayError(
            "commercial authority/model binding does not match request"
        )
    if quote.max_cost_microusd > authority.provider_cost_ceiling_microusd:
        raise OpenRouterManagedVideoGatewayError(
            "provider request cost exceeds commercial authority ceiling"
        )


def _request_model_id(request: ProviderRequest) -> str:
    value = request.payload.get("model_id")
    if not isinstance(value, str) or not value.strip():
        raise OpenRouterManagedVideoGatewayError("request model_id must be non-empty")
    return value


def _validate_capabilities(request: ProviderRequest, model: OpenRouterVideoModel) -> None:
    if request.payload.get("request_count") != 1:
        raise OpenRouterManagedVideoGatewayError(
            "catalog capability gate requires one generation item"
        )
    items_json = request.payload.get("items_json")
    if not isinstance(items_json, str):
        raise OpenRouterManagedVideoGatewayError("items_json must be a string")
    try:
        parsed = json.loads(items_json)
    except json.JSONDecodeError as exc:
        raise OpenRouterManagedVideoGatewayError("items_json is invalid JSON") from exc
    if not isinstance(parsed, list) or len(parsed) != 1 or not isinstance(parsed[0], dict):
        raise OpenRouterManagedVideoGatewayError(
            "items_json must contain exactly one object"
        )
    item = cast(Mapping[str, object], parsed[0])
    try:
        validate_bound_frame_fields(item=item, model=model)
    except FrameReferenceRoutingError as exc:
        raise OpenRouterManagedVideoGatewayError(str(exc)) from exc
    duration = item.get("duration_seconds")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        raise OpenRouterManagedVideoGatewayError("duration_seconds must be numeric")
    duration_int = int(duration)
    if float(duration) != float(duration_int) or duration_int <= 0:
        raise OpenRouterManagedVideoGatewayError(
            "duration_seconds must be a positive whole number"
        )
    if model.supported_durations and duration_int not in model.supported_durations:
        raise OpenRouterManagedVideoGatewayError(
            "requested duration is not supported by live model capability"
        )
    aspect_ratio = item.get("aspect_ratio")
    if not isinstance(aspect_ratio, str) or not aspect_ratio.strip():
        raise OpenRouterManagedVideoGatewayError("aspect_ratio must be non-empty")
    if model.supported_aspect_ratios and aspect_ratio not in model.supported_aspect_ratios:
        raise OpenRouterManagedVideoGatewayError(
            "requested aspect ratio is not supported by live model capability"
        )
    resolution = item.get("resolution", "480p")
    if not isinstance(resolution, str) or not resolution.strip():
        raise OpenRouterManagedVideoGatewayError("resolution must be non-empty")
    if model.supported_resolutions and resolution not in model.supported_resolutions:
        raise OpenRouterManagedVideoGatewayError(
            "requested resolution is not supported by live model capability"
        )
    generate_audio = item.get("generate_audio", False)
    if not isinstance(generate_audio, bool):
        raise OpenRouterManagedVideoGatewayError("generate_audio must be boolean")
    if generate_audio and not model.generate_audio:
        raise OpenRouterManagedVideoGatewayError(
            "requested audio generation is not supported by live model capability"
        )
