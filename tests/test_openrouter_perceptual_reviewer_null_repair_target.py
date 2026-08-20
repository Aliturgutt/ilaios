from __future__ import annotations

import pytest

from src.video_automation.openrouter_perceptual_reviewer import (
    OpenRouterPerceptualReviewError,
    _extract_review,
)


def _payload(*, score: float, repair_target: object) -> dict[str, object]:
    import json

    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "score": score,
                            "detail": "The sampled frames match the requested scene.",
                            "repair_target": repair_target,
                        },
                        separators=(",", ":"),
                    )
                }
            }
        ]
    }


def test_extract_review_normalizes_null_repair_target_to_empty_string() -> None:
    review = _extract_review(_payload(score=0.91, repair_target=None))

    assert review["score"] == pytest.approx(0.91)
    assert review["repair_target"] == ""


def test_extract_review_rejects_non_string_non_null_repair_target() -> None:
    with pytest.raises(OpenRouterPerceptualReviewError, match="repair_target is invalid"):
        _extract_review(_payload(score=0.91, repair_target={"target": "regenerate"}))
