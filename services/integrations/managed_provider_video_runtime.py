"""Explicit managed-cost provider composition for the canonical Desktop Video Factory.

This module does not add a second planner, coordinator, renderer, QA authority, or
provider-selection authority. It supplies the existing provider-backed Desktop
runtime with one explicitly selected managed OpenRouter provider session and one
terminal cost-evidence policy. The default Desktop runtime remains verified-free.

Managed execution is fail closed:
- live catalog capability and pricing are required before every provider POST;
- a locked commercial authority and durable managed-credit reservation exist
  before every provider POST;
- the aggregate managed-credit account is the hard external-spend ceiling;
- terminal provider usage is reconciled before the canonical runtime can accept;
- no paid route is selected implicitly by this module.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path

from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.runtime import DurableGrantPolicy
from src.video_automation.commercial_admission import (
    CommercialAdmissionEngine,
    CommercialPricingPolicy,
    LockedVideoQuote,
    PaymentAuthorization,
    ProviderPricingSnapshot,
    TaxProfile,
    VideoCostEnvelope,
)
from src.video_automation.commercial_store import CommercialAuthorityStore
from src.video_automation.generation_execution_tracking import GenerationDispatchExecution
from src.video_automation.generation_job_polling import (
    ProviderJobObservation,
    ProviderJobStatus,
)
from src.video_automation.managed_credit_policy import managed_credit_production_policy
from src.video_automation.managed_credit_store import ManagedCreditLedgerStore
from src.video_automation.managed_credits import (
    ManagedCreditAccount,
    ManagedCreditError,
    ProviderCostQuote,
    usd_to_microusd,
)
from src.video_automation.models import ProviderRequest, ProviderResult
from src.video_automation.openrouter_managed_video_gateway import OpenRouterManagedVideoGateway
from src.video_automation.openrouter_managed_video_provider import (
    OPENROUTER_MANAGED_PROVIDER_NAME,
)
from src.video_automation.openrouter_managed_video_runtime import (
    OpenRouterManagedVideoGenerationJobPoller,
    actual_cost_microusd_from_observation,
)
from src.video_automation.openrouter_video_catalog import OpenRouterVideoCatalogClient
from src.video_automation.openrouter_video_provider import (
    OpenRouterGeneratedAssetRetriever,
    OpenRouterTransport,
    UrllibOpenRouterTransport,
)
from src.video_automation.provider_production_certification import (
    CertificationShape,
    certification_price,
    certification_provider_cost_ceiling,
    select_certification_model,
)
from src.video_automation.providers import ProviderCapabilities

from .provider_video_runtime import (
    ObjectiveResolver,
    ProviderBackedDesktopVideoRuntime,
    ProviderCostEvidence,
    SemanticVideoReviewer,
)
from .video_runtime import VideoRuntimeError

_DEFAULT_MODEL_ID = "bytedance/seedance-2.0-fast"
_DEFAULT_RESOLUTION = "480p"
_DEFAULT_MAX_UNIT_PRICE_USD = Decimal("0.15")
_DEFAULT_MAX_REQUEST_COST_USD = Decimal("0.50")


@dataclass(slots=True)
class _DispatchContext:
    request_id: str
    authorization_id: str
    quote: LockedVideoQuote
    provider_cost_ceiling_microusd: int
    actual_cost_microusd: int | None = None
    actual_margin_bps: int | None = None


class ManagedDesktopVideoSession:
    """One explicit managed provider/cost session shared by provider and poller."""

    def __init__(
        self,
        *,
        root: Path,
        api_key: str,
        model_id: str,
        resolution: str,
        max_total_cost_usd: Decimal,
        max_request_cost_usd: Decimal = _DEFAULT_MAX_REQUEST_COST_USD,
        max_unit_price_usd: Decimal = _DEFAULT_MAX_UNIT_PRICE_USD,
        generate_audio: bool = True,
        transport: OpenRouterTransport | None = None,
    ) -> None:
        if not api_key or api_key != api_key.strip():
            raise VideoRuntimeError("managed Desktop video requires API credentials")
        self.validate_model_id(model_id)
        if not resolution.strip():
            raise VideoRuntimeError("managed Desktop video resolution must not be blank")
        if max_total_cost_usd <= 0:
            raise VideoRuntimeError("managed Desktop total cost ceiling must be positive")
        if max_request_cost_usd <= 0 or max_request_cost_usd > max_total_cost_usd:
            raise VideoRuntimeError(
                "managed Desktop per-request ceiling must be positive and within total cap"
            )
        if max_unit_price_usd <= 0:
            raise VideoRuntimeError("managed Desktop unit-price ceiling must be positive")

        self._root = root
        self._model_id = model_id
        self._resolution = resolution
        self._max_total_cost_usd = max_total_cost_usd
        self._max_total_cost_microusd = usd_to_microusd(max_total_cost_usd)
        self._max_request_cost_usd = max_request_cost_usd
        self._max_unit_price_usd = max_unit_price_usd
        self._generate_audio = generate_audio
        self._transport = transport or UrllibOpenRouterTransport()
        self._catalog = OpenRouterVideoCatalogClient(
            api_key,
            transport=self._transport,
        )
        self._credit_store = ManagedCreditLedgerStore(root / "managed-credit-ledger")
        self._commercial_store = CommercialAuthorityStore(root / "commercial-authority")
        self._commercial_policy = CommercialPricingPolicy()
        self._commercial_engine = CommercialAdmissionEngine(self._commercial_policy)
        self._account = ManagedCreditAccount(
            tenant_id="ilaios-desktop-managed-proof",
            user_id="video-provider-proof",
            available_microusd=self._max_total_cost_microusd,
        )
        self._credit_store.seed_account(self._account)
        self._gateway = OpenRouterManagedVideoGateway(
            api_key=api_key,
            policy=managed_credit_production_policy(
                max_cost_per_video=float(max_request_cost_usd),
                max_daily_cost=float(max_total_cost_usd),
                max_retry_cost=0.0,
            ),
            credit_store=self._credit_store,
            commercial_store=self._commercial_store,
            catalog=self._catalog,
            transport=self._transport,
        )
        self._delegate_poller = OpenRouterManagedVideoGenerationJobPoller(
            api_key,
            provider_id=OPENROUTER_MANAGED_PROVIDER_NAME,
            transport=self._transport,
        )
        self._contexts: dict[str, _DispatchContext] = {}
        self._lock = threading.Lock()
        self._capabilities = ProviderCapabilities(
            provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
            operations=("video.generate",),
            is_paid=True,
            metadata={
                "backend": "openrouter",
                "billing_authority": "managed_credits",
                "commercial_authority": True,
                "aggregate_hard_cap_microusd": self._max_total_cost_microusd,
            },
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    @property
    def provider_id(self) -> str:
        return OPENROUTER_MANAGED_PROVIDER_NAME

    @property
    def transport(self) -> OpenRouterTransport:
        return self._transport

    @property
    def max_total_cost_microusd(self) -> int:
        return self._max_total_cost_microusd

    def validate_model_id(self, model_id: str) -> None:
        if not model_id.strip() or model_id.endswith(":free"):
            raise VideoRuntimeError(
                "managed Desktop Video Factory requires an explicit non-free model id"
            )

    def execute(self, request: ProviderRequest) -> ProviderResult:
        if request.provider_name != OPENROUTER_MANAGED_PROVIDER_NAME:
            return _provider_failure(request, "invalid_request", "managed provider mismatch")
        if request.operation != "video.generate":
            return _provider_failure(request, "invalid_request", "managed operation mismatch")
        try:
            normalized, item = self._normalized_request(request)
            model_id = _request_model_id(normalized)
            if model_id != self._model_id:
                raise VideoRuntimeError("managed Desktop model changed after composition")
            shape = _shape_from_item(
                model_id=model_id,
                item=item,
                resolution=self._resolution,
                generate_audio=self._generate_audio,
                max_unit_price_usd=self._max_unit_price_usd,
                max_total_cost_usd=self._max_request_cost_usd,
            )
            model = select_certification_model(
                self._catalog.paid_eligible_models(),
                shape,
            )
            price = certification_price(model, shape)
            provider_ceiling = certification_provider_cost_ceiling(
                price,
                shape,
                contingency_bps=self._commercial_policy.contingency_bps,
            )
            snapshot = self._catalog.last_good_snapshot
            if snapshot is None:
                raise VideoRuntimeError("managed Desktop catalog evidence is unavailable")
            observed_at = int(snapshot.observed_at_epoch_s)
            pricing = ProviderPricingSnapshot(
                provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
                model_id=model_id,
                pricing_fingerprint=snapshot.catalog_digest,
                observed_at_epoch_s=observed_at,
                expires_at_epoch_s=observed_at + 300,
                estimated_job_cost_microusd=price.estimated_total_microusd,
                max_job_cost_microusd=provider_ceiling,
            )
            provider_quote = ProviderCostQuote(
                provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
                model_id=model_id,
                estimated_cost_microusd=price.estimated_total_microusd,
                max_cost_microusd=provider_ceiling,
            )
            quote = self._commercial_engine.create_locked_quote(
                quote_id=f"desktop-managed-quote-{request.request_id}",
                now_epoch_s=observed_at,
                tax_profile=TaxProfile(
                    "INTERNAL_DESKTOP_PROVIDER_PROOF_NO_SALE",
                    "INTERNAL",
                    0,
                ),
                pricing=pricing,
                costs=VideoCostEnvelope(provider_generation_microusd=provider_ceiling),
                duration_seconds=shape.duration_seconds,
                aggregate_generated_seconds=shape.duration_seconds,
                resolution=shape.resolution,
                shot_count=1,
            )
            payment = PaymentAuthorization(
                payment_authorization_id=f"desktop-managed-budget-{request.request_id}",
                quote_id=quote.quote_id,
                secured_amount_microusd=quote.gross_customer_price_microusd,
                secured_at_epoch_s=observed_at,
            )
            authority = self._commercial_engine.authorize_paid_dispatch(
                now_epoch_s=observed_at,
                quote=quote,
                payment=payment,
                current_pricing=pricing,
                provider_quote=provider_quote,
            )
            self._commercial_store.record_quote(quote)
            self._commercial_store.record_payment(payment)
            self._commercial_store.record_authority(authority)
            routing_decision_id = f"desktop-managed-route-{request.request_id}"
            result = self._gateway.submit(
                account=self._account,
                request=normalized,
                quote=provider_quote,
                routing_decision_id=routing_decision_id,
                commercial_authority=authority,
            )
            if not result.success or result.external_id is None:
                return result
            authorization_id = result.metadata.get("credit_authorization_id")
            if not isinstance(authorization_id, str) or not authorization_id.strip():
                raise VideoRuntimeError(
                    "managed provider result omitted durable credit authorization"
                )
            with self._lock:
                if result.external_id in self._contexts:
                    raise VideoRuntimeError("managed provider job identity collision")
                self._contexts[result.external_id] = _DispatchContext(
                    request_id=normalized.request_id,
                    authorization_id=authorization_id,
                    quote=quote,
                    provider_cost_ceiling_microusd=provider_ceiling,
                )
            return result
        except Exception as exc:  # noqa: BLE001
            return _provider_failure(
                request,
                "managed_admission_failed",
                str(exc).strip() or exc.__class__.__name__,
            )

    def poll(self, provider_job_id: str) -> ProviderJobObservation:
        observation = self._delegate_poller.poll(provider_job_id)
        if observation.status not in {
            ProviderJobStatus.SUCCEEDED,
            ProviderJobStatus.FAILED,
            ProviderJobStatus.CANCELLED,
        }:
            return observation
        with self._lock:
            context = self._contexts.get(provider_job_id)
        if context is None:
            raise VideoRuntimeError("managed terminal job lacks dispatch context")
        if context.actual_cost_microusd is None:
            actual_cost = actual_cost_microusd_from_observation(observation)
            try:
                self._credit_store.settle(
                    authorization_id=context.authorization_id,
                    actual_cost_microusd=actual_cost,
                    provider_job_id=provider_job_id,
                )
            except ManagedCreditError as exc:
                raise VideoRuntimeError("managed provider credit settlement failed") from exc
            reservation_violated = self._commercial_store.settle_request(
                request_id=context.request_id,
                actual_cost_microusd=actual_cost,
            )
            reconciliation = self._commercial_engine.reconcile(
                quote=context.quote,
                actual_provider_cost_microusd=actual_cost,
                actual_other_variable_cost_microusd=0,
            )
            if reservation_violated:
                raise VideoRuntimeError("managed provider commercial reservation was violated")
            if reconciliation.provider_quarantined:
                raise VideoRuntimeError(
                    reconciliation.quarantine_reason
                    or "managed provider commercial reconciliation quarantined provider"
                )
            with self._lock:
                context.actual_cost_microusd = actual_cost
                context.actual_margin_bps = reconciliation.actual_margin_bps
                settled_total = sum(
                    item.actual_cost_microusd or 0 for item in self._contexts.values()
                )
            if settled_total > self._max_total_cost_microusd:
                raise VideoRuntimeError("managed Desktop aggregate cost exceeded hard cap")

        metadata = dict(observation.metadata)
        metadata.update(
            {
                "managed_cost_proven": "true",
                "actual_provider_cost_microusd": str(context.actual_cost_microusd),
                "provider_cost_ceiling_microusd": str(
                    context.provider_cost_ceiling_microusd
                ),
                "actual_margin_bps": str(context.actual_margin_bps),
                "aggregate_hard_cap_microusd": str(self._max_total_cost_microusd),
            }
        )
        return replace(observation, metadata=metadata)

    def verify(
        self, records: Sequence[GenerationDispatchExecution]
    ) -> ProviderCostEvidence:
        if not records:
            raise VideoRuntimeError("managed provider cost evidence is missing")
        actual_total = 0
        ceiling_total = 0
        for record in records:
            metadata: Mapping[str, str] = record.metadata
            if metadata.get("managed_cost_proven") != "true":
                raise VideoRuntimeError("managed provider terminal cost is not proven")
            actual = _nonnegative_int(
                metadata.get("actual_provider_cost_microusd"),
                "actual provider cost",
            )
            ceiling = _nonnegative_int(
                metadata.get("provider_cost_ceiling_microusd"),
                "provider cost ceiling",
            )
            if actual > ceiling:
                raise VideoRuntimeError("managed provider actual cost exceeded dispatch ceiling")
            actual_total += actual
            ceiling_total += ceiling
        if actual_total > self._max_total_cost_microusd:
            raise VideoRuntimeError("managed provider actual total exceeded aggregate hard cap")
        if ceiling_total > self._max_total_cost_microusd:
            raise VideoRuntimeError("managed provider reserved ceilings exceeded aggregate hard cap")
        return ProviderCostEvidence(
            mode="managed-bounded",
            proven=True,
            zero=actual_total == 0,
            actual_microusd=actual_total,
            ceiling_microusd=self._max_total_cost_microusd,
        )

    def _normalized_request(
        self, request: ProviderRequest
    ) -> tuple[ProviderRequest, Mapping[str, object]]:
        raw_items = request.payload.get("items_json")
        if not isinstance(raw_items, str) or not raw_items:
            raise VideoRuntimeError("managed provider request items_json is missing")
        parsed = json.loads(raw_items)
        if not isinstance(parsed, list) or len(parsed) != 1 or not isinstance(parsed[0], dict):
            raise VideoRuntimeError("managed provider request requires exactly one item")
        item: dict[str, object] = dict(parsed[0])
        item["resolution"] = self._resolution
        item["generate_audio"] = self._generate_audio
        payload = dict(request.payload)
        payload["items_json"] = json.dumps(
            [item], sort_keys=True, separators=(",", ":")
        )
        return (
            ProviderRequest(
                request_id=request.request_id,
                job_id=request.job_id,
                provider_name=request.provider_name,
                operation=request.operation,
                payload=payload,
            ),
            item,
        )


class ManagedProviderBackedDesktopVideoRuntime(ProviderBackedDesktopVideoRuntime):
    """Canonical Desktop Video runtime with an explicitly bounded managed provider."""

    PROVIDER_ID = OPENROUTER_MANAGED_PROVIDER_NAME

    def __init__(
        self,
        root: Path,
        grants: DurableGrantPolicy,
        governance: GovernedRuntimeGateway,
        evidence: EvidenceStore,
        *,
        objective_resolver: ObjectiveResolver,
        api_key: str,
        max_total_cost_usd: Decimal,
        model_id: str = _DEFAULT_MODEL_ID,
        qa_model_id: str = "openrouter/free",
        resolution: str = _DEFAULT_RESOLUTION,
        poll_interval_seconds: float = 5.0,
        max_poll_rounds: int = 144,
        reviewer: SemanticVideoReviewer | None = None,
        transport: OpenRouterTransport | None = None,
    ) -> None:
        session = ManagedDesktopVideoSession(
            root=root / "managed-provider",
            api_key=api_key,
            model_id=model_id,
            resolution=resolution,
            max_total_cost_usd=max_total_cost_usd,
            transport=transport,
        )
        super().__init__(
            root,
            grants,
            governance,
            evidence,
            objective_resolver=objective_resolver,
            api_key=api_key,
            model_id=model_id,
            qa_model_id=qa_model_id,
            resolution=resolution,
            poll_interval_seconds=poll_interval_seconds,
            max_poll_rounds=max_poll_rounds,
            provider=session,
            poller=session,
            retriever=OpenRouterGeneratedAssetRetriever(
                api_key,
                provider_id=self.PROVIDER_ID,
                transport=session.transport,
            ),
            reviewer=reviewer,
            cost_policy=session,
        )
        self._managed_provider_session = session


def _request_model_id(request: ProviderRequest) -> str:
    model_id = request.payload.get("model_id")
    if not isinstance(model_id, str) or not model_id.strip():
        raise VideoRuntimeError("managed provider request model_id is missing")
    return model_id


def _shape_from_item(
    *,
    model_id: str,
    item: Mapping[str, object],
    resolution: str,
    generate_audio: bool,
    max_unit_price_usd: Decimal,
    max_total_cost_usd: Decimal,
) -> CertificationShape:
    duration = item.get("duration_seconds")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        raise VideoRuntimeError("managed provider duration must be numeric")
    normalized_duration = int(duration)
    if float(duration) != float(normalized_duration) or normalized_duration <= 0:
        raise VideoRuntimeError("managed provider duration must be a positive whole number")
    aspect_ratio = item.get("aspect_ratio")
    if not isinstance(aspect_ratio, str) or not aspect_ratio.strip():
        raise VideoRuntimeError("managed provider aspect ratio is missing")
    return CertificationShape(
        model_id=model_id,
        duration_seconds=normalized_duration,
        resolution=resolution,
        aspect_ratio=aspect_ratio,
        generate_audio=generate_audio,
        max_unit_price_usd=max_unit_price_usd,
        max_total_cost_usd=max_total_cost_usd,
    )


def _nonnegative_int(value: str | None, name: str) -> int:
    if value is None:
        raise VideoRuntimeError(f"{name} evidence is missing")
    try:
        normalized = int(value)
    except ValueError as exc:
        raise VideoRuntimeError(f"{name} evidence is invalid") from exc
    if normalized < 0:
        raise VideoRuntimeError(f"{name} evidence must not be negative")
    return normalized


def _provider_failure(
    request: ProviderRequest,
    code: str,
    message: str,
) -> ProviderResult:
    return ProviderResult(
        request_id=request.request_id,
        provider_name=request.provider_name,
        success=False,
        error_code=code,
        error_message=message,
        metadata={
            "backend": "openrouter",
            "cost_mode": "managed-bounded",
        },
    )
