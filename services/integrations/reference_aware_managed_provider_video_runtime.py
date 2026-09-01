"""Explicit managed-cost composition for the reference-aware Desktop Video Factory.

This module keeps the canonical reference-aware generation/QA path and injects the
existing managed OpenRouter provider/cost authority only when Desktop composition
explicitly selects managed-bounded mode. It does not provide automatic paid
fallback. Provider-native reference URLs are additive and are enabled only when a
separately configured short-lived relay is supplied by the composition root.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.reference_asset_admission import ReferenceAssetAdmissionStore
from services.reference_assets import ReferenceAssetStore
from services.reference_brief_cache import ReferenceBriefCache
from services.reference_relay import ReferenceRelay
from services.runtime import DurableGrantPolicy
from services.source_media import SourceMediaStore
from src.video_automation.generation_job_polling import ProviderJobObservation, ProviderJobStatus
from src.video_automation.managed_credits import ManagedCreditAccount
from src.video_automation.models import ProviderRequest, ProviderResult
from src.video_automation.openrouter_managed_video_provider import (
    OPENROUTER_MANAGED_PROVIDER_NAME,
)
from src.video_automation.openrouter_video_catalog import OpenRouterVideoModel
from src.video_automation.openrouter_video_provider import OpenRouterGeneratedAssetRetriever
from src.video_automation.reference_image_analysis import OpenRouterReferenceImageAnalyzer

from .managed_provider_video_runtime import ManagedDesktopVideoSession
from .native_reference_relay import (
    NativeReferencePreparation,
    NativeReferenceRelayBinder,
)
from .provider_video_runtime import (
    ObjectiveResolver,
    ProviderBackedDesktopVideoRuntime,
    SemanticVideoReviewer,
)
from .reference_aware_provider_video_runtime import (
    ReferenceAwareProviderBackedDesktopVideoRuntime,
)
from .video_runtime import VideoRuntimeError

_DEFAULT_MODEL_ID = "bytedance/seedance-2.0-fast"
_DEFAULT_QA_MODEL_ID = "openrouter/free"
_DEFAULT_REFERENCE_ANALYZER_MODEL_ID = "google/gemma-4-26b-a4b-it:free"
_DEFAULT_RESOLUTION = "480p"
_TERMINAL_PROVIDER_STATUSES = frozenset(
    {ProviderJobStatus.SUCCEEDED, ProviderJobStatus.FAILED, ProviderJobStatus.CANCELLED}
)


class DurableProductIdentityResolver:
    """Resolve one admitted Desktop product request to its durable tenant/principal."""

    def __init__(self, product_database: Path) -> None:
        self._database = product_database

    def resolve(self, request_id: str) -> tuple[str, str]:
        normalized_request = request_id.strip()
        if not normalized_request:
            raise VideoRuntimeError("managed Desktop product request identity is blank")
        if not self._database.is_file():
            raise VideoRuntimeError("managed Desktop product identity store is unavailable")
        connection = sqlite3.connect(
            self._database.resolve().as_uri() + "?mode=ro",
            uri=True,
            timeout=10,
        )
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                "SELECT identity.tenant_id, identity.requester_id "
                "FROM product_proofs AS proof "
                "JOIN product_proof_identity AS identity "
                "ON identity.request_id = proof.request_id "
                "WHERE proof.request_id = ? LIMIT 2",
                (normalized_request,),
            ).fetchall()
        except sqlite3.Error as error:
            raise VideoRuntimeError(
                "managed Desktop product identity lookup failed"
            ) from error
        finally:
            connection.close()
        if len(rows) != 1:
            raise VideoRuntimeError(
                "managed Desktop product request lacks one durable product identity"
            )
        tenant_id = rows[0]["tenant_id"]
        requester_id = rows[0]["requester_id"]
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise VideoRuntimeError("managed Desktop tenant identity is unavailable")
        if not isinstance(requester_id, str) or not requester_id.strip():
            raise VideoRuntimeError("managed Desktop principal identity is unavailable")
        return tenant_id.strip(), requester_id.strip()


class TenantBoundManagedDesktopVideoSession(ManagedDesktopVideoSession):
    """Bind the existing durable managed-credit authority to the admitted identity."""

    def __init__(
        self,
        *,
        identity_resolver: DurableProductIdentityResolver,
        root: Path,
        api_key: str,
        model_id: str,
        resolution: str,
        max_total_cost_usd: Decimal,
    ) -> None:
        super().__init__(
            root=root,
            api_key=api_key,
            model_id=model_id,
            resolution=resolution,
            max_total_cost_usd=max_total_cost_usd,
        )
        self._identity_resolver = identity_resolver
        self._account_switch_lock = threading.Lock()
        self._product_request_context: ContextVar[str | None] = ContextVar(
            f"managed-video-product-request-{id(self)}",
            default=None,
        )

    @contextmanager
    def bind_product_request(self, request_id: str) -> Iterator[None]:
        """Bind provider dispatches to the exact admitted product request in this call."""

        normalized = request_id.strip()
        if not normalized:
            raise VideoRuntimeError("managed Desktop product request binding is blank")
        if self._product_request_context.get() is not None:
            raise VideoRuntimeError("managed Desktop product request binding is already active")
        token = self._product_request_context.set(normalized)
        try:
            yield
        finally:
            self._product_request_context.reset(token)

    def _require_bound_product_request(self) -> str:
        request_id = self._product_request_context.get()
        if request_id is None:
            raise VideoRuntimeError(
                "managed Desktop provider dispatch lacks product request identity binding"
            )
        return request_id

    def execute(self, request: ProviderRequest) -> ProviderResult:
        product_request_id = self._require_bound_product_request()
        tenant_id, requester_id = self._identity_resolver.resolve(product_request_id)
        account = self._credit_store.seed_account(
            ManagedCreditAccount(
                tenant_id=tenant_id,
                user_id=requester_id,
                available_microusd=self.max_total_cost_microusd,
            )
        )
        # ManagedDesktopVideoSession passes _account only to the synchronous
        # durable reservation/provider-submit boundary. Serialize that narrow
        # boundary so concurrent tenants cannot observe another account.
        with self._account_switch_lock:
            previous = self._account
            self._account = account
            try:
                return super().execute(request)
            finally:
                self._account = previous


class NativeReferenceTenantBoundManagedDesktopVideoSession(
    TenantBoundManagedDesktopVideoSession
):
    """Add provider-native relay fields to the same managed provider session."""

    def __init__(
        self,
        *,
        native_reference_binder: NativeReferenceRelayBinder,
        identity_resolver: DurableProductIdentityResolver,
        root: Path,
        api_key: str,
        model_id: str,
        resolution: str,
        max_total_cost_usd: Decimal,
    ) -> None:
        super().__init__(
            identity_resolver=identity_resolver,
            root=root,
            api_key=api_key,
            model_id=model_id,
            resolution=resolution,
            max_total_cost_usd=max_total_cost_usd,
        )
        self._native_reference_binder = native_reference_binder
        self._native_preparation_context: ContextVar[NativeReferencePreparation | None] = (
            ContextVar(f"managed-video-native-reference-{id(self)}", default=None)
        )
        self._native_jobs: dict[str, NativeReferencePreparation] = {}
        self._native_jobs_lock = threading.Lock()

    def execute(self, request: ProviderRequest) -> ProviderResult:
        token = self._native_preparation_context.set(None)
        try:
            result = super().execute(request)
            preparation = self._native_preparation_context.get()
            if preparation is None:
                return result
            metadata = dict(result.metadata)
            metadata.update(_native_result_metadata(preparation))
            if result.success and result.external_id is not None:
                with self._native_jobs_lock:
                    if result.external_id in self._native_jobs:
                        raise VideoRuntimeError("native reference provider job identity collision")
                    self._native_jobs[result.external_id] = preparation
            else:
                self._native_reference_binder.release(preparation)
            return replace(result, metadata=metadata)
        finally:
            self._native_preparation_context.reset(token)

    def poll(self, provider_job_id: str) -> ProviderJobObservation:
        observation = super().poll(provider_job_id)
        if observation.status not in _TERMINAL_PROVIDER_STATUSES:
            return observation
        with self._native_jobs_lock:
            preparation = self._native_jobs.pop(provider_job_id, None)
        if preparation is None:
            return observation
        # A terminal provider job no longer needs the provider-fetchable image.
        # Cleanup failure is a privacy failure and therefore blocks acceptance;
        # ticket expiry remains the crash-only safety net.
        self._native_reference_binder.release(preparation)
        metadata = dict(observation.metadata)
        metadata.update(_native_observation_metadata(preparation))
        return replace(observation, metadata=metadata)

    def _normalized_request(
        self, request: ProviderRequest
    ) -> tuple[ProviderRequest, Mapping[str, object]]:
        normalized, item = super()._normalized_request(request)
        product_request_id = self._require_bound_product_request()
        model = self._exact_live_model(normalized)
        preparation = self._native_reference_binder.prepare(
            request_id=product_request_id,
            model=model,
        )
        merged_item: dict[str, object] = dict(item)
        for key, value in preparation.item_fields.items():
            if key in merged_item and merged_item[key] != value:
                self._native_reference_binder.release(preparation)
                raise VideoRuntimeError("native reference field collides with provider request")
            merged_item[key] = value
        payload = dict(normalized.payload)
        payload["items_json"] = json.dumps(
            [merged_item], sort_keys=True, separators=(",", ":")
        )
        self._native_preparation_context.set(preparation)
        return (
            ProviderRequest(
                request_id=normalized.request_id,
                job_id=normalized.job_id,
                provider_name=normalized.provider_name,
                operation=normalized.operation,
                payload=payload,
            ),
            merged_item,
        )

    def _exact_live_model(self, request: ProviderRequest) -> OpenRouterVideoModel:
        model_id = request.payload.get("model_id")
        if not isinstance(model_id, str) or not model_id.strip():
            raise VideoRuntimeError("native reference request model_id is unavailable")
        matches = tuple(
            model
            for model in self._catalog.paid_eligible_models()
            if model.model_id == model_id
        )
        if len(matches) != 1:
            raise VideoRuntimeError(
                "native reference selected model is absent from the live paid catalog"
            )
        return matches[0]


class ManagedReferenceAwareProviderBackedDesktopVideoRuntime(
    ReferenceAwareProviderBackedDesktopVideoRuntime
):
    """Reference-aware canonical Desktop runtime with explicit managed spending."""

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
        product_identity_database: Path,
        max_total_cost_usd: Decimal,
        model_id: str = _DEFAULT_MODEL_ID,
        qa_model_id: str = _DEFAULT_QA_MODEL_ID,
        resolution: str = _DEFAULT_RESOLUTION,
        poll_interval_seconds: float = 5.0,
        max_poll_rounds: int = 144,
        reviewer: SemanticVideoReviewer | None = None,
        reference_assets: ReferenceAssetStore | None = None,
        source_media: SourceMediaStore | None = None,
        reference_relay: ReferenceRelay | None = None,
    ) -> None:
        resolver = DurableProductIdentityResolver(product_identity_database)
        data_root = root.parent
        reference_store = reference_assets or ReferenceAssetAdmissionStore(
            data_root / "reference-assets.sqlite3",
            data_root / "reference-assets" / "blobs",
        )
        source_store = source_media or SourceMediaStore(
            data_root / "source-media.sqlite3",
            data_root / "source-media" / "blobs",
        )
        if reference_relay is None:
            session: TenantBoundManagedDesktopVideoSession = (
                TenantBoundManagedDesktopVideoSession(
                    identity_resolver=resolver,
                    root=root / "managed-provider",
                    api_key=api_key,
                    model_id=model_id,
                    resolution=resolution,
                    max_total_cost_usd=max_total_cost_usd,
                )
            )
        else:
            session = NativeReferenceTenantBoundManagedDesktopVideoSession(
                native_reference_binder=NativeReferenceRelayBinder(
                    reference_assets=reference_store,
                    relay=reference_relay,
                ),
                identity_resolver=resolver,
                root=root / "managed-provider",
                api_key=api_key,
                model_id=model_id,
                resolution=resolution,
                max_total_cost_usd=max_total_cost_usd,
            )
        ProviderBackedDesktopVideoRuntime.__init__(
            self,
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
        self._reference_assets = reference_store
        self._source_media = source_store
        self._reference_analyzer = OpenRouterReferenceImageAnalyzer(
            api_key,
            _DEFAULT_REFERENCE_ANALYZER_MODEL_ID,
        )
        self._reference_brief_cache = ReferenceBriefCache(
            data_root / "reference-briefs.sqlite3"
        )
        self._managed_reference_session = session
        self._native_reference_relay_configured = reference_relay is not None

    @property
    def native_reference_relay_configured(self) -> bool:
        return self._native_reference_relay_configured

    def _generate_finished_product(
        self,
        *,
        run_root: Path,
        request_id: str,
        job_id: str,
        objective: str,
        duration_seconds: float,
    ) -> dict[str, object]:
        # ProviderExecution creates provider-facing generation dispatch IDs, which
        # are intentionally not product identity keys. Carry the exact admitted
        # product request through a request-scoped context instead of guessing
        # identity from a downstream dispatch/job identifier.
        with self._managed_reference_session.bind_product_request(request_id):
            return super()._generate_finished_product(
                run_root=run_root,
                request_id=request_id,
                job_id=job_id,
                objective=objective,
                duration_seconds=duration_seconds,
            )


def _native_result_metadata(
    preparation: NativeReferencePreparation,
) -> dict[str, str | int | bool]:
    return {
        "provider_native_reference_url_used": preparation.provider_native_reference_url_used,
        "native_reference_mode": preparation.mode,
        "native_reference_count": len(preparation.tickets),
    }


def _native_observation_metadata(
    preparation: NativeReferencePreparation,
) -> dict[str, str]:
    return {
        "provider_native_reference_url_used": (
            "true" if preparation.provider_native_reference_url_used else "false"
        ),
        "native_reference_mode": preparation.mode,
        "native_reference_count": str(len(preparation.tickets)),
        "native_reference_sha256s": ",".join(preparation.reference_sha256s),
        "native_reference_relay_released": "true",
    }
