from __future__ import annotations

import pytest

from src.image_automation.factory import (
    GovernedImageFactory,
    ImageBackendArtifact,
    ImageCandidate,
    ImageCandidateKind,
    ImageExecutionError,
    ImageGenerationRequest,
    ImageQualityEvaluation,
    ImageRoutingPlan,
)
from src.image_automation.model_candidates import (
    FLUX1_SCHNELL_PUBLISHED_SHA256,
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
            execution_evidence_ref=f"evidence://image/{candidate.candidate_id}",
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
        passed = score >= 0.8
        return ImageQualityEvaluation(
            score=score,
            threshold=0.8,
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
        self.calls += 1
        return ImageBackendArtifact(
            body=f"repaired:{candidate.candidate_id}".encode(),
            execution_evidence_ref=f"evidence://repair/{candidate.candidate_id}/{attempt}",
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
    )


def _native() -> ImageCandidate:
    return ImageCandidate(
        candidate_id="native-001",
        kind=ImageCandidateKind.NATIVE,
        model_id="black-forest-labs/FLUX.1-schnell",
        provider_name="ilaios-native",
    )


def _managed() -> ImageCandidate:
    return ImageCandidate(
        candidate_id="managed-001",
        kind=ImageCandidateKind.MANAGED,
        model_id="managed/image-premium",
        provider_name="managed-provider",
        credit_authorization_id="credit-auth-001",
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


def test_managed_candidate_requires_prior_credit_authorization() -> None:
    with pytest.raises(ImageExecutionError, match="credit authorization"):
        ImageCandidate(
            candidate_id="managed-001",
            kind=ImageCandidateKind.MANAGED,
            model_id="managed/image-premium",
            provider_name="managed-provider",
        )


def test_selective_native_repair_can_avoid_paid_fallback() -> None:
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


def test_open_weight_candidates_are_not_prematurely_approved_native() -> None:
    flux = flux1_schnell_candidate()
    qwen = qwen_image_candidate()
    assert flux.eligibility is ModelEligibility.REVIEW_REQUIRED
    assert qwen.eligibility is ModelEligibility.REVIEW_REQUIRED
    assert flux.checkpoint_digest_sha256 == FLUX1_SCHNELL_PUBLISHED_SHA256
