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


_SOURCE_MODEL = "google/gemma-3-27b-it:free"
_FALLBACK_MODEL = "google/gemma-4-26b-a4b-it-20260403:free"


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
                        '{"score":0.91,"detail":"The sampled frames match the objective.",'
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
        _SOURCE_MODEL,
        sample_count=2,
        transport=transport,
    )
    return reviewer.review(
        video_path=Path("unused.mp4"),
        objective="Create a cinematic coastal city video.",
        artifact_sha256="a" * 64,
        producer_id="provider-video:seedance",
        review_id="review-free-vision-fallback",
    )


def _capability_failure(status_code: int = 404) -> OpenRouterReviewResponse:
    return OpenRouterReviewResponse(
        status_code,
        {"error": {"code": status_code, "message": "No route available"}},
    )


def test_explicit_free_semantic_model_404_uses_bounded_free_vision_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _QueuedTransport(
        [
            _capability_failure(),
            _capability_failure(),
            OpenRouterReviewResponse(200, _success_payload()),
        ]
    )

    submission = _review(transport, monkeypatch)

    assert submission.score == pytest.approx(0.91)
    assert submission.threshold == pytest.approx(0.78)
    assert submission.reviewer_id == f"openrouter-semantic-review:{_FALLBACK_MODEL}"
    assert f"model={_FALLBACK_MODEL}" in submission.provenance_reference
    assert "route=free-vision-json-schema-fallback" in submission.provenance_reference
    assert len(transport.requests) == 3
    assert transport.requests[0]["model"] == _SOURCE_MODEL
    assert transport.requests[1]["model"] == _SOURCE_MODEL
    assert transport.requests[2]["model"] == _FALLBACK_MODEL
    assert "response_format" in transport.requests[0]
    assert "response_format" not in transport.requests[1]
    assert "response_format" in transport.requests[2]
    assert transport.requests[0]["messages"] == transport.requests[2]["messages"]
    assert transport.requests[0]["provider"] == transport.requests[2]["provider"] == {
        "require_parameters": True
    }


def test_persistent_semantic_capability_404_still_fails_closed_after_free_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _QueuedTransport(
        [
            _capability_failure(),
            _capability_failure(),
            _capability_failure(),
            _capability_failure(),
        ]
    )

    with pytest.raises(OpenRouterPerceptualReviewError, match="failed with HTTP 404"):
        _review(transport, monkeypatch)

    assert len(transport.requests) == 4
    assert [request["model"] for request in transport.requests] == [
        _SOURCE_MODEL,
        _SOURCE_MODEL,
        _FALLBACK_MODEL,
        _FALLBACK_MODEL,
    ]
    assert "response_format" in transport.requests[0]
    assert "response_format" not in transport.requests[1]
    assert "response_format" in transport.requests[2]
    assert "response_format" not in transport.requests[3]
