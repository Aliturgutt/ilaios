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
_final_review: PerceptualReviewSubmission | None = None


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
    if review_id.endswith("-final"):
        global _final_review
        _final_review = review
    return review


def semantic_review_evidence(review: PerceptualReviewSubmission) -> dict[str, object]:
    """Return the bounded, non-secret final-review evidence safe for CI artifacts."""
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


def _augment_failure_artifact(review: PerceptualReviewSubmission) -> None:
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
    document["semantic_review"] = evidence
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
    global _final_review
    _final_review = None
    setattr(OpenRouterPerceptualReviewer, "review", _recording_review)
    try:
        return certification.main()
    except BaseException:
        if _final_review is not None:
            _augment_failure_artifact(_final_review)
        raise
    finally:
        setattr(OpenRouterPerceptualReviewer, "review", _ORIGINAL_REVIEW)


if __name__ == "__main__":
    raise SystemExit(main())
