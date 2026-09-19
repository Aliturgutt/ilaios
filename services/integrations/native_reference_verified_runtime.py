"""Native-reference QA adapter for the canonical managed Desktop Video runtime.

This is an additive acceptance layer, not a second video engine. The existing
managed reference-aware runtime still performs planning, routing, provider
execution, technical QA, semantic QA, assembly and evidence. When the native
relay is configured, this adapter additionally requires independent visual
reference-consistency QA before the finished product can be accepted.

If native provider generation preserves subject/product continuity but distorts
an admitted logo, the exact original logo asset may be deterministically
composited through canonical M18 FFmpeg. The repaired output must then pass fresh
technical, semantic and reference-consistency QA before acceptance.
"""

from __future__ import annotations

import json
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.reference_assets import (
    ReferenceAssetError,
    ReferenceAssetRecord,
    ReferenceAssetRole,
    ReferenceAssetStore,
)
from services.reference_relay import ReferenceRelay
from services.runtime import DurableGrantPolicy
from services.source_media import SourceMediaStore
from src.video_automation.logo_asset_lock import (
    LogoAssetLockCompositor,
    LogoAssetLockError,
    LogoAssetLockInput,
    LogoAssetLockResult,
)
from src.video_automation.media_technical_validation import FfprobeMediaTechnicalProbe
from src.video_automation.reference_consistency_review import (
    OpenRouterReferenceConsistencyReviewer,
    ReferenceConsistencyReview,
    ReferenceConsistencyReviewError,
)
from src.video_automation.reference_image_analysis import ReferenceImageInput

from .provider_video_runtime import ObjectiveResolver, SemanticVideoReviewer
from .reference_aware_managed_provider_video_runtime import (
    ManagedReferenceAwareProviderBackedDesktopVideoRuntime,
)
from .video_runtime import VideoRuntimeError

_CRITICAL_ROLE_THRESHOLD = 0.80
_NATIVE_INPUT_REFERENCE_MODEL_ID = "bytedance/seedance-2.0-fast"
_FRAME_REFERENCE_ROLES = frozenset(
    {ReferenceAssetRole.FIRST_FRAME, ReferenceAssetRole.LAST_FRAME}
)


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
        logo_asset_lock: LogoAssetLockCompositor | None = None,
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
        self._logo_asset_lock = logo_asset_lock or LogoAssetLockCompositor()

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
        # only for this bounded QA/repair call and are not persisted outside EvidenceStore.
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
        outcome.update(
            _native_provider_evidence(
                records,
                model_id=self._model_id,
                generated_shot_count=_positive_int(outcome, "generated_shot_count"),
            )
        )

        final_path = Path(str(outcome["final_path"]))
        initial_review = self._review_consistency(final_path, references)
        asset_lock_result: LogoAssetLockResult | None = None
        review = initial_review

        if not initial_review.passed:
            if not _logo_only_repairable(initial_review):
                raise VideoRuntimeError(
                    "native reference consistency QA rejected finished video"
                )
            logo_records = tuple(record for record in records if record.role.value == "logo")
            if len(logo_records) != 1:
                raise VideoRuntimeError(
                    "deterministic logo asset-lock requires exactly one logo reference"
                )
            logo_record = logo_records[0]
            logo_reference = next(
                (
                    reference
                    for reference in references
                    if reference.sha256_hex == logo_record.sha256
                    and reference.role == "logo"
                ),
                None,
            )
            if logo_reference is None:
                raise VideoRuntimeError("logo asset-lock reference binding is inconsistent")
            locked_path = final_path.with_name(
                f"{final_path.stem}-logo-asset-lock{final_path.suffix}"
            )
            try:
                asset_lock_result = self._logo_asset_lock.apply(
                    video_path=final_path,
                    output_path=locked_path,
                    logo=LogoAssetLockInput(
                        content=logo_reference.content,
                        mime_type=logo_reference.mime_type,
                        sha256_hex=logo_reference.sha256_hex,
                        width=logo_record.width,
                        height=logo_record.height,
                        instruction=logo_reference.instruction,
                    ),
                    frame_width=_positive_int(outcome, "width"),
                    frame_height=_positive_int(outcome, "height"),
                )
            except LogoAssetLockError as error:
                raise VideoRuntimeError(
                    "native logo fidelity failed and deterministic asset-lock could not repair it"
                ) from error

            locked_digest = sha256(locked_path.read_bytes()).hexdigest()
            observation = FfprobeMediaTechnicalProbe(timeout_seconds=30).probe(locked_path)
            _verify_locked_technical(outcome, observation)
            final_semantic = self._reviewer.review(
                video_path=locked_path,
                objective=objective,
                artifact_sha256=locked_digest,
                producer_id=self.PRODUCER_ID,
                review_id=f"{request_id}-logo-asset-lock-final",
            )
            if not final_semantic.passed:
                raise VideoRuntimeError(
                    "logo asset-lock output failed final semantic acceptance"
                )
            review = self._review_consistency(locked_path, references)
            if not review.passed:
                raise VideoRuntimeError(
                    "logo asset-lock output failed final reference-consistency acceptance"
                )

            original_digest = str(outcome["artifact_sha256"])
            locked_path.replace(final_path)
            outcome["artifact_sha256"] = locked_digest
            outcome["semantic_score"] = final_semantic.score
            outcome["semantic_threshold"] = final_semantic.threshold
            outcome["duration_seconds"] = observation.duration_seconds
            outcome["width"] = observation.width
            outcome["height"] = observation.height
            outcome["frame_rate"] = observation.frames_per_second
            outcome["video_codec"] = observation.video_codec
            outcome["audio_codec"] = observation.audio_codec or "none"
            asset_lock_evidence = self._record_logo_asset_lock_evidence(
                request_id=request_id,
                job_id=job_id,
                original_video_sha256=original_digest,
                repaired_video_sha256=locked_digest,
                result=asset_lock_result,
                pre_review=initial_review,
                post_review=review,
                semantic_score=final_semantic.score,
                semantic_threshold=final_semantic.threshold,
            )
            outcome.update(asset_lock_evidence)
        else:
            outcome["logo_asset_lock_applied"] = False

        consistency_evidence = self._record_consistency_evidence(
            request_id=request_id,
            job_id=job_id,
            review=review,
            asset_lock_result=asset_lock_result,
        )
        outcome.update(consistency_evidence)
        return outcome

    def _review_consistency(
        self,
        video_path: Path,
        references: tuple[ReferenceImageInput, ...],
    ) -> ReferenceConsistencyReview:
        try:
            return self._consistency_reviewer.review(
                video_path=video_path,
                references=references,
            )
        except ReferenceConsistencyReviewError as error:
            raise VideoRuntimeError(
                "native reference consistency QA could not be established"
            ) from error

    def _record_consistency_evidence(
        self,
        *,
        request_id: str,
        job_id: str,
        review: ReferenceConsistencyReview,
        asset_lock_result: LogoAssetLockResult | None,
    ) -> dict[str, object]:
        document = {
            "schema": "ilaios.video.native-reference-consistency.v2",
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
            "logo_asset_lock_applied": asset_lock_result is not None,
            "logo_asset_lock_source_sha256": (
                asset_lock_result.source_logo_sha256
                if asset_lock_result is not None
                else None
            ),
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
        return {
            "reference_consistency_passed": True,
            "reference_consistency_score": review.score,
            "reference_consistency_threshold": review.threshold,
            "reference_consistency_subject_score": review.subject_score,
            "reference_consistency_product_score": review.product_score,
            "reference_consistency_logo_score": review.logo_score,
            "reference_consistency_evidence_digest": artifact.digest,
            "reference_consistency_provenance_hash": provenance.record_hash,
        }

    def _record_logo_asset_lock_evidence(
        self,
        *,
        request_id: str,
        job_id: str,
        original_video_sha256: str,
        repaired_video_sha256: str,
        result: LogoAssetLockResult,
        pre_review: ReferenceConsistencyReview,
        post_review: ReferenceConsistencyReview,
        semantic_score: float,
        semantic_threshold: float,
    ) -> dict[str, object]:
        document = {
            "schema": "ilaios.video.logo-asset-lock.v1",
            "request_id": request_id,
            "job_id": job_id,
            "source_logo_sha256": result.source_logo_sha256,
            "original_video_sha256": original_video_sha256,
            "repaired_video_sha256": repaired_video_sha256,
            "placement": result.placement.value,
            "x": result.x,
            "y": result.y,
            "margin": result.margin,
            "logo_width": result.logo_width,
            "logo_height": result.logo_height,
            "resized": False,
            "cropped": False,
            "recolored": False,
            "pre_logo_score": pre_review.logo_score,
            "post_logo_score": post_review.logo_score,
            "semantic_score": semantic_score,
            "semantic_threshold": semantic_threshold,
            "final_reference_consistency_passed": post_review.passed,
            "final_semantic_passed": semantic_score >= semantic_threshold,
        }
        body = json.dumps(document, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        artifact = self._evidence.put_artifact(body)
        provenance = self._evidence.append_provenance(
            job_id,
            artifact,
            "video.logo_asset_lock",
        )
        return {
            "logo_asset_lock_applied": True,
            "logo_asset_lock_source_sha256": result.source_logo_sha256,
            "logo_asset_lock_placement": result.placement.value,
            "logo_asset_lock_resized": False,
            "logo_asset_lock_cropped": False,
            "logo_asset_lock_recolored": False,
            "logo_asset_lock_evidence_digest": artifact.digest,
            "logo_asset_lock_provenance_hash": provenance.record_hash,
        }


def _native_provider_evidence(
    records: tuple[ReferenceAssetRecord, ...],
    *,
    model_id: str,
    generated_shot_count: int,
) -> dict[str, object]:
    """Describe the fail-closed native relay mode proven by the completed runtime path.

    This records that signed relay URLs were supplied to every successful provider
    dispatch. Actual remote fetch is separately proven by the relay access ledger in
    trusted-master live certification.
    """

    if generated_shot_count <= 0:
        raise VideoRuntimeError("native reference generated shot count is invalid")
    frame_records = tuple(record for record in records if record.role in _FRAME_REFERENCE_ROLES)
    if frame_records:
        mode = "frame-images"
        native_records = frame_records
    elif model_id == _NATIVE_INPUT_REFERENCE_MODEL_ID:
        mode = "input-references"
        native_records = records
    else:
        return {
            "provider_native_reference_url_used": False,
            "native_reference_mode": "private-multimodal-brief-fallback",
            "native_reference_count": 0,
            "native_reference_dispatch_count": 0,
            "native_reference_sha256s": (),
            "native_reference_relay_released": True,
        }
    return {
        "provider_native_reference_url_used": True,
        "native_reference_mode": mode,
        "native_reference_count": len(native_records),
        "native_reference_dispatch_count": generated_shot_count,
        "native_reference_sha256s": tuple(record.sha256 for record in native_records),
        # The parent runtime returns only after every provider job reached terminal
        # state; the native session fails if terminal relay cleanup fails.
        "native_reference_relay_released": True,
    }


def _logo_only_repairable(review: ReferenceConsistencyReview) -> bool:
    if review.logo_score is None or review.logo_score >= _CRITICAL_ROLE_THRESHOLD:
        return False
    for score in (review.subject_score, review.product_score):
        if score is not None and score < _CRITICAL_ROLE_THRESHOLD:
            return False
    return True


def _positive_int(outcome: dict[str, object], key: str) -> int:
    value = outcome.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise VideoRuntimeError(f"native reference outcome is missing positive {key}")
    return value


def _verify_locked_technical(outcome: dict[str, object], observation: object) -> None:
    width = getattr(observation, "width", None)
    height = getattr(observation, "height", None)
    duration = getattr(observation, "duration_seconds", None)
    video_codec = getattr(observation, "video_codec", None)
    audio_codec = getattr(observation, "audio_codec", None)
    audio_stream_count = getattr(observation, "audio_stream_count", None)
    if width != _positive_int(outcome, "width") or height != _positive_int(outcome, "height"):
        raise VideoRuntimeError("logo asset-lock changed final video dimensions")
    expected_duration = outcome.get("duration_seconds")
    if isinstance(expected_duration, bool) or not isinstance(expected_duration, (int, float)):
        raise VideoRuntimeError("native reference outcome is missing duration evidence")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        raise VideoRuntimeError("logo asset-lock duration evidence is invalid")
    if abs(float(duration) - float(expected_duration)) > 0.5:
        raise VideoRuntimeError("logo asset-lock changed final video duration")
    if video_codec != "h264":
        raise VideoRuntimeError("logo asset-lock output is not H.264")
    if audio_stream_count is None or int(audio_stream_count) < 1 or audio_codec != "aac":
        raise VideoRuntimeError("logo asset-lock output is missing required AAC audio")
