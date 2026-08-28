"""Manual real-provider certification through canonical Video provider boundaries.

This operational proof validates a paid provider route end to end. A locked
customer quote is created and persisted before the provider POST. Terminal
provider cost may be positive; acceptance is based on the locked provider
ceiling and hard minimum margin. Exact-zero cost remains a property of the
separate free-provider certification only.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from pathlib import Path
from typing import NoReturn

from .commercial_admission import (
    CommercialAdmissionEngine,
    CommercialPricingPolicy,
    PaymentAuthorization,
    ProviderPricingSnapshot,
    TaxProfile,
    VideoCostEnvelope,
)
from .commercial_store import CommercialAuthorityStore
from .generation_job_polling import ProviderJobStatus
from .managed_credit_policy import managed_credit_production_policy
from .managed_credit_store import ManagedCreditLedgerStore
from .managed_credits import ManagedCreditAccount, ProviderCostQuote, usd_to_microusd
from .models import ProviderRequest
from .openrouter_managed_video_gateway import OpenRouterManagedVideoGateway
from .openrouter_managed_video_provider import OPENROUTER_MANAGED_PROVIDER_NAME
from .openrouter_managed_video_runtime import (
    OpenRouterManagedVideoGenerationJobPoller,
    actual_cost_microusd_from_observation,
)
from .openrouter_video_catalog import OpenRouterVideoCatalogClient, OpenRouterVideoModel
from .openrouter_video_provider import (
    OpenRouterGeneratedAssetRetriever,
    UrllibOpenRouterTransport,
)

DEFAULT_MODEL_ID = "bytedance/seedance-2.0-fast"
DEFAULT_DURATION_SECONDS = 4
DEFAULT_RESOLUTION = "480p"
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_MAX_UNIT_PRICE_USD = Decimal("0.15")
DEFAULT_MAX_TOTAL_COST_USD = Decimal("0.60")
DEFAULT_POLL_TIMEOUT_SECONDS = 12 * 60
DEFAULT_POLL_INTERVAL_SECONDS = 5


class ProviderProductionCertificationError(ValueError):
    """Raised when real-provider production proof cannot be completed safely."""


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise ProviderProductionCertificationError(
            f"{name} must be normalized non-blank text"
        )


@dataclass(frozen=True, slots=True)
class CertificationShape:
    model_id: str = DEFAULT_MODEL_ID
    duration_seconds: int = DEFAULT_DURATION_SECONDS
    resolution: str = DEFAULT_RESOLUTION
    aspect_ratio: str = DEFAULT_ASPECT_RATIO
    generate_audio: bool = False
    max_unit_price_usd: Decimal = DEFAULT_MAX_UNIT_PRICE_USD
    max_total_cost_usd: Decimal = DEFAULT_MAX_TOTAL_COST_USD

    def __post_init__(self) -> None:
        _text("model_id", self.model_id)
        _text("resolution", self.resolution)
        _text("aspect_ratio", self.aspect_ratio)
        if self.duration_seconds <= 0:
            raise ProviderProductionCertificationError(
                "duration_seconds must be positive"
            )
        if self.max_unit_price_usd <= 0 or self.max_total_cost_usd <= 0:
            raise ProviderProductionCertificationError(
                "certification cost ceilings must be positive"
            )


@dataclass(frozen=True, slots=True)
class CertificationPrice:
    sku: str
    unit_price_usd: Decimal
    estimated_units: Decimal
    estimated_total_usd: Decimal
    estimated_total_microusd: int


def select_certification_model(
    models: tuple[OpenRouterVideoModel, ...],
    shape: CertificationShape,
) -> OpenRouterVideoModel:
    """Require the configured model and exact proof capability."""

    selected = next((model for model in models if model.model_id == shape.model_id), None)
    if selected is None:
        raise ProviderProductionCertificationError(
            "configured certification model is not currently paid-eligible"
        )
    if (
        selected.supported_durations
        and shape.duration_seconds not in selected.supported_durations
    ):
        raise ProviderProductionCertificationError(
            "configured certification duration is not currently supported"
        )
    if (
        selected.supported_resolutions
        and shape.resolution not in selected.supported_resolutions
    ):
        raise ProviderProductionCertificationError(
            "configured certification resolution is not currently supported"
        )
    if (
        selected.supported_aspect_ratios
        and shape.aspect_ratio not in selected.supported_aspect_ratios
    ):
        raise ProviderProductionCertificationError(
            "configured certification aspect ratio is not currently supported"
        )
    if shape.generate_audio and not selected.generate_audio:
        raise ProviderProductionCertificationError(
            "configured certification audio generation is not supported"
        )
    return selected


def _catalog_decimal_price(raw_price: str) -> Decimal:
    try:
        unit_price = Decimal(raw_price)
    except InvalidOperation as exc:
        raise ProviderProductionCertificationError(
            "live catalog video price is not a decimal"
        ) from exc
    if not unit_price.is_finite() or unit_price < 0:
        raise ProviderProductionCertificationError(
            "live catalog video price must be finite and non-negative"
        )
    return unit_price


def _certification_video_token_units(shape: CertificationShape) -> Decimal:
    """Return conservative whole-token units for the explicitly proven shape.

    OpenRouter documents ByteDance video-token quantity as
    ``height * width * duration * 24 / 1024``. Production certification keeps
    the pixel mapping deliberately narrow: only the exact 480p/16:9 proof shape
    is admitted until another shape is independently evidenced.
    """

    dimensions = {
        ("480p", "16:9"): (854, 480),
    }.get((shape.resolution, shape.aspect_ratio))
    if dimensions is None:
        raise ProviderProductionCertificationError(
            "token-priced certification lacks an approved pixel mapping"
        )
    width, height = dimensions
    numerator = Decimal(width * height * shape.duration_seconds * 24)
    units = (numerator / Decimal(1024)).to_integral_value(rounding=ROUND_CEILING)
    if units <= 0:
        raise ProviderProductionCertificationError(
            "token-priced certification produced invalid video-token quantity"
        )
    return units


def certification_price(
    model: OpenRouterVideoModel,
    shape: CertificationShape,
) -> CertificationPrice:
    """Derive a conservative bounded quote from recognized live video-price SKUs."""

    per_second_skus = (
        f"per-video-second-{shape.resolution}",
        "per-video-second",
        "generate",
    )
    for sku in per_second_skus:
        raw_price = model.pricing_skus.get(sku)
        if raw_price is None:
            continue
        unit_price = _catalog_decimal_price(raw_price)
        estimated_units = Decimal(shape.duration_seconds)
        total = unit_price * estimated_units
        if unit_price > shape.max_unit_price_usd:
            raise ProviderProductionCertificationError(
                "live unit price exceeds certification cost ceiling"
            )
        if total > shape.max_total_cost_usd:
            raise ProviderProductionCertificationError(
                "live total price exceeds certification cost ceiling"
            )
        return CertificationPrice(
            sku=sku,
            unit_price_usd=unit_price,
            estimated_units=estimated_units,
            estimated_total_usd=total,
            estimated_total_microusd=usd_to_microusd(total),
        )

    token_skus = (
        ("video_tokens",)
        if shape.generate_audio
        else ("video_tokens_without_audio", "video_tokens")
    )
    for sku in token_skus:
        raw_price = model.pricing_skus.get(sku)
        if raw_price is None:
            continue
        unit_price = _catalog_decimal_price(raw_price)
        estimated_units = _certification_video_token_units(shape)
        total = unit_price * estimated_units
        effective_per_second = total / Decimal(shape.duration_seconds)
        if effective_per_second > shape.max_unit_price_usd:
            raise ProviderProductionCertificationError(
                "live effective per-second price exceeds certification cost ceiling"
            )
        if total > shape.max_total_cost_usd:
            raise ProviderProductionCertificationError(
                "live total price exceeds certification cost ceiling"
            )
        return CertificationPrice(
            sku=sku,
            unit_price_usd=unit_price,
            estimated_units=estimated_units,
            estimated_total_usd=total,
            estimated_total_microusd=usd_to_microusd(total),
        )

    raise ProviderProductionCertificationError(
        "live catalog lacks a recognized bounded video price SKU"
    )


def certification_provider_cost_ceiling(
    price: CertificationPrice,
    shape: CertificationShape,
    *,
    contingency_bps: int,
) -> int:
    """Reserve bounded provider variance before dispatch without widening the hard cap."""

    if contingency_bps < 0 or contingency_bps >= 10_000:
        raise ProviderProductionCertificationError(
            "provider reservation contingency must be between 0 and 9999 bps"
        )
    hard_cap_microusd = usd_to_microusd(shape.max_total_cost_usd)
    estimated_microusd = price.estimated_total_microusd
    buffered_microusd = (
        estimated_microusd * (10_000 + contingency_bps) + 9_999
    ) // 10_000
    ceiling_microusd = min(buffered_microusd, hard_cap_microusd)
    if ceiling_microusd < estimated_microusd:
        raise ProviderProductionCertificationError(
            "provider reservation hard cap is below the live estimated cost"
        )
    return ceiling_microusd


def build_certification_request(
    *,
    shape: CertificationShape,
    run_id: str,
    run_attempt: str,
) -> ProviderRequest:
    """Build one unique managed-provider request for a manual certification run."""

    _text("run_id", run_id)
    _text("run_attempt", run_attempt)
    request_id = f"video-provider-cert-{run_id}-{run_attempt}"
    item = {
        "request_id": request_id,
        "shot_id": "provider-production-proof-shot-001",
        "prompt_text": (
            "A four-second cinematic abstract technology shot for infrastructure "
            "validation: soft cyan light travels across a dark graphite geometric "
            "surface, subtle depth, slow controlled dolly motion, clean background, "
            "no people, no text, no logos."
        ),
        "duration_seconds": shape.duration_seconds,
        "aspect_ratio": shape.aspect_ratio,
        "output_count": 1,
        "resolution": shape.resolution,
        "generate_audio": shape.generate_audio,
    }
    return ProviderRequest(
        request_id=request_id,
        job_id=f"video-provider-cert-job-{run_id}-{run_attempt}",
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        operation="video.generate",
        payload={
            "model_id": shape.model_id,
            "request_count": 1,
            "items_json": json.dumps([item], sort_keys=True, separators=(",", ":")),
        },
    )


def run_certification(
    *,
    api_key: str,
    proof_dir: Path,
    revision_sha: str,
    run_id: str,
    run_attempt: str,
    shape: CertificationShape | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    poll_timeout_seconds: int = DEFAULT_POLL_TIMEOUT_SECONDS,
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
) -> dict[str, object]:
    """Execute one paid proof with quote-before-generation and reconciliation."""

    proof_shape = shape if shape is not None else CertificationShape()
    proof_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = proof_dir / "provider-receipt.json"
    video_path = proof_dir / "provider-proof.mp4"
    receipt: dict[str, object] = {
        "schema": "ilaios.video.real-provider-proof.v3",
        "status": "STARTED",
        "revision_sha": revision_sha,
        "workflow_run_id": run_id,
        "workflow_run_attempt": run_attempt,
        "provider": OPENROUTER_MANAGED_PROVIDER_NAME,
        "model": proof_shape.model_id,
        "cost_mode": "COMMERCIAL_BOUNDED",
        "credential_reference": (
            "github-environment-secret://Production/OPENROUTER_API_KEY"
        ),
        "request_shape": {
            "duration_seconds": proof_shape.duration_seconds,
            "resolution": proof_shape.resolution,
            "aspect_ratio": proof_shape.aspect_ratio,
            "generate_audio": proof_shape.generate_audio,
        },
        "budget_guard": {
            "max_unit_price_usd": str(proof_shape.max_unit_price_usd),
            "max_total_cost_usd": str(proof_shape.max_total_cost_usd),
        },
        "started_at": _utc_now(),
    }
    _persist(receipt_path, receipt)
    if run_attempt != "1":
        _fail(
            receipt_path,
            receipt,
            "BLOCKED_REPEAT_PAID_ATTEMPT",
            "paid Video certification re-runs are forbidden; use a new exact revision after review.",
        )
    if not api_key or not api_key.strip():
        _fail(
            receipt_path,
            receipt,
            "BLOCKED_MISSING_SECRET",
            "OPENROUTER_API_KEY is unavailable; no provider request was submitted.",
        )

    transport = UrllibOpenRouterTransport()
    catalog = OpenRouterVideoCatalogClient(api_key, transport=transport)
    try:
        model = select_certification_model(catalog.paid_eligible_models(), proof_shape)
        price = certification_price(model, proof_shape)
    except Exception as exc:
        _fail(
            receipt_path,
            receipt,
            "BLOCKED_CATALOG_CAPABILITY_OR_PRICE",
            str(exc),
        )

    commercial_policy = CommercialPricingPolicy()
    provider_cost_ceiling_microusd = certification_provider_cost_ceiling(
        price,
        proof_shape,
        contingency_bps=commercial_policy.contingency_bps,
    )

    snapshot = catalog.last_good_snapshot
    if snapshot is None:
        _fail(
            receipt_path,
            receipt,
            "BLOCKED_CATALOG_EVIDENCE",
            "canonical catalog did not retain a live evidence snapshot",
        )
    receipt["catalog"] = {
        "catalog_digest": snapshot.catalog_digest,
        "observed_at_epoch_s": snapshot.observed_at_epoch_s,
        "pricing_sku": price.sku,
        "unit_price_usd": str(price.unit_price_usd),
        "estimated_units": str(price.estimated_units),
        "estimated_total_usd": str(price.estimated_total_usd),
        "reserved_provider_ceiling_microusd": provider_cost_ceiling_microusd,
    }
    receipt["provider_reservation_contingency_bps"] = commercial_policy.contingency_bps

    request = build_certification_request(
        shape=proof_shape,
        run_id=run_id,
        run_attempt=run_attempt,
    )
    routing_decision_id = f"video-provider-cert-route-{run_id}-{run_attempt}"
    provider_quote = ProviderCostQuote(
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        model_id=proof_shape.model_id,
        estimated_cost_microusd=price.estimated_total_microusd,
        max_cost_microusd=provider_cost_ceiling_microusd,
    )
    credit_store = ManagedCreditLedgerStore(proof_dir / "managed-credit-ledger")
    account = ManagedCreditAccount(
        tenant_id="ilaios-production-certification",
        user_id="video-provider-proof",
        available_microusd=usd_to_microusd(proof_shape.max_total_cost_usd),
    )
    policy = managed_credit_production_policy(
        max_cost_per_video=float(proof_shape.max_total_cost_usd),
        max_daily_cost=float(proof_shape.max_total_cost_usd),
        max_retry_cost=0.0,
    )

    commercial_now = int(snapshot.observed_at_epoch_s)
    commercial_pricing = ProviderPricingSnapshot(
        provider_name=OPENROUTER_MANAGED_PROVIDER_NAME,
        model_id=proof_shape.model_id,
        pricing_fingerprint=snapshot.catalog_digest,
        observed_at_epoch_s=commercial_now,
        expires_at_epoch_s=commercial_now + 300,
        estimated_job_cost_microusd=price.estimated_total_microusd,
        max_job_cost_microusd=provider_cost_ceiling_microusd,
    )
    commercial_engine = CommercialAdmissionEngine(commercial_policy)
    locked_quote = commercial_engine.create_locked_quote(
        quote_id=f"video-provider-cert-quote-{run_id}-{run_attempt}",
        now_epoch_s=commercial_now,
        tax_profile=TaxProfile(
            "INTERNAL_CERTIFICATION_NO_SALE",
            "INTERNAL",
            0,
        ),
        pricing=commercial_pricing,
        costs=VideoCostEnvelope(
            provider_generation_microusd=provider_cost_ceiling_microusd,
        ),
        duration_seconds=proof_shape.duration_seconds,
        aggregate_generated_seconds=proof_shape.duration_seconds,
        resolution=proof_shape.resolution,
        shot_count=1,
    )
    payment = PaymentAuthorization(
        payment_authorization_id=(
            f"internal-certification-budget-{run_id}-{run_attempt}"
        ),
        quote_id=locked_quote.quote_id,
        secured_amount_microusd=locked_quote.gross_customer_price_microusd,
        secured_at_epoch_s=commercial_now,
    )
    commercial_authority = commercial_engine.authorize_paid_dispatch(
        now_epoch_s=commercial_now,
        quote=locked_quote,
        payment=payment,
        current_pricing=commercial_pricing,
        provider_quote=provider_quote,
    )
    commercial_store = CommercialAuthorityStore(proof_dir / "commercial-authority")
    commercial_store.record_quote(locked_quote)
    commercial_store.record_payment(payment)
    commercial_store.record_authority(commercial_authority)

    receipt["request_id"] = request.request_id
    receipt["routing_decision_id"] = routing_decision_id
    receipt["quoted_provider_cost_microusd"] = price.estimated_total_microusd
    receipt["reserved_provider_cost_ceiling_microusd"] = (
        provider_cost_ceiling_microusd
    )
    receipt["customer_quote"] = {
        "quote_id": locked_quote.quote_id,
        "quote_sha256": locked_quote.quote_sha256,
        "net_price_ex_tax_microusd": locked_quote.net_price_ex_tax_microusd,
        "tax_microusd": locked_quote.tax_microusd,
        "gross_customer_price_microusd": locked_quote.gross_customer_price_microusd,
        "provider_cost_ceiling_microusd": locked_quote.provider_cost_ceiling_microusd,
        "target_margin_bps": locked_quote.target_margin_bps,
        "hard_min_margin_bps": locked_quote.hard_min_margin_bps,
        "expires_at_epoch_s": locked_quote.expires_at_epoch_s,
    }
    receipt["commercial_admission"] = {
        "funding_mode": "INTERNAL_CERTIFICATION_BUDGET",
        "quote_id": locked_quote.quote_id,
        "quote_sha256": locked_quote.quote_sha256,
        "authority_sha256": commercial_authority.authority_sha256,
        "tax_profile_id": locked_quote.tax_profile_id,
        "provider_cost_ceiling_microusd": (
            commercial_authority.provider_cost_ceiling_microusd
        ),
        "payment_secured_before_dispatch": True,
        "quote_persisted_before_dispatch": True,
    }
    receipt["quote_ready_at"] = _utc_now()
    _persist(receipt_path, receipt)

    gateway = OpenRouterManagedVideoGateway(
        api_key=api_key,
        policy=policy,
        credit_store=credit_store,
        commercial_store=commercial_store,
        catalog=catalog,
        transport=transport,
    )
    receipt["submitted_at"] = _utc_now()
    _persist(receipt_path, receipt)
    result = gateway.submit(
        account=account,
        request=request,
        quote=provider_quote,
        routing_decision_id=routing_decision_id,
        commercial_authority=commercial_authority,
    )
    receipt["provider_result"] = {
        "success": result.success,
        "external_id": result.external_id,
        "error_code": result.error_code,
        "error_message": result.error_message,
        "metadata": dict(result.metadata),
    }
    _persist(receipt_path, receipt)
    if not result.success or result.external_id is None:
        _fail(
            receipt_path,
            receipt,
            "FAILED_PROVIDER_SUBMIT",
            result.error_message or "canonical provider submission failed",
        )

    provider_job_id = result.external_id
    poller = OpenRouterManagedVideoGenerationJobPoller(
        api_key,
        provider_id=OPENROUTER_MANAGED_PROVIDER_NAME,
        transport=transport,
    )
    deadline = monotonic() + poll_timeout_seconds
    poll_observations: list[dict[str, object]] = []
    final_asset_id: str | None = None
    terminal_observation = None
    while monotonic() < deadline:
        observation = poller.poll(provider_job_id)
        poll_observations.append(
            {
                "status": observation.status.value,
                "output_asset_ids": list(observation.output_asset_ids),
                "error_code": observation.error_code,
                "error_message": observation.error_message,
                "metadata": dict(observation.metadata),
            }
        )
        receipt["poll_observations"] = poll_observations
        _persist(receipt_path, receipt)
        if observation.status is ProviderJobStatus.SUCCEEDED:
            if not observation.output_asset_ids:
                _fail(
                    receipt_path,
                    receipt,
                    "FAILED_PROVIDER_RECEIPT",
                    "successful provider observation omitted output asset evidence",
                )
            final_asset_id = observation.output_asset_ids[0]
            terminal_observation = observation
            break
        if observation.status in {
            ProviderJobStatus.FAILED,
            ProviderJobStatus.CANCELLED,
        }:
            terminal_observation = observation
            break
        sleep(float(poll_interval_seconds))
    else:
        _fail(
            receipt_path,
            receipt,
            "FAILED_PROVIDER_TIMEOUT",
            "provider job did not become terminal within the bounded polling window",
        )

    if terminal_observation is None:
        _fail(
            receipt_path,
            receipt,
            "FAILED_PROVIDER_RECEIPT",
            "provider completed without terminal accounting evidence",
        )
    try:
        actual_provider_cost_microusd = actual_cost_microusd_from_observation(
            terminal_observation
        )
    except Exception as exc:
        _fail(
            receipt_path,
            receipt,
            "FAILED_PROVIDER_COST_EVIDENCE",
            str(exc),
        )

    reservation_violated = commercial_store.settle_request(
        request_id=request.request_id,
        actual_cost_microusd=actual_provider_cost_microusd,
    )
    reconciliation = commercial_engine.reconcile(
        quote=locked_quote,
        actual_provider_cost_microusd=actual_provider_cost_microusd,
        actual_other_variable_cost_microusd=0,
    )
    receipt["commercial_reconciliation"] = {
        "actual_provider_cost_microusd": actual_provider_cost_microusd,
        "actual_total_cost_microusd": reconciliation.actual_total_cost_microusd,
        "gross_profit_microusd": reconciliation.gross_profit_microusd,
        "actual_margin_bps": reconciliation.actual_margin_bps,
        "hard_min_margin_bps": locked_quote.hard_min_margin_bps,
        "provider_cost_ceiling_microusd": locked_quote.provider_cost_ceiling_microusd,
        "reservation_violated": reservation_violated,
        "provider_quarantined": reconciliation.provider_quarantined,
        "quarantine_reason": reconciliation.quarantine_reason,
    }
    _persist(receipt_path, receipt)
    if reservation_violated or reconciliation.provider_quarantined:
        _fail(
            receipt_path,
            receipt,
            "FAILED_COMMERCIAL_RECONCILIATION",
            reconciliation.quarantine_reason
            or "actual provider cost exceeded locked commercial authority",
        )

    if terminal_observation.status is not ProviderJobStatus.SUCCEEDED:
        _fail(
            receipt_path,
            receipt,
            "FAILED_PROVIDER_GENERATION",
            terminal_observation.error_message or terminal_observation.status.value,
        )
    if final_asset_id is None:
        _fail(
            receipt_path,
            receipt,
            "FAILED_PROVIDER_RECEIPT",
            "provider completed without an exact output asset reference",
        )

    retriever = OpenRouterGeneratedAssetRetriever(
        api_key,
        provider_id=OPENROUTER_MANAGED_PROVIDER_NAME,
        transport=transport,
    )
    asset = retriever.retrieve(final_asset_id)
    artifact_sha256 = hashlib.sha256(asset.body).hexdigest()
    video_path.write_bytes(asset.body)

    receipt["status"] = "PASS"
    receipt["external_job_id"] = provider_job_id
    receipt["generation_receipt_ref"] = f"openrouter://videos/{provider_job_id}"
    receipt["provider_terminal_metadata"] = dict(terminal_observation.metadata)
    receipt["provider_cost_zero"] = actual_provider_cost_microusd == 0
    receipt["commercial_cost_proven"] = True
    receipt["artifact"] = {
        "path": video_path.name,
        "source_asset_id": asset.source_asset_id,
        "sha256": artifact_sha256,
        "bytes": len(asset.body),
        "content_type": asset.content_type,
        "metadata": dict(asset.metadata),
    }
    receipt["artifact_receipt_ref"] = f"sha256:{artifact_sha256}"
    receipt["finished_at"] = _utc_now()
    _persist(receipt_path, receipt)
    return receipt


def certification_from_environment() -> dict[str, object]:
    """Run the manual GitHub Production-environment certification."""

    proof_dir = Path(
        os.environ.get(
            "VIDEO_PROVIDER_PROOF_DIR",
            "artifacts/video-provider-production-certification",
        )
    )
    shape = CertificationShape(
        model_id=os.environ.get("VIDEO_PROVIDER_MODEL", DEFAULT_MODEL_ID),
        duration_seconds=int(
            os.environ.get(
                "VIDEO_PROVIDER_DURATION_SECONDS",
                str(DEFAULT_DURATION_SECONDS),
            )
        ),
        resolution=os.environ.get("VIDEO_PROVIDER_RESOLUTION", DEFAULT_RESOLUTION),
        aspect_ratio=os.environ.get(
            "VIDEO_PROVIDER_ASPECT_RATIO", DEFAULT_ASPECT_RATIO
        ),
        generate_audio=False,
        max_unit_price_usd=Decimal(
            os.environ.get(
                "VIDEO_PROVIDER_MAX_UNIT_PRICE_USD",
                str(DEFAULT_MAX_UNIT_PRICE_USD),
            )
        ),
        max_total_cost_usd=Decimal(
            os.environ.get(
                "VIDEO_PROVIDER_MAX_TOTAL_COST_USD",
                str(DEFAULT_MAX_TOTAL_COST_USD),
            )
        ),
    )
    return run_certification(
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        proof_dir=proof_dir,
        revision_sha=os.environ.get("GITHUB_SHA", "unknown"),
        run_id=os.environ.get("GITHUB_RUN_ID", "local"),
        run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        shape=shape,
    )


def _persist(path: Path, receipt: dict[str, object]) -> None:
    path.write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _fail(
    path: Path,
    receipt: dict[str, object],
    status: str,
    message: str,
) -> NoReturn:
    receipt["status"] = status
    receipt["error"] = message
    receipt["finished_at"] = _utc_now()
    _persist(path, receipt)
    raise ProviderProductionCertificationError(message)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    proof = certification_from_environment()
    artifact = proof.get("artifact")
    artifact_sha = artifact.get("sha256") if isinstance(artifact, dict) else None
    print("PROVIDER_PROOF_STATUS=PASS")
    print(f"PROVIDER_JOB_ID={proof.get('external_job_id')}")
    print(f"PROVIDER_ARTIFACT_SHA256={artifact_sha}")
