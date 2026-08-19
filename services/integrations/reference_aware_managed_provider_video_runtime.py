"""Explicit managed-cost composition for the reference-aware Desktop Video Factory.

This module keeps the canonical reference-aware generation/QA path and injects the
existing managed OpenRouter provider/cost authority only when Desktop composition
explicitly selects managed-bounded mode. It does not provide automatic paid
fallback.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from decimal import Decimal
from pathlib import Path

from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.reference_asset_admission import ReferenceAssetAdmissionStore
from services.reference_assets import ReferenceAssetStore
from services.reference_brief_cache import ReferenceBriefCache
from services.runtime import DurableGrantPolicy
from services.source_media import SourceMediaStore
from src.video_automation.managed_credits import ManagedCreditAccount
from src.video_automation.models import ProviderRequest, ProviderResult
from src.video_automation.openrouter_managed_video_provider import (
    OPENROUTER_MANAGED_PROVIDER_NAME,
)
from src.video_automation.openrouter_video_provider import OpenRouterGeneratedAssetRetriever
from src.video_automation.reference_image_analysis import OpenRouterReferenceImageAnalyzer

from .managed_provider_video_runtime import ManagedDesktopVideoSession
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
_DEFAULT_RESOLUTION = "480p"


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
    ) -> None:
        resolver = DurableProductIdentityResolver(product_identity_database)
        session = TenantBoundManagedDesktopVideoSession(
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
        data_root = root.parent
        self._reference_assets = reference_assets or ReferenceAssetAdmissionStore(
            data_root / "reference-assets.sqlite3",
            data_root / "reference-assets" / "blobs",
        )
        self._source_media = source_media or SourceMediaStore(
            data_root / "source-media.sqlite3",
            data_root / "source-media" / "blobs",
        )
        self._reference_analyzer = OpenRouterReferenceImageAnalyzer(
            api_key,
            _DEFAULT_QA_MODEL_ID,
        )
        self._reference_brief_cache = ReferenceBriefCache(
            data_root / "reference-briefs.sqlite3"
        )
        self._managed_reference_session = session

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
