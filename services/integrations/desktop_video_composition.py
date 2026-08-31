"""Fail-closed Desktop Video provider composition.

Verified-free remains the default. Managed provider execution is available only
through the explicit ``ILAIOS_VIDEO_PROVIDER_MODE=managed-bounded`` setting and a
bounded budget value. There is no automatic free-to-paid fallback. Provider-native
references additionally require a separately configured HTTPS relay and an
independent reference-consistency acceptance layer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from services.cloudflare_reference_relay import CloudflareReferenceRelayClient
from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.reference_assets import ReferenceAssetStore
from services.reference_relay import HttpReferenceRelayClient, ReferenceRelay
from services.runtime import DurableGrantPolicy
from services.source_media import SourceMediaStore
from src.video_automation.openrouter_video_provider import SEEDANCE_FREE_MODEL_ID

from .native_reference_receipt_runtime import (
    ReceiptBoundNativeReferenceManagedDesktopVideoRuntime,
)
from .provider_video_runtime import ObjectiveResolver, UnavailableProviderVideoRuntime
from .reference_aware_managed_provider_video_runtime import (
    ManagedReferenceAwareProviderBackedDesktopVideoRuntime,
)
from .reference_aware_provider_video_runtime import (
    ReferenceAwareProviderBackedDesktopVideoRuntime,
)
from .video_runtime import DeterministicLocalVideoRuntime, VideoRuntimeError

_VERIFIED_FREE = "verified-free"
_MANAGED_BOUNDED = "managed-bounded"
_MAX_MANAGED_DESKTOP_BUDGET_USD = Decimal("1.00")
_DEFAULT_MANAGED_MODEL_ID = "bytedance/seedance-2.0-fast"
_LEGACY_RELAY_PROTOCOL = "legacy-json-v1"
_CLOUDFLARE_RELAY_PROTOCOL = "cloudflare-r2-d1-v1"


@dataclass(frozen=True, slots=True)
class DesktopVideoComposition:
    runtime: DeterministicLocalVideoRuntime
    configured: bool
    provider_id: str
    provider_mode: str
    managed_budget_usd: str | None
    native_reference_relay_configured: bool


def compose_desktop_video_runtime(
    *,
    root: Path,
    grants: DurableGrantPolicy,
    governance: GovernedRuntimeGateway,
    evidence: EvidenceStore,
    objective_resolver: ObjectiveResolver,
    api_key: str,
    reference_assets: ReferenceAssetStore,
    source_media: SourceMediaStore,
    product_identity_database: Path,
) -> DesktopVideoComposition:
    mode = os.environ.get("ILAIOS_VIDEO_PROVIDER_MODE", _VERIFIED_FREE).strip()
    if mode not in {_VERIFIED_FREE, _MANAGED_BOUNDED}:
        raise VideoRuntimeError("unknown Desktop Video provider mode")
    reference_relay = _reference_relay_from_environment(mode)
    if not api_key:
        unavailable = UnavailableProviderVideoRuntime(
            root,
            grants,
            governance,
            evidence,
            reason=(
                "Provider-backed Video Factory is unavailable because "
                "OPENROUTER_API_KEY is not configured"
            ),
        )
        return DesktopVideoComposition(
            unavailable,
            False,
            "unavailable",
            mode,
            None,
            False,
        )

    qa_model_id = os.environ.get("ILAIOS_VIDEO_QA_MODEL_ID", "openrouter/free").strip()
    if mode == _VERIFIED_FREE:
        model_id = os.environ.get("ILAIOS_VIDEO_MODEL_ID", SEEDANCE_FREE_MODEL_ID).strip()
        runtime = ReferenceAwareProviderBackedDesktopVideoRuntime(
            root,
            grants,
            governance,
            evidence,
            objective_resolver=objective_resolver,
            api_key=api_key,
            model_id=model_id,
            qa_model_id=qa_model_id,
            reference_assets=reference_assets,
            source_media=source_media,
        )
        return DesktopVideoComposition(
            runtime,
            True,
            ReferenceAwareProviderBackedDesktopVideoRuntime.PROVIDER_ID,
            mode,
            None,
            False,
        )

    budget = _managed_budget()
    managed_model_id = os.environ.get(
        "ILAIOS_VIDEO_MANAGED_MODEL_ID",
        _DEFAULT_MANAGED_MODEL_ID,
    ).strip()
    if reference_relay is None:
        managed_runtime: DeterministicLocalVideoRuntime = (
            ManagedReferenceAwareProviderBackedDesktopVideoRuntime(
                root,
                grants,
                governance,
                evidence,
                objective_resolver=objective_resolver,
                api_key=api_key,
                product_identity_database=product_identity_database,
                max_total_cost_usd=budget,
                model_id=managed_model_id,
                qa_model_id=qa_model_id,
                reference_assets=reference_assets,
                source_media=source_media,
            )
        )
    else:
        managed_runtime = ReceiptBoundNativeReferenceManagedDesktopVideoRuntime(
            root,
            grants,
            governance,
            evidence,
            objective_resolver=objective_resolver,
            api_key=api_key,
            product_identity_database=product_identity_database,
            max_total_cost_usd=budget,
            model_id=managed_model_id,
            qa_model_id=qa_model_id,
            reference_assets=reference_assets,
            source_media=source_media,
            reference_relay=reference_relay,
        )
    return DesktopVideoComposition(
        managed_runtime,
        True,
        ManagedReferenceAwareProviderBackedDesktopVideoRuntime.PROVIDER_ID,
        mode,
        str(budget),
        reference_relay is not None,
    )


def _managed_budget() -> Decimal:
    raw = os.environ.get("ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD", "").strip()
    if not raw:
        raise VideoRuntimeError(
            "managed Desktop Video requires ILAIOS_VIDEO_MANAGED_MAX_TOTAL_USD"
        )
    try:
        value = Decimal(raw)
    except InvalidOperation as error:
        raise VideoRuntimeError("managed Desktop Video budget is not a decimal") from error
    if not value.is_finite() or value <= 0 or value > _MAX_MANAGED_DESKTOP_BUDGET_USD:
        raise VideoRuntimeError("managed Desktop Video budget must be > 0 and <= 1.00 USD")
    if value * Decimal(1_000_000) != (value * Decimal(1_000_000)).to_integral_value():
        raise VideoRuntimeError("managed Desktop Video budget must have microUSD precision")
    return value


def _reference_relay_from_environment(mode: str) -> ReferenceRelay | None:
    upload_url = os.environ.get("ILAIOS_REFERENCE_RELAY_UPLOAD_URL", "").strip()
    upload_token = os.environ.get("ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN", "").strip()
    protocol = os.environ.get(
        "ILAIOS_REFERENCE_RELAY_PROTOCOL",
        _LEGACY_RELAY_PROTOCOL,
    ).strip()
    if not upload_url and not upload_token:
        return None
    if not upload_url or not upload_token:
        raise VideoRuntimeError(
            "native reference relay requires both upload URL and upload token"
        )
    if mode != _MANAGED_BOUNDED:
        raise VideoRuntimeError(
            "native reference relay is supported only in explicit managed-bounded mode"
        )
    if protocol not in {_LEGACY_RELAY_PROTOCOL, _CLOUDFLARE_RELAY_PROTOCOL}:
        raise VideoRuntimeError("native reference relay protocol is unsupported")
    try:
        if protocol == _CLOUDFLARE_RELAY_PROTOCOL:
            relay = CloudflareReferenceRelayClient(
                upload_url=upload_url,
                bearer_token=upload_token,
            )
            if not relay.ready():
                raise VideoRuntimeError("native reference relay readiness check failed")
            return relay
        return HttpReferenceRelayClient(
            upload_url=upload_url,
            bearer_token=upload_token,
        )
    except VideoRuntimeError:
        raise
    except Exception as error:
        raise VideoRuntimeError("native reference relay configuration is invalid") from error
