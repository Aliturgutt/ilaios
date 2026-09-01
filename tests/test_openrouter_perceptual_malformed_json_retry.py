from __future__ import annotations

import json
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


class _SequenceTransport:
    def __init__(self, responses: list[OpenRouterReviewResponse]) -> None:
        self._responses = responses
        self.calls: list[Mapping[str, object]] = []

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterReviewResponse:
        assert url.endswith("/chat/completions")
        assert headers["Authorization"] == "Bearer test-key"
        assert timeout_seconds > 0
        self.calls.append(body)
        return self._responses.pop(0)


def _payload(content: str) -> dict[str, object]:
    return {"choices": [{"message": {"content": content}}]}


def _valid_payload() -> dict[str, object]:
    return _payload(
        json.dumps(
            {
                "score": 0.93,
                "detail": "The sampled frames match the objective.",
                "repair_target": "",
            },
            separators=(",", ":"),
        )
    )


def _reviewer(transport: _SequenceTransport) -> OpenRouterPerceptualReviewer:
    return OpenRouterPerceptualReviewer(
        "test-key",
        "openrouter/free",
        sample_count=2,
        transport=transport,
    )


def _patch_frames(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reviewer_module, "_sample_frames", lambda path, count: (b"a", b"b"))


def _review(
    reviewer: OpenRouterPerceptualReviewer, tmp_path: Path
) -> PerceptualReviewSubmission:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    return reviewer.review(
        video_path=video,
        objective="Show the requested product in the requested scene.",
        artifact_sha256="a" * 64,
        producer_id="managed-provider:video",
        review_id="review-1",
    )


def test_prompt_json_fallback_retries_identical_request_once_after_malformed_2xx(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_frames(monkeypatch)
    transport = _SequenceTransport(
        [
            OpenRouterReviewResponse(503, {}),
            OpenRouterReviewResponse(200, _payload("not-json")),
            OpenRouterReviewResponse(200, _valid_payload()),
        ]
    )

    result = _review(_reviewer(transport), tmp_path)

    assert result.score == 0.93
    assert "route=prompt-json-fallback-retry" in result.provenance_reference
    assert len(transport.calls) == 3
    assert "response_format" in transport.calls[0]
    assert "response_format" not in transport.calls[1]
    assert transport.calls[1] == transport.calls[2]


def test_prompt_json_fallback_persistent_malformed_2xx_still_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_frames(monkeypatch)
    transport = _SequenceTransport(
        [
            OpenRouterReviewResponse(503, {}),
            OpenRouterReviewResponse(200, _payload("not-json")),
            OpenRouterReviewResponse(200, _payload("still-not-json")),
        ]
    )

    with pytest.raises(OpenRouterPerceptualReviewError, match="review content is not valid JSON"):
        _review(_reviewer(transport), tmp_path)

    assert len(transport.calls) == 3
    assert transport.calls[1] == transport.calls[2]
