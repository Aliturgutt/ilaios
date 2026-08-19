"""Native-reference QA adapter for the canonical managed Desktop Video runtime.

This is an additive acceptance layer, not a second video engine. The existing
managed reference-aware runtime still performs planning, routing, provider
execution, technical QA, semantic QA, assembly and evidence. When the native
relay is configured, this adapter additionally requires independent visual
reference-consistency QA before the finished product can be accepted.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.reference_assets import ReferenceAssetError, ReferenceAssetStore
from services.reference_relay import ReferenceRelay
from services.runtime import DurableGrantPolicy
from services.source_media import SourceMediaStore
from src.video_automation.reference_consistency_review import (
    OpenRouterReferenceConsistencyReviewer,
    ReferenceConsistencyReviewError,
)
from src.video_automation.reference_image_analysis import ReferenceImageInput

from .provider_video_runtime import ObjectiveResolver, SemanticVideoReviewer
from .reference_aware_managed_provider_video_runtime import (
    ManagedReferenceAwareProviderBackedDesktopVideoRuntime,
)
from .video_runtime import VideoRuntimeError


class NativeReferenceVerifiedManagedDesktopVideoRuntime(
    ManagedReferenceAwareProviderBackedDesktopVideoRuntime
):
    """Require reference-consistency PASS for relay-enabled managed video."""

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
        reference_relay: ReferenceRelay,
        model_id: str = "bytedance/seedance-2.0-fast",
        qa_model_id: str = "openrouter/free",
        resolution: str = "480p",
        poll_interval_seconds: float = 5.0,
        max_poll_rounds: int = 144,
        reviewer: SemanticVideoReviewer | None = None,
        reference_assets: ReferenceAssetStore | None = None,
        source_media: SourceMediaStore | None = None,
        consistency_reviewer: OpenRouterReferenceConsistencyReviewer | None = None,
    ) -> None:
        super().__init__(
            root,
            grants,
            governance,
            evidence,
            objective_resolver=objective_resolver,
            api_key=api_key,
            product_identity_database=product_identity_database,
            max_total_cost_usd=max_total_cost_usd,
            model_id=model_id,
            qa_model_id=qa_model_id,
            resolution=resolution,
            poll_interval_seconds=poll_interval_seconds,
            max_poll_rounds=max_poll_rounds,
            reviewer=reviewer,
            reference_assets=reference_assets,
            source_media=source_media,
            reference_relay=reference_relay,
        )
        self._consistency_reviewer = consistency_reviewer or (
            OpenRouterReferenceConsistencyReviewer(api_key, qa_model_id)
        )

    def _generate_finished_product(
        self,
        *,
        run_root: Path,
        request_id: str,
        job_id: str,
        objective: str,
        duration_seconds: float,
    ) -> dict[str, object]:
        # Capture immutable admitted bytes before the parent releases the private
        # local blobs after successful generation. These in-memory copies exist
        # only for this bounded QA call and are not persisted outside EvidenceStore.
        records = self._reference_assets.for_request(request_id)
        try:
            references = tuple(
                ReferenceImageInput(
                    content=self._reference_assets.read_bytes(record),
                    mime_type=record.mime_type,
                    sha256_hex=record.sha256,
                    role=record.role.value,
                    instruction=record.instruction,
                )
                for record in records
            )
        except ReferenceAssetError as error:
            raise VideoRuntimeError(
                "native reference QA could not read admitted reference bytes"
            ) from error

        outcome = super()._generate_finished_product(
            run_root=run_root,
            request_id=request_id,
            job_id=job_id,
            objective=objective,
            duration_seconds=duration_seconds,
        )
        if not references:
            return outcome

        try:
            review = self._consistency_reviewer.review(
                video_path=Path(str(outcome["final_path"])),
                references=references,
            )
        except ReferenceConsistencyReviewError as error:
            raise VideoRuntimeError(
                "native reference consistency QA could not be established"
            ) from error
        if not review.passed:
            raise VideoRuntimeError("native reference consistency QA rejected finished video")

        document = {
            "schema": "ilaios.video.native-reference-consistency.v1",
            "request_id": request_id,
            "job_id": job_id,
            "reviewer_id": review.reviewer_id,
            "score": review.score,
            "threshold": review.threshold,
            "subject_score": review.subject_score,
            "product_score": review.product_score,
            "logo_score": review.logo_score,
            "detail": review.detail,
            "repair_target": review.repair_target,
            "reference_sha256s": list(review.reference_sha256s),
            "frame_sha256s": list(review.frame_sha256s),
            "passed": True,
        }
        evidence_bytes = (
            json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        artifact = self._evidence.put_artifact(evidence_bytes)
        provenance = self._evidence.append_provenance(
            job_id,
            artifact,
            "video.reference_consistency_review",
        )
        outcome["reference_consistency_passed"] = True
        outcome["reference_consistency_score"] = review.score
        outcome["reference_consistency_threshold"] = review.threshold
        outcome["reference_consistency_subject_score"] = review.subject_score
        outcome["reference_consistency_product_score"] = review.product_score
        outcome["reference_consistency_logo_score"] = review.logo_score
        outcome["reference_consistency_evidence_digest"] = artifact.digest
        outcome["reference_consistency_provenance_hash"] = provenance.record_hash
        return outcome
