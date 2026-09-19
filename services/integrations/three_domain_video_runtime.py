"""Three-domain final perceptual admission for canonical Video runtimes.

This module is an additive runtime wrapper. It preserves the existing VISUAL
review performed by the canonical provider runtime and requires independent
AUDIO and BRAND reviews against the exact same final MP4 before execution can
return a finished product.
"""

from __future__ import annotations

from pathlib import Path

from src.video_automation.perceptual_review import (
    PerceptualReviewSubmission,
    admit_perceptual_reviews,
)
from src.video_automation.video_skills import QaDomain

from .native_reference_receipt_runtime import (
    ReceiptBoundNativeReferenceManagedDesktopVideoRuntime,
)
from .provider_video_runtime import SemanticVideoReviewer
from .reference_aware_managed_provider_video_runtime import (
    ManagedReferenceAwareProviderBackedDesktopVideoRuntime,
)
from .reference_aware_provider_video_runtime import (
    ReferenceAwareProviderBackedDesktopVideoRuntime,
)
from .video_runtime import VideoRuntimeError


class _FinalDomainReviewConfig:
    """Shared fail-closed configuration for exact-artifact AUDIO/BRAND review."""

    PRODUCER_ID = "ilaios-provider-video-factory"
    _final_audio_reviewer: SemanticVideoReviewer | None = None
    _final_brand_reviewer: SemanticVideoReviewer | None = None

    def configure_final_perceptual_reviewers(
        self,
        *,
        audio_reviewer: SemanticVideoReviewer,
        brand_reviewer: SemanticVideoReviewer,
    ) -> None:
        if audio_reviewer.reviewer_id == brand_reviewer.reviewer_id:
            raise VideoRuntimeError("final AUDIO and BRAND reviewers must have distinct identities")
        if audio_reviewer.reviewer_id == self.PRODUCER_ID:
            raise VideoRuntimeError("final AUDIO reviewer must be independent from producer")
        if brand_reviewer.reviewer_id == self.PRODUCER_ID:
            raise VideoRuntimeError("final BRAND reviewer must be independent from producer")
        self._final_audio_reviewer = audio_reviewer
        self._final_brand_reviewer = brand_reviewer

    def _apply_final_domain_reviews(
        self,
        *,
        outcome: dict[str, object],
        objective: str,
        request_id: str,
    ) -> dict[str, object]:
        audio_reviewer = self._final_audio_reviewer
        brand_reviewer = self._final_brand_reviewer
        if audio_reviewer is None or brand_reviewer is None:
            raise VideoRuntimeError("final AUDIO/BRAND perceptual reviewers are not configured")

        final_path_raw = outcome.get("final_path")
        artifact_sha_raw = outcome.get("artifact_sha256")
        if not isinstance(final_path_raw, (str, Path)):
            raise VideoRuntimeError("final video path is unavailable for perceptual admission")
        if not isinstance(artifact_sha_raw, str):
            raise VideoRuntimeError("final video digest is unavailable for perceptual admission")

        final_path = Path(final_path_raw)
        audio_review = audio_reviewer.review(
            video_path=final_path,
            objective=objective,
            artifact_sha256=artifact_sha_raw,
            producer_id=self.PRODUCER_ID,
            review_id=f"{request_id}-final-audio",
        )
        brand_review = brand_reviewer.review(
            video_path=final_path,
            objective=objective,
            artifact_sha256=artifact_sha_raw,
            producer_id=self.PRODUCER_ID,
            review_id=f"{request_id}-final-brand",
        )
        _require_domain(audio_review, QaDomain.AUDIO)
        _require_domain(brand_review, QaDomain.BRAND)

        admitted = admit_perceptual_reviews(
            (audio_review, brand_review),
            artifact_sha256=artifact_sha_raw,
            producer_id=self.PRODUCER_ID,
        )
        if len(admitted) != 2 or not audio_review.passed or not brand_review.passed:
            raise VideoRuntimeError("final video AUDIO/BRAND perceptual acceptance failed")

        outcome["audio_perceptual_score"] = audio_review.score
        outcome["audio_perceptual_threshold"] = audio_review.threshold
        outcome["brand_perceptual_score"] = brand_review.score
        outcome["brand_perceptual_threshold"] = brand_review.threshold
        outcome["final_perceptual_domains"] = ("visual", "audio", "brand")
        outcome["final_perceptual_artifact_sha256"] = artifact_sha_raw
        return outcome


class ThreeDomainReferenceAwareProviderBackedDesktopVideoRuntime(
    ReferenceAwareProviderBackedDesktopVideoRuntime,
    _FinalDomainReviewConfig,
):
    """Verified-free reference-aware runtime with final three-domain admission."""

    def _generate_finished_product(
        self,
        *,
        run_root: Path,
        request_id: str,
        job_id: str,
        objective: str,
        duration_seconds: float,
    ) -> dict[str, object]:
        outcome = super()._generate_finished_product(
            run_root=run_root,
            request_id=request_id,
            job_id=job_id,
            objective=objective,
            duration_seconds=duration_seconds,
        )
        return self._apply_final_domain_reviews(
            outcome=outcome,
            objective=objective,
            request_id=request_id,
        )


class ThreeDomainManagedReferenceAwareProviderBackedDesktopVideoRuntime(
    ManagedReferenceAwareProviderBackedDesktopVideoRuntime,
    _FinalDomainReviewConfig,
):
    """Managed reference-aware runtime with final three-domain admission."""

    def _generate_finished_product(
        self,
        *,
        run_root: Path,
        request_id: str,
        job_id: str,
        objective: str,
        duration_seconds: float,
    ) -> dict[str, object]:
        outcome = super()._generate_finished_product(
            run_root=run_root,
            request_id=request_id,
            job_id=job_id,
            objective=objective,
            duration_seconds=duration_seconds,
        )
        return self._apply_final_domain_reviews(
            outcome=outcome,
            objective=objective,
            request_id=request_id,
        )


class ThreeDomainReceiptBoundNativeReferenceManagedDesktopVideoRuntime(
    ReceiptBoundNativeReferenceManagedDesktopVideoRuntime,
    _FinalDomainReviewConfig,
):
    """Receipt-bound native-reference runtime with final three-domain admission."""

    def _generate_finished_product(
        self,
        *,
        run_root: Path,
        request_id: str,
        job_id: str,
        objective: str,
        duration_seconds: float,
    ) -> dict[str, object]:
        outcome = super()._generate_finished_product(
            run_root=run_root,
            request_id=request_id,
            job_id=job_id,
            objective=objective,
            duration_seconds=duration_seconds,
        )
        return self._apply_final_domain_reviews(
            outcome=outcome,
            objective=objective,
            request_id=request_id,
        )


def _require_domain(review: PerceptualReviewSubmission, expected: QaDomain) -> None:
    if review.domain is not expected:
        raise VideoRuntimeError(
            f"final perceptual reviewer returned {review.domain.value} for {expected.value} domain"
        )
