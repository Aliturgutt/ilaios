from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path

import pytest

import src.video_automation.reference_consistency_review as review_module
from src.video_automation.openrouter_perceptual_reviewer import OpenRouterReviewResponse
from src.video_automation.reference_consistency_review import (
    OpenRouterReferenceConsistencyReviewer,
    ReferenceConsistencyReviewError,
)
from src.video_automation.reference_image_analysis import ReferenceImageInput


class _SequenceTransport:
    def __init__(self, responses: list[OpenRouterReviewResponse]) -> None:
        self.responses = responses
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
        return self.responses.pop(0)


def _reference() -> ReferenceImageInput:
    marker = b"product-reference"
    return ReferenceImageInput(
        content=marker,
        mime_type="image/png",
        sha256_hex=sha256(marker).hexdigest(),
        role="product",
    )


def _patch_media(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(review_module, "_normalize_reference", lambda content: b"jpeg-ref")
    monkeypatch.setattr(
        review_module,
        "_sample_video_frames",
        lambda path, count: tuple(f"frame-{index}".encode() for index in range(count)),
    )


def _response(status_code: int, document: Mapping[str, object] | None = None) -> OpenRouterReviewResponse:
    payload: dict[str, object] = {}
    if document is not None:
        payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(document, separators=(",", ":"))
                    }
                }
            ]
        }
    return OpenRouterReviewResponse(status_code, payload)


def _passing_product_document() -> dict[str, object]:
    return {
        "score": 0.91,
        "subject_score": None,
        "product_score": 0.90,
        "logo_score": None,
        "detail": "Visible product geometry remains consistent.",
        "repair_target": "preserve product geometry",
    }


def test_reference_consistency_retries_one_429_with_identical_strict_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_media(monkeypatch)
    transport = _SequenceTransport(
        [_response(429), _response(200, _passing_product_document())]
    )
    reviewer = OpenRouterReferenceConsistencyReviewer(
        "test-key",
        "openrouter/free",
        transport=transport,
    )
    video = tmp_path / "result.mp4"
    video.write_bytes(b"video")

    result = reviewer.review(video_path=video, references=(_reference(),))

    assert result.passed
    assert len(transport.calls) == 2
    assert transport.calls[0] == transport.calls[1]
    assert transport.calls[0]["model"] == "openrouter/free"
    assert "response_format" in transport.calls[0]


def test_reference_consistency_persistent_429_fails_closed_after_one_outer_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_media(monkeypatch)
    transport = _SequenceTransport([_response(429), _response(429)])
    reviewer = OpenRouterReferenceConsistencyReviewer(
        "test-key",
        "openrouter/free",
        transport=transport,
    )
    video = tmp_path / "result.mp4"
    video.write_bytes(b"video")

    with pytest.raises(ReferenceConsistencyReviewError, match="failed with HTTP 429"):
        reviewer.review(video_path=video, references=(_reference(),))

    assert len(transport.calls) == 2
    assert transport.calls[0] == transport.calls[1]
