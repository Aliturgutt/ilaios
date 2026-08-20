from __future__ import annotations

from apps.desktop.e2e.provider_video_native_reference_semantic_diagnostic_e2e import (
    semantic_review_evidence,
)
from src.video_automation.perceptual_review import (
    PerceptualReviewSubmission,
    PerceptualReviewerKind,
)
from src.video_automation.video_skills import QaDomain


def test_semantic_review_evidence_preserves_fail_closed_rejection_details() -> None:
    review = PerceptualReviewSubmission(
        review_id="native-reference-final",
        domain=QaDomain.VISUAL,
        artifact_sha256="a" * 64,
        reviewer_id="openrouter-semantic-review:test-model",
        producer_id="ilaios-provider-video-factory",
        reviewer_kind=PerceptualReviewerKind.INDEPENDENT_MODEL,
        criteria_id="ilaios.video.semantic-prompt-alignment",
        criteria_version="1.0.0",
        criteria_sha256="b" * 64,
        score=0.62,
        threshold=0.78,
        evidence_references=("frame-sha256:" + "c" * 64,),
        provenance_reference="openrouter-review:model=test-model:artifact=" + "a" * 64,
        repair_target="preserve-product-identity",
    )

    evidence = semantic_review_evidence(review)

    assert evidence == {
        "review_id": "native-reference-final",
        "reviewer_id": "openrouter-semantic-review:test-model",
        "score": 0.62,
        "threshold": 0.78,
        "passed": False,
        "repair_target": "preserve-product-identity",
        "criteria_id": "ilaios.video.semantic-prompt-alignment",
        "criteria_version": "1.0.0",
        "criteria_sha256": "b" * 64,
        "provenance_reference": "openrouter-review:model=test-model:artifact=" + "a" * 64,
    }
