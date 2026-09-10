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
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import cast

from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.reference_asset_admission import ReferenceAssetAdmissionStore
from services.reference_assets import ReferenceAssetStore
from services.reference_brief_cache import ReferenceBriefCache
from services.reference_relay import ReferenceRelay
from services.runtime import DurableGrantPolicy
from services.source_media import SourceMediaStore
from src.video_automation.generation_execution_tracking import GenerationDispatchExecution
from src.video_automation.generation_job_polling import ProviderJobObservation, ProviderJobStatus
from src.video_automation.managed_credits import (
    ManagedCreditAccount,
    microusd_to_usd,
)
from src.video_automation.models import MetadataValue, ProviderRequest, ProviderResult
from src.video_automation.openrouter_managed_video_provider import (
    OPENROUTER_MANAGED_PROVIDER_NAME,
)
from src.video_automation.openrouter_video_catalog import OpenRouterVideoModel
from src.video_automation.openrouter_video_provider import OpenRouterGeneratedAssetRetriever
from src.video_automation.provider_production_certification import (
    CertificationShape,
    certification_price,
    certification_provider_cost_ceiling,
    select_certification_model,
)
from src.video_automation.reference_image_analysis import OpenRouterReferenceImageAnalyzer

from .desktop_video_runtime import requested_duration
from .managed_provider_video_runtime import ManagedDesktopVideoSession
from .native_reference_relay import (
    NativeReferencePreparation,
    NativeReferenceRelayBinder,
)
from .provider_video_runtime import (
    ObjectiveResolver,
    ProviderBackedDesktopVideoRuntime,
    ProviderCostEvidence,
    SemanticVideoReviewer,
    _partition_duration,
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
_MICRO_USD_PER_MINOR_USD = 10_000


@dataclass(frozen=True, slots=True)
class ApprovedProductBudget:
    """Existing approved product proposal budget bound to one tenant/request."""

    request_id: str
    tenant_id: str
    requester_id: str
    approval_id: str
    approved_budget_microusd: int


@dataclass(frozen=True, slots=True)
class ManagedVideoPreflightEstimate:
    """Live provider estimate shown before the existing human approval boundary."""

    provider: str
    model: str
    resolution: str
    planned_generation_count: int
    estimated_cost_microusd: int
    reserved_ceiling_microusd: int
    approved_budget_microusd: int

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "model": self.model,
            "resolution": self.resolution,
            "planned_generation_count": self.planned_generation_count,
            "retry_policy": "no automatic paid retry; every new paid dispatch shares the same approved job budget",
            "estimated_cost_usd": str(microusd_to_usd(self.estimated_cost_microusd)),
            "maximum_approved_spend_usd": str(
                microusd_to_usd(self.approved_budget_microusd)
            ),
            "reserved_provider_ceiling_usd": str(
                microusd_to_usd(self.reserved_ceiling_microusd)
            ),
            "estimate_is_actual_cost": False,
            "paid_provider": True,
        }


class DurableProductIdentityResolver:
    """Resolve one admitted Desktop product request to its durable tenant/principal."""

    def __init__(self, product_database: Path) -> None:
        self._database = product_database

    def resolve(self, request_id: str) -> tuple[str, str]:
        normalized_request = request_id.strip()
        if not normalized_request:
            raise VideoRuntimeError("managed Desktop product request identity is blank")
        row = self._product_row(normalized_request)
        tenant_id = row["tenant_id"]
        requester_id = row["requester_id"]
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise VideoRuntimeError("managed Desktop tenant identity is unavailable")
        if not isinstance(requester_id, str) or not requester_id.strip():
            raise VideoRuntimeError("managed Desktop principal identity is unavailable")
        return tenant_id.strip(), requester_id.strip()

    def approved_budget(
        self,
        request_id: str,
        *,
        approval_proven: bool,
    ) -> ApprovedProductBudget:
        """Read the immutable approved proposal budget for this exact product request."""

        normalized_request = request_id.strip()
        if not normalized_request:
            raise VideoRuntimeError("managed Desktop product request identity is blank")
        if not approval_proven:
            raise VideoRuntimeError(
                "paid Seedance execution requires explicit approval for this exact request"
            )
        row = self._product_row(normalized_request)
        tenant_id = row["tenant_id"]
        requester_id = row["requester_id"]
        proposal_id = row["proposal_id"]
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise VideoRuntimeError("managed Desktop tenant identity is unavailable")
        if not isinstance(requester_id, str) or not requester_id.strip():
            raise VideoRuntimeError("managed Desktop principal identity is unavailable")
        if not isinstance(proposal_id, str) or not proposal_id.strip():
            raise VideoRuntimeError("managed Desktop approved proposal identity is unavailable")

        control_plane_database = self._database.parent / "control-plane.sqlite3"
        if not control_plane_database.is_file():
            raise VideoRuntimeError("managed Desktop control-plane budget store is unavailable")
        connection = sqlite3.connect(
            control_plane_database.resolve().as_uri() + "?mode=ro",
            uri=True,
            timeout=10,
        )
        connection.row_factory = sqlite3.Row
        try:
            proposal = connection.execute(
                "SELECT proposal_json FROM proposals WHERE proposal_id = ? LIMIT 2",
                (proposal_id.strip(),),
            ).fetchall()
        except sqlite3.Error as error:
            raise VideoRuntimeError("managed Desktop proposal budget lookup failed") from error
        finally:
            connection.close()
        if len(proposal) != 1:
            raise VideoRuntimeError("managed Desktop request lacks one approved proposal budget")
        try:
            payload = json.loads(str(proposal[0]["proposal_json"]))
            minor = payload["goal"]["budget"]["max_external_spend_minor"]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise VideoRuntimeError("managed Desktop proposal budget evidence is malformed") from error
        if isinstance(minor, bool) or not isinstance(minor, int) or minor <= 0:
            raise VideoRuntimeError(
                "paid Seedance execution requires a positive user-approved USD budget"
            )
        approved_microusd = minor * _MICRO_USD_PER_MINOR_USD
        return ApprovedProductBudget(
            request_id=normalized_request,
            tenant_id=tenant_id.strip(),
            requester_id=requester_id.strip(),
            approval_id=normalized_request,
            approved_budget_microusd=approved_microusd,
        )

    def _product_row(self, request_id: str) -> sqlite3.Row:
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
                "SELECT proof.proposal_id, identity.tenant_id, identity.requester_id "
                "FROM product_proofs AS proof "
                "JOIN product_proof_identity AS identity "
                "ON identity.request_id = proof.request_id "
                "WHERE proof.request_id = ? LIMIT 2",
                (request_id,),
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
        return cast(sqlite3.Row, rows[0])


class TenantBoundManagedDesktopVideoSession(ManagedDesktopVideoSession):
    """Bind the existing durable managed-credit authority to approved job spend."""

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
            max_request_cost_usd=max_total_cost_usd,
        )
        self._identity_resolver = identity_resolver
        self._approval_checker: Callable[[str], bool] | None = None
        self._account_switch_lock = threading.Lock()
        self._budget_jobs_lock = threading.Lock()
        self._budget_jobs: dict[str, tuple[ApprovedProductBudget, str]] = {}
        self._budget_summaries: dict[str, dict[str, object]] = {}
        self._product_request_context: ContextVar[str | None] = ContextVar(
            f"managed-video-product-request-{id(self)}",
            default=None,
        )

    def configure_approval_checker(self, checker: Callable[[str], bool]) -> None:
        if self._approval_checker is not None:
            raise VideoRuntimeError("managed Desktop approval checker is already configured")
        self._approval_checker = checker

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

    def preflight_estimate(
        self,
        *,
        objective: str,
        approved_budget_microusd: int,
    ) -> ManagedVideoPreflightEstimate:
        if approved_budget_microusd <= 0:
            raise VideoRuntimeError("paid Seedance preflight requires a positive approved budget")
        duration = requested_duration(objective)
        durations = _partition_duration(duration)
        models = self._catalog.paid_eligible_models()
        estimated_total = 0
        reserved_total = 0
        approved_budget_usd = microusd_to_usd(approved_budget_microusd)
        for shot_duration in durations:
            shape = CertificationShape(
                model_id=self._model_id,
                duration_seconds=int(round(shot_duration)),
                resolution=self._resolution,
                aspect_ratio="16:9",
                generate_audio=self._generate_audio,
                max_unit_price_usd=self._max_unit_price_usd,
                max_total_cost_usd=approved_budget_usd,
            )
            model = select_certification_model(models, shape)
            price = certification_price(model, shape)
            provider_ceiling = certification_provider_cost_ceiling(
                price,
                shape,
                contingency_bps=0,
            )
            estimated_total += price.estimated_total_microusd
            reserved_total += provider_ceiling
        if reserved_total > approved_budget_microusd:
            raise VideoRuntimeError(
                "estimated paid Seedance spend exceeds the user-approved job budget; reapproval required"
            )
        return ManagedVideoPreflightEstimate(
            provider=OPENROUTER_MANAGED_PROVIDER_NAME,
            model=self._model_id,
            resolution=self._resolution,
            planned_generation_count=len(durations),
            estimated_cost_microusd=estimated_total,
            reserved_ceiling_microusd=reserved_total,
            approved_budget_microusd=approved_budget_microusd,
        )

    def execute(self, request: ProviderRequest) -> ProviderResult:
        product_request_id = self._require_bound_product_request()
        checker = self._approval_checker
        if checker is None:
            self._store_reapproval_summary(
                product_request_id,
                approval_id=product_request_id,
                reason="paid Seedance execution has no configured approval authority",
            )
            return _budget_failure(
                request,
                "approval_required",
                "paid Seedance execution has no configured approval authority",
                {"approval_id": product_request_id, "reapproval_required": "true"},
            )
        try:
            approved = self._identity_resolver.approved_budget(
                product_request_id,
                approval_proven=checker(product_request_id),
            )
        except Exception as error:  # noqa: BLE001
            self._store_reapproval_summary(
                product_request_id,
                approval_id=product_request_id,
                reason=str(error).strip() or error.__class__.__name__,
            )
            return _budget_failure(
                request,
                "approval_required",
                str(error).strip() or error.__class__.__name__,
                {"approval_id": product_request_id, "reapproval_required": "true"},
            )

        account_user_id = f"{approved.requester_id}::video-job::{approved.request_id}"
        account = self._credit_store.seed_account(
            ManagedCreditAccount(
                tenant_id=approved.tenant_id,
                user_id=account_user_id,
                available_microusd=approved.approved_budget_microusd,
            )
        )
        with self._account_switch_lock:
            previous = self._account
            self._account = account
            previous_request_ceiling = self._max_request_cost_usd
            self._max_request_cost_usd = microusd_to_usd(
                approved.approved_budget_microusd
            )
            try:
                result = super().execute(request)
            finally:
                self._max_request_cost_usd = previous_request_ceiling
                self._account = previous

        metadata = dict(result.metadata)
        metadata.update(_approval_metadata(approved, self._model_id))
        if not result.success or result.external_id is None:
            if "insufficient ILAIOS credits" in (result.error_message or ""):
                current = self._credit_store.get_account(
                    tenant_id=approved.tenant_id,
                    user_id=account_user_id,
                )
                summary = _budget_summary(
                    approved,
                    model_id=self._model_id,
                    actual_microusd=(
                        approved.approved_budget_microusd
                        - current.available_microusd
                        - current.reserved_microusd
                    ),
                    remaining_microusd=current.available_microusd,
                    event="REAPPROVAL_REQUIRED",
                    reapproval_required=True,
                )
                with self._budget_jobs_lock:
                    self._budget_summaries[approved.request_id] = summary
                metadata.update(
                    {
                        "budget_event": "REAPPROVAL_REQUIRED",
                        "reapproval_required": "true",
                    }
                )
            return replace(result, metadata=metadata)

        authorization_id = metadata.get("credit_authorization_id")
        if not isinstance(authorization_id, str) or not authorization_id.strip():
            return _budget_failure(
                request,
                "managed_budget_evidence_missing",
                "paid Seedance result omitted durable budget authorization evidence",
                metadata,
            )
        persistent = self._credit_store.get_authorization(authorization_id)
        current = self._credit_store.get_account(
            tenant_id=approved.tenant_id,
            user_id=account_user_id,
        )
        cumulative = (
            approved.approved_budget_microusd
            - current.available_microusd
            - current.reserved_microusd
        )
        metadata.update(
            {
                "estimated_cost_usd": str(
                    microusd_to_usd(persistent.estimated_cost_microusd)
                ),
                "cumulative_job_spend_usd": str(microusd_to_usd(cumulative)),
                "remaining_budget_usd": str(
                    microusd_to_usd(current.available_microusd)
                ),
                "retry_spend_usd": "0",
                "budget_event": "PROVIDER_COST_RESERVED",
                "reapproval_required": "false",
            }
        )
        with self._budget_jobs_lock:
            self._budget_jobs[result.external_id] = (approved, account_user_id)
        return replace(result, metadata=metadata)

    def poll(self, provider_job_id: str) -> ProviderJobObservation:
        with self._account_switch_lock:
            observation = super().poll(provider_job_id)
            if observation.status in _TERMINAL_PROVIDER_STATUSES:
                with self._lock:
                    self._contexts.pop(provider_job_id, None)
        if observation.status not in _TERMINAL_PROVIDER_STATUSES:
            return observation
        with self._budget_jobs_lock:
            budget_context = self._budget_jobs.get(provider_job_id)
        if budget_context is None:
            return observation
        approved, account_user_id = budget_context
        current = self._credit_store.get_account(
            tenant_id=approved.tenant_id,
            user_id=account_user_id,
        )
        metadata = dict(observation.metadata)
        actual_raw = metadata.get("actual_provider_cost_microusd")
        try:
            actual = int(actual_raw) if actual_raw is not None else 0
        except (TypeError, ValueError) as error:
            raise VideoRuntimeError("managed actual provider cost evidence is malformed") from error
        cumulative = (
            approved.approved_budget_microusd
            - current.available_microusd
            - current.reserved_microusd
        )
        summary = _budget_summary(
            approved,
            model_id=self._model_id,
            actual_microusd=cumulative,
            remaining_microusd=current.available_microusd,
            event="PROVIDER_COST_SETTLED",
            reapproval_required=False,
        )
        with self._budget_jobs_lock:
            self._budget_summaries[approved.request_id] = summary
            self._budget_jobs.pop(provider_job_id, None)
        metadata.update(
            _approval_metadata(approved, self._model_id)
            | {
                "actual_provider_cost_usd": str(microusd_to_usd(actual)),
                "cumulative_job_spend_usd": str(microusd_to_usd(cumulative)),
                "remaining_budget_usd": str(
                    microusd_to_usd(current.available_microusd)
                ),
                "retry_spend_usd": "0",
                "budget_event": "PROVIDER_COST_SETTLED",
                "reapproval_required": "false",
            }
        )
        return replace(observation, metadata=metadata)

    def verify(
        self, records: Sequence[GenerationDispatchExecution]
    ) -> ProviderCostEvidence:
        product_request_id = self._require_bound_product_request()
        checker = self._approval_checker
        if checker is None:
            raise VideoRuntimeError("managed Desktop approval authority is unavailable")
        approved = self._identity_resolver.approved_budget(
            product_request_id,
            approval_proven=checker(product_request_id),
        )
        if not records:
            raise VideoRuntimeError("managed provider cost evidence is missing")
        actual_total = 0
        ceiling_total = 0
        for record in records:
            metadata: Mapping[str, str] = record.metadata
            if metadata.get("managed_cost_proven") != "true":
                raise VideoRuntimeError("managed provider terminal cost is not proven")
            if metadata.get("approval_id") != approved.approval_id:
                raise VideoRuntimeError("managed provider approval evidence does not match job")
            if metadata.get("approved_budget_usd") != str(
                microusd_to_usd(approved.approved_budget_microusd)
            ):
                raise VideoRuntimeError("managed provider approved budget evidence changed")
            if metadata.get("budget_tenant_id") != approved.tenant_id:
                raise VideoRuntimeError("managed provider tenant budget evidence changed")
            if metadata.get("model") != self._model_id:
                raise VideoRuntimeError("managed provider model budget evidence changed")
            try:
                actual = int(metadata["actual_provider_cost_microusd"])
                ceiling = int(metadata["provider_cost_ceiling_microusd"])
            except (KeyError, TypeError, ValueError) as error:
                raise VideoRuntimeError("managed provider cost evidence is malformed") from error
            if actual < 0 or ceiling < 0 or actual > ceiling:
                raise VideoRuntimeError("managed provider terminal cost violated dispatch ceiling")
            actual_total += actual
            ceiling_total += ceiling
        if actual_total > approved.approved_budget_microusd:
            raise VideoRuntimeError("managed provider actual total exceeded approved job budget")
        if ceiling_total > approved.approved_budget_microusd:
            raise VideoRuntimeError("managed provider reserved total exceeded approved job budget")
        account_user_id = f"{approved.requester_id}::video-job::{approved.request_id}"
        current = self._credit_store.get_account(
            tenant_id=approved.tenant_id,
            user_id=account_user_id,
        )
        cumulative = (
            approved.approved_budget_microusd
            - current.available_microusd
            - current.reserved_microusd
        )
        if cumulative != actual_total:
            raise VideoRuntimeError("managed provider cumulative spend evidence is inconsistent")
        summary = _budget_summary(
            approved,
            model_id=self._model_id,
            actual_microusd=actual_total,
            remaining_microusd=current.available_microusd,
            event="FINAL_PROVIDER_COST_RECONCILED",
            reapproval_required=False,
        )
        with self._budget_jobs_lock:
            self._budget_summaries[approved.request_id] = summary
        return ProviderCostEvidence(
            mode="managed-user-approved-budget",
            proven=True,
            zero=actual_total == 0,
            actual_microusd=actual_total,
            ceiling_microusd=approved.approved_budget_microusd,
        )

    def budget_evidence(self, request_id: str) -> dict[str, object]:
        normalized = request_id.strip()
        if not normalized:
            raise VideoRuntimeError("managed Video budget evidence request is blank")
        with self._budget_jobs_lock:
            value = self._budget_summaries.get(normalized)
            if value is None:
                raise VideoRuntimeError("managed Video budget evidence is unavailable")
            return dict(value)

    def _store_reapproval_summary(
        self,
        request_id: str,
        *,
        approval_id: str,
        reason: str,
    ) -> None:
        with self._budget_jobs_lock:
            self._budget_summaries[request_id] = {
                "approval_id": approval_id,
                "provider": OPENROUTER_MANAGED_PROVIDER_NAME,
                "model": self._model_id,
                "budget_event": "REAPPROVAL_REQUIRED",
                "budget_event_reason": reason,
                "reapproval_required": True,
                "retry_spend_usd": "0",
            }


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
        session.configure_approval_checker(governance.approval_proven)
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

    def preflight_cost_estimate(
        self,
        *,
        objective: str,
        max_external_spend_minor: int,
    ) -> dict[str, object]:
        if (
            isinstance(max_external_spend_minor, bool)
            or not isinstance(max_external_spend_minor, int)
            or max_external_spend_minor <= 0
        ):
            raise VideoRuntimeError(
                "paid Seedance requires a positive user-approved external-spend budget"
            )
        approved_microusd = max_external_spend_minor * _MICRO_USD_PER_MINOR_USD
        estimate = self._managed_reference_session.preflight_estimate(
            objective=objective,
            approved_budget_microusd=approved_microusd,
        )
        return estimate.as_dict()

    def budget_evidence(self, request_id: str) -> dict[str, object]:
        return self._managed_reference_session.budget_evidence(request_id)

    def _generate_finished_product(
        self,
        *,
        run_root: Path,
        request_id: str,
        job_id: str,
        objective: str,
        duration_seconds: float,
    ) -> dict[str, object]:
        with self._managed_reference_session.bind_product_request(request_id):
            return super()._generate_finished_product(
                run_root=run_root,
                request_id=request_id,
                job_id=job_id,
                objective=objective,
                duration_seconds=duration_seconds,
            )


def _approval_metadata(
    approved: ApprovedProductBudget,
    model_id: str,
) -> dict[str, str]:
    return {
        "approval_id": approved.approval_id,
        "approved_budget_usd": str(
            microusd_to_usd(approved.approved_budget_microusd)
        ),
        "budget_tenant_id": approved.tenant_id,
        "budget_requester_id": approved.requester_id,
        "provider": OPENROUTER_MANAGED_PROVIDER_NAME,
        "model": model_id,
    }


def _budget_summary(
    approved: ApprovedProductBudget,
    *,
    model_id: str,
    actual_microusd: int,
    remaining_microusd: int,
    event: str,
    reapproval_required: bool,
) -> dict[str, object]:
    if actual_microusd < 0 or remaining_microusd < 0:
        raise VideoRuntimeError("managed Video budget summary cannot be negative")
    if actual_microusd + remaining_microusd > approved.approved_budget_microusd:
        raise VideoRuntimeError("managed Video budget summary exceeds approved budget")
    actual_usd = str(microusd_to_usd(actual_microusd))
    return {
        "approval_id": approved.approval_id,
        "approved_budget_usd": str(
            microusd_to_usd(approved.approved_budget_microusd)
        ),
        "provider": OPENROUTER_MANAGED_PROVIDER_NAME,
        "model": model_id,
        "budget_tenant_id": approved.tenant_id,
        "budget_requester_id": approved.requester_id,
        "actual_provider_cost_usd": actual_usd,
        "cumulative_job_spend_usd": actual_usd,
        "remaining_budget_usd": str(microusd_to_usd(remaining_microusd)),
        "retry_spend_usd": "0",
        "budget_event": event,
        "budget_events": [event],
        "reapproval_required": reapproval_required,
        "final_actual_cost_usd": actual_usd,
    }


def _budget_failure(
    request: ProviderRequest,
    code: str,
    message: str,
    metadata: Mapping[str, MetadataValue],
) -> ProviderResult:
    return ProviderResult(
        request_id=request.request_id,
        provider_name=request.provider_name,
        success=False,
        error_code=code,
        error_message=message,
        metadata=metadata,
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
