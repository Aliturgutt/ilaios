"""Catalog-bound managed OpenRouter dispatch without a second routing authority."""

from __future__ import annotations

import json
from collections.abc import Mapping
from decimal import Decimal, ROUND_CEILING
from typing import cast

from .commercial_pricing import (
    CommercialPricingError,
    CommercialPricingGuard,
    CommercialPricingPolicy,
)
from .configuration import VideoAutomationPolicy
from .managed_credit_store import ManagedCreditLedgerStore, ProviderSideEffectLedger
from .managed_credits import (
    ManagedCreditAccount,
    ManagedCreditError,
    ProviderCostQuote,
)
from .managed_provider_execution import ManagedPaidVideoExecutionCoordinator
from .models import ProviderRequest, ProviderResult
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

_MICRO_USD_PER_USD = Decimal("1000000")


class OpenRouterManagedVideoGatewayError(ValueError):
    """Raised before dispatch when capability or financial evidence is insufficient."""


class OpenRouterManagedVideoGateway:
    """Bind live catalog facts to the existing managed-credit dispatch boundary.

    The gateway never chooses a provider/model. It validates an already governed
    request and canonical routing-decision binding before creating a provider.
    Every paid submit additionally proves authoritative provider cost and a
    configured non-loss-making customer net price before any external POST.
    """

    def __init__(
        self,
        *,
        api_key: str,
        policy: VideoAutomationPolicy,
        credit_store: ManagedCreditLedgerStore,
        catalog: OpenRouterVideoCatalogClient,
        commercial_pricing_policy: CommercialPricingPolicy,
        transport: OpenRouterTransport | None = None,
        webhook_store: OpenRouterVideoWebhookStore | None = None,
        callback_url: str | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise OpenRouterManagedVideoGatewayError("api_key must not be blank")
        self._api_key = api_key
        self._policy = policy
        self._credit_store = credit_store
        self._catalog = catalog
        self._commercial_pricing_policy = commercial_pricing_policy
        self._transport = transport
        self._webhook_store = webhook_store
        self._callback_url = callback_url

    def submit(
        self,
        *,
        account: ManagedCreditAccount,
        request: ProviderRequest,
        quote: ProviderCostQuote,
        routing_decision_id: str,
        customer_net_price_usd: Decimal,
    ) -> ProviderResult:
        """Validate catalog, cost floor, margin floor, then perform one governed POST."""

        if request.provider_name != OPENROUTER_MANAGED_PROVIDER_NAME:
            raise OpenRouterManagedVideoGatewayError(
                "request is not bound to the managed OpenRouter provider"
            )

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
        model_id = _request_model_id(request)
        model = model_by_id.get(model_id)
        if model is None:
            raise OpenRouterManagedVideoGatewayError(
                "requested model is not currently paid-eligible"
            )
        item = _validate_capabilities(request, model)
        duration_seconds = _item_duration(item)
        resolution = _item_resolution(item)

        try:
            catalog_provider_cost_usd = model.quote_provider_cost_usd(
                duration_seconds=duration_seconds,
                resolution=resolution,
            )
        except OpenRouterCatalogError as exc:
            raise OpenRouterManagedVideoGatewayError(str(exc)) from exc

        _validate_provider_quote(
            quote,
            model_id=model_id,
            catalog_provider_cost_usd=catalog_provider_cost_usd,
        )
        try:
            commercial_quote = CommercialPricingGuard().quote_for_provider_cost(
                provider_cost_usd=catalog_provider_cost_usd,
                generated_seconds=duration_seconds,
                policy=self._commercial_pricing_policy,
            )
            CommercialPricingGuard().assert_charge_is_safe(
                commercial_quote,
                customer_net_price_usd=customer_net_price_usd,
            )
        except CommercialPricingError as exc:
            raise OpenRouterManagedVideoGatewayError(
                f"paid dispatch blocked by commercial pricing guard: {exc}"
            ) from exc

        snapshot = self._catalog.last_good_snapshot
        if snapshot is None:
            raise OpenRouterManagedVideoGatewayError(
                "catalog lost last-known-good snapshot before dispatch"
            )
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
        plan = coordinator.authorize(
            account=account,
            request=request,
            quote=quote,
            routing_decision_id=routing_decision_id,
        )
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


def _request_model_id(request: ProviderRequest) -> str:
    value = request.payload.get("model_id")
    if not isinstance(value, str) or not value.strip():
        raise OpenRouterManagedVideoGatewayError("request model_id must be non-empty")
    return value


def _validate_provider_quote(
    quote: ProviderCostQuote,
    *,
    model_id: str,
    catalog_provider_cost_usd: Decimal,
) -> None:
    if quote.provider_name != OPENROUTER_MANAGED_PROVIDER_NAME:
        raise OpenRouterManagedVideoGatewayError(
            "provider cost quote is bound to the wrong provider"
        )
    if quote.model_id != model_id:
        raise OpenRouterManagedVideoGatewayError(
            "provider cost quote is bound to the wrong model"
        )
    required_microusd = int(
        (catalog_provider_cost_usd * _MICRO_USD_PER_USD).to_integral_value(
            rounding=ROUND_CEILING
        )
    )
    if required_microusd <= 0:
        raise OpenRouterManagedVideoGatewayError(
            "paid dispatch requires a positive authoritative provider cost"
        )
    if quote.estimated_cost_microusd < required_microusd:
        raise OpenRouterManagedVideoGatewayError(
            "provider cost quote underestimates authoritative catalog price"
        )
    if quote.max_cost_microusd < required_microusd:
        raise OpenRouterManagedVideoGatewayError(
            "provider maximum cost does not cover authoritative catalog price"
        )


def _validate_capabilities(
    request: ProviderRequest,
    model: OpenRouterVideoModel,
) -> Mapping[str, object]:
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
    if (
        not isinstance(parsed, list)
        or len(parsed) != 1
        or not isinstance(parsed[0], dict)
    ):
        raise OpenRouterManagedVideoGatewayError(
            "items_json must contain exactly one object"
        )
    item = cast(Mapping[str, object], parsed[0])
    duration_int = _item_duration(item)
    if model.supported_durations and duration_int not in model.supported_durations:
        raise OpenRouterManagedVideoGatewayError(
            "requested duration is not supported by live model capability"
        )
    aspect_ratio = item.get("aspect_ratio")
    if not isinstance(aspect_ratio, str) or not aspect_ratio.strip():
        raise OpenRouterManagedVideoGatewayError("aspect_ratio must be non-empty")
    if (
        model.supported_aspect_ratios
        and aspect_ratio not in model.supported_aspect_ratios
    ):
        raise OpenRouterManagedVideoGatewayError(
            "requested aspect ratio is not supported by live model capability"
        )
    resolution = _item_resolution(item)
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
    return item


def _item_duration(item: Mapping[str, object]) -> int:
    duration = item.get("duration_seconds")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        raise OpenRouterManagedVideoGatewayError("duration_seconds must be numeric")
    duration_int = int(duration)
    if float(duration) != float(duration_int) or duration_int <= 0:
        raise OpenRouterManagedVideoGatewayError(
            "duration_seconds must be a positive whole number"
        )
    return duration_int


def _item_resolution(item: Mapping[str, object]) -> str:
    resolution = item.get("resolution", "480p")
    if not isinstance(resolution, str) or not resolution.strip():
        raise OpenRouterManagedVideoGatewayError("resolution must be non-empty")
    return resolution
