from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

import src.video_automation.openrouter_perceptual_reviewer as reviewer_module
from src.video_automation.openrouter_perceptual_reviewer import (
    OpenRouterPerceptualReviewError,
    OpenRouterPerceptualReviewer,
    OpenRouterReviewResponse,
)
from src.video_automation.perceptual_review import PerceptualReviewSubmission


class _QueuedTransport:
    def __init__(self, responses: list[OpenRouterReviewResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[Mapping[str, object]] = []

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterReviewResponse:
        del url, headers, timeout_seconds
        self.requests.append(body)
        if not self._responses:
            raise AssertionError("unexpected OpenRouter review request")
        return self._responses.pop(0)


def _success_payload() -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"score":0.95,"detail":"frames match objective",'
                        '"repair_target":""}'
                    )
                }
            }
        ]
    }


def _review(
    transport: _QueuedTransport,
    monkeypatch: pytest.MonkeyPatch,
) -> PerceptualReviewSubmission:
    monkeypatch.setattr(
        reviewer_module,
        "_sample_frames",
        lambda path, count: (b"frame-one", b"frame-two"),
    )
    reviewer = OpenRouterPerceptualReviewer(
        "secret",
        "openrouter/free",
        sample_count=2,
        transport=transport,
    )
    return reviewer.review(
        video_path=Path("unused.mp4"),
        objective="Create a cinematic coastal city video.",
        artifact_sha256="a" * 64,
        producer_id="provider-video:seedance",
        review_id="review-missing-choices",
    )


def test_200_missing_choices_falls_back_to_prompt_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _QueuedTransport(
        [
            OpenRouterReviewResponse(200, {"error": {"message": "route unavailable"}}),
            OpenRouterReviewResponse(200, _success_payload()),
        ]
    )

    submission = _review(transport, monkeypatch)

    assert len(transport.requests) == 2
    assert "response_format" in transport.requests[0]
    assert "response_format" not in transport.requests[1]
    assert "route=prompt-json-fallback" in submission.provenance_reference
    assert submission.score == pytest.approx(0.95)


def test_fallback_missing_choices_gets_one_bounded_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _QueuedTransport(
        [
            OpenRouterReviewResponse(404, {"error": {"message": "no strict route"}}),
            OpenRouterReviewResponse(200, {"choices": []}),
            OpenRouterReviewResponse(200, _success_payload()),
        ]
    )

    submission = _review(transport, monkeypatch)

    assert len(transport.requests) == 3
    assert "response_format" in transport.requests[0]
    assert "response_format" not in transport.requests[1]
    assert "response_format" not in transport.requests[2]
    assert "route=prompt-json-fallback-retry" in submission.provenance_reference


def test_missing_choices_persists_after_bounded_retry_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _QueuedTransport(
        [
            OpenRouterReviewResponse(404, {"error": {"message": "no strict route"}}),
            OpenRouterReviewResponse(200, {"choices": []}),
            OpenRouterReviewResponse(200, {"error": {"message": "still unavailable"}}),
        ]
    )

    with pytest.raises(OpenRouterPerceptualReviewError, match="missing choices"):
        _review(transport, monkeypatch)

    assert len(transport.requests) == 3
