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


class _SequenceTransport:
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
        assert url.endswith("/chat/completions")
        assert headers["Authorization"] == "Bearer secret"
        assert timeout_seconds > 0
        self.requests.append(body)
        if not self._responses:
            raise AssertionError("unexpected OpenRouter review request")
        return self._responses.pop(0)


def _not_found() -> OpenRouterReviewResponse:
    return OpenRouterReviewResponse(
        404,
        {"error": {"code": 404, "message": "No endpoints found"}},
    )


def _success() -> OpenRouterReviewResponse:
    return OpenRouterReviewResponse(
        200,
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"score":0.91,"detail":"The generated frames match the requested '
                            'scene.","repair_target":""}'
                        )
                    }
                }
            ]
        },
    )


def _review(
    monkeypatch: pytest.MonkeyPatch,
    transport: _SequenceTransport,
):
    monkeypatch.setattr(
        reviewer_module,
        "_sample_frames",
        lambda path, count: (b"frame-one", b"frame-two"),
    )
    reviewer = OpenRouterPerceptualReviewer(
        "secret",
        "google/gemma-3-27b-it:free",
        sample_count=2,
        transport=transport,
    )
    return reviewer.review(
        video_path=Path("unused.mp4"),
        objective="Create a cinematic coastal city video.",
        artifact_sha256="a" * 64,
        producer_id="provider-video:seedance",
        review_id="review-live-404",
    )


def test_persistent_configured_free_model_404_uses_explicit_free_vision_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _SequenceTransport([_not_found(), _not_found(), _success()])

    submission = _review(monkeypatch, transport)

    assert len(transport.requests) == 3
    assert transport.requests[0]["model"] == "google/gemma-3-27b-it:free"
    assert transport.requests[1]["model"] == "google/gemma-3-27b-it:free"
    assert transport.requests[2]["model"] == "google/gemma-4-26b-a4b-it-20260403:free"
    assert "response_format" in transport.requests[0]
    assert "response_format" not in transport.requests[1]
    assert "response_format" in transport.requests[2]
    assert submission.score == pytest.approx(0.91)
    assert submission.threshold == pytest.approx(0.78)
    assert submission.reviewer_id.endswith("google/gemma-4-26b-a4b-it-20260403:free")
    assert "model=google/gemma-4-26b-a4b-it-20260403:free" in submission.provenance_reference
    assert "route=free-vision-json-schema-fallback" in submission.provenance_reference


def test_persistent_free_vision_404_still_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _SequenceTransport(
        [_not_found(), _not_found(), _not_found(), _not_found()]
    )

    with pytest.raises(OpenRouterPerceptualReviewError, match="HTTP 404"):
        _review(monkeypatch, transport)

    assert len(transport.requests) == 4
    assert transport.requests[2]["model"] == "google/gemma-4-26b-a4b-it-20260403:free"
    assert transport.requests[3]["model"] == "google/gemma-4-26b-a4b-it-20260403:free"
    assert "response_format" in transport.requests[2]
    assert "response_format" not in transport.requests[3]
