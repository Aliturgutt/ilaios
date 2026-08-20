from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.desktop.e2e import provider_video_native_reference_finished_product_e2e as certification  # noqa: E402
from src.video_automation.openrouter_perceptual_reviewer import OpenRouterPerceptualReviewer  # noqa: E402
from src.video_automation.perceptual_review import PerceptualReviewSubmission  # noqa: E402

_ORIGINAL_REVIEW = OpenRouterPerceptualReviewer.review
_semantic_reviews: list[PerceptualReviewSubmission] = []


def _recording_review(
    self: OpenRouterPerceptualReviewer,
    *,
    video_path: Path,
    objective: str,
    artifact_sha256: str,
    producer_id: str,
    review_id: str,
) -> PerceptualReviewSubmission:
    review = _ORIGINAL_REVIEW(
        self,
        video_path=video_path,
        objective=objective,
        artifact_sha256=artifact_sha256,
        producer_id=producer_id,
        review_id=review_id,
    )
    _semantic_reviews.append(review)
    return review


def semantic_review_evidence(review: PerceptualReviewSubmission) -> dict[str, object]:
    """Return bounded, non-secret semantic-review evidence safe for CI artifacts."""
    return {
        "review_id": review.review_id,
        "reviewer_id": review.reviewer_id,
        "score": review.score,
        "threshold": review.threshold,
        "passed": review.passed,
        "repair_target": review.repair_target,
        "criteria_id": review.criteria_id,
        "criteria_version": review.criteria_version,
        "criteria_sha256": review.criteria_sha256,
        "provenance_reference": review.provenance_reference,
    }


def _select_failure_review(
    reviews: list[PerceptualReviewSubmission],
) -> PerceptualReviewSubmission | None:
    failed = [review for review in reviews if not review.passed]
    if failed:
        return failed[-1]
    if reviews:
        return reviews[-1]
    return None


def _semantic_review_stage(review: PerceptualReviewSubmission) -> str:
    return "final" if review.review_id.endswith("-final") else "generated-shot"


def _augment_failure_artifact(reviews: list[PerceptualReviewSubmission]) -> None:
    review = _select_failure_review(reviews)
    if review is None:
        return
    proof_root = Path(
        os.environ.get(
            "VIDEO_DESKTOP_NATIVE_REFERENCE_PROOF_DIR",
            "artifacts/video-desktop-native-reference-proof",
        )
    ).resolve()
    failure_path = proof_root / "failure.json"
    if not failure_path.is_file():
        return
    document = json.loads(failure_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        return
    evidence = semantic_review_evidence(review)
    document["semantic_review_stage"] = _semantic_review_stage(review)
    document["semantic_review"] = evidence
    document["semantic_reviews"] = [
        semantic_review_evidence(item) for item in reviews if not item.passed
    ]
    failure_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "VIDEO_NATIVE_REFERENCE_SEMANTIC_REVIEW="
        + json.dumps(evidence, sort_keys=True, separators=(",", ":")),
        flush=True,
    )


def main() -> int:
    _semantic_reviews.clear()
    setattr(OpenRouterPerceptualReviewer, "review", _recording_review)
    try:
        return certification.main()
    except BaseException:
        _augment_failure_artifact(_semantic_reviews)
        raise
    finally:
        setattr(OpenRouterPerceptualReviewer, "review", _ORIGINAL_REVIEW)


if __name__ == "__main__":
    raise SystemExit(main())
