from __future__ import annotations

import pytest

from src.image_automation.factory import (
    GovernedImageFactory,
    ImageBackendArtifact,
    ImageCandidate,
    ImageCandidateKind,
    ImageExecutionError,
    ImageGenerationRequest,
    ImageOutputFormat,
    ImageQualityEvaluation,
    ImageRoutingPlan,
)
from src.image_automation.model_candidates import (
    FLUX1_SOURCE_REVISION,
    QWEN_IMAGE_SOURCE_REVISION,
    flux1_schnell_candidate,
    qwen_image_candidate,
)
from src.media_model_governance import ModelEligibility


class _Executor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate(
        self,
        *,
        request: ImageGenerationRequest,
        candidate: ImageCandidate,
    ) -> ImageBackendArtifact:
        self.calls.append(candidate.candidate_id)
        return ImageBackendArtifact(
            body=f"image:{candidate.candidate_id}".encode(),
            width=request.width,
            height=request.height,
            mime_type=request.output_format.mime_type,
            execution_evidence_ref=f"evidence://image/{candidate.candidate_id}",
            model_evidence_ref=f"evidence://model/{candidate.model_id}",
            provenance_ref=f"evidence://provenance/{candidate.candidate_id}",
        )


class _Evaluator:
    def __init__(self, scores: dict[bytes, float]) -> None:
        self._scores = scores

    def evaluate(
        self,
        *,
        request: ImageGenerationRequest,
        candidate: ImageCandidate,
        artifact: ImageBackendArtifact,
    ) -> ImageQualityEvaluation:
        score = self._scores.get(artifact.body, 0.2)
        passed = score >= request.quality_floor
        return ImageQualityEvaluation(
            score=score,
            passed=passed,
            evidence_ref=f"evidence://quality/{candidate.candidate_id}/{score}",
            repair_targets=() if passed else ("prompt_alignment",),
        )


class _Repairer:
    def __init__(self) -> None:
        self.calls = 0

    def repair(
        self,
        *,
        request: ImageGenerationRequest,
        candidate: ImageCandidate,
        artifact: ImageBackendArtifact,
        repair_targets: tuple[str, ...],
        attempt: int,
    ) -> ImageBackendArtifact:
        del artifact, repair_targets
        self.calls += 1
        return ImageBackendArtifact(
            body=f"repaired:{candidate.candidate_id}".encode(),
            width=request.width,
            height=request.height,
            mime_type=request.output_format.mime_type,
            execution_evidence_ref=f"evidence://repair/{candidate.candidate_id}/{attempt}",
            model_evidence_ref=f"evidence://model/{candidate.model_id}",
            provenance_ref=f"evidence://provenance/{candidate.candidate_id}/repair/{attempt}",
        )


def _request() -> ImageGenerationRequest:
    return ImageGenerationRequest(
        tenant_id="tenant-001",
        user_id="user-001",
        request_id="image-request-001",
        routing_decision_id="route-image-001",
        prompt="A clean product hero image",
        width=1024,
        height=1024,
        output_format=ImageOutputFormat.PNG,
        style="minimal premium product photography",
        quality_floor=0.8,
        brand_constraints=("preserve supplied logo geometry",),
    )


def _native() -> ImageCandidate:
    return ImageCandidate(
        candidate_id="native-001",
        kind=ImageCandidateKind.NATIVE,
        model_id="black-forest-labs/FLUX.1-schnell",
        provider_name="native_image",
    )


def _managed() -> ImageCandidate:
    return ImageCandidate(
        candidate_id="managed-001",
        kind=ImageCandidateKind.MANAGED,
        model_id="managed/image-premium",
        provider_name="managed-image-provider",
    )


def test_routing_plan_must_match_canonical_decision() -> None:
    factory = GovernedImageFactory(
        executor=_Executor(), evaluator=_Evaluator({}), repairer=_Repairer()
    )

    with pytest.raises(ImageExecutionError, match="canonical routing decision"):
        factory.execute(
            request=_request(),
            routing_plan=ImageRoutingPlan("different-route", (_native(),)),
        )


def test_selective_native_repair_can_avoid_managed_fallback() -> None:
    executor = _Executor()
    repairer = _Repairer()
    evaluator = _Evaluator(
        {
            b"image:native-001": 0.5,
            b"repaired:native-001": 0.95,
        }
    )
    result = GovernedImageFactory(
        executor=executor,
        evaluator=evaluator,
        repairer=repairer,
        max_repair_attempts=1,
    ).execute(
        request=_request(),
        routing_plan=ImageRoutingPlan("route-image-001", (_native(), _managed())),
    )

    assert result.candidate_id == "native-001"
    assert result.repair_attempts == 1
    assert executor.calls == ["native-001"]
    assert repairer.calls == 1
    assert len(result.sha256_hex) == 64
    assert result.width == 1024
    assert result.mime_type == "image/png"


def test_managed_fallback_occurs_only_in_canonical_candidate_order() -> None:
    executor = _Executor()
    result = GovernedImageFactory(
        executor=executor,
        evaluator=_Evaluator(
            {
                b"image:native-001": 0.1,
                b"repaired:native-001": 0.2,
                b"image:managed-001": 0.9,
            }
        ),
        repairer=_Repairer(),
        max_repair_attempts=1,
    ).execute(
        request=_request(),
        routing_plan=ImageRoutingPlan("route-image-001", (_native(), _managed())),
    )

    assert result.candidate_id == "managed-001"
    assert executor.calls == ["native-001", "managed-001"]


def test_open_weight_candidates_remain_review_required_with_exact_source_provenance() -> None:
    flux = flux1_schnell_candidate()
    qwen = qwen_image_candidate()

    assert flux.eligibility is ModelEligibility.REVIEW_REQUIRED
    assert qwen.eligibility is ModelEligibility.REVIEW_REQUIRED
    assert flux.source_revision == FLUX1_SOURCE_REVISION
    assert qwen.source_revision == QWEN_IMAGE_SOURCE_REVISION
    assert flux.official_source == "https://github.com/black-forest-labs/flux"
    assert qwen.official_source == "https://github.com/QwenLM/Qwen-Image"
    assert flux.checkpoint_digest_sha256 is None
    assert qwen.checkpoint_digest_sha256 is None


def test_wrong_dimensions_are_never_accepted_without_repair() -> None:
    class _WrongExecutor(_Executor):
        def generate(
            self,
            *,
            request: ImageGenerationRequest,
            candidate: ImageCandidate,
        ) -> ImageBackendArtifact:
            return ImageBackendArtifact(
                body=b"wrong-size",
                width=512,
                height=512,
                mime_type="image/png",
                execution_evidence_ref="evidence://image/wrong",
                model_evidence_ref="evidence://model/wrong",
                provenance_ref="evidence://provenance/wrong",
            )

    with pytest.raises(ImageExecutionError, match="acceptance floor"):
        GovernedImageFactory(
            executor=_WrongExecutor(),
            evaluator=_Evaluator({b"wrong-size": 1.0}),
            repairer=_Repairer(),
            max_repair_attempts=0,
        ).execute(
            request=_request(),
            routing_plan=ImageRoutingPlan("route-image-001", (_native(),)),
        )
