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
    ReferenceConsistencyReview,
)
from src.video_automation.reference_image_analysis import ReferenceImageInput


class _SequenceTransport:
    def __init__(self, responses: list[OpenRouterReviewResponse]) -> None:
        self.responses = list(responses)
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
        if not self.responses:
            raise AssertionError("unexpected review request")
        return self.responses.pop(0)


def _reference() -> ReferenceImageInput:
    content = b"product-reference"
    return ReferenceImageInput(
        content=content,
        mime_type="image/png",
        sha256_hex=sha256(content).hexdigest(),
        role="product",
    )


def _patch_media(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(review_module, "_normalize_reference", lambda content: b"jpeg-ref")
    monkeypatch.setattr(
        review_module,
        "_sample_video_frames",
        lambda path, count: tuple(f"frame-{index}".encode() for index in range(count)),
    )


def _success() -> OpenRouterReviewResponse:
    document = {
        "score": 0.92,
        "subject_score": None,
        "product_score": 0.91,
        "logo_score": None,
        "detail": "Visible product geometry remains consistent.",
        "repair_target": "preserve product geometry",
    }
    return OpenRouterReviewResponse(
        200,
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(document, separators=(",", ":"))
                    }
                }
            ]
        },
    )


def _not_found() -> OpenRouterReviewResponse:
    return OpenRouterReviewResponse(
        404,
        {"error": {"code": 404, "message": "No endpoints found"}},
    )


def _review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    transport: _SequenceTransport,
) -> ReferenceConsistencyReview:
    _patch_media(monkeypatch)
    video = tmp_path / "result.mp4"
    video.write_bytes(b"video")
    reviewer = OpenRouterReferenceConsistencyReviewer(
        "test-key",
        "openrouter/free",
        transport=transport,
    )
    return reviewer.review(video_path=video, references=(_reference(),))


def test_persistent_free_router_404_uses_explicit_free_vision_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = _SequenceTransport([_not_found(), _not_found(), _success()])

    result = _review(tmp_path, monkeypatch, transport)

    assert result.passed
    assert len(transport.calls) == 3
    assert transport.calls[0]["model"] == "openrouter/free"
    assert transport.calls[1]["model"] == "openrouter/free"
    assert transport.calls[2]["model"] == "google/gemma-4-26b-a4b-it-20260403:free"
    assert "response_format" in transport.calls[0]
    assert "response_format" not in transport.calls[1]
    assert "response_format" in transport.calls[2]
    assert result.reviewer_id.endswith("google/gemma-4-26b-a4b-it-20260403:free")


def test_explicit_free_vision_model_also_has_prompt_json_capability_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = _SequenceTransport([_not_found(), _not_found(), _not_found(), _success()])

    result = _review(tmp_path, monkeypatch, transport)

    assert result.passed
    assert len(transport.calls) == 4
    assert transport.calls[3]["model"] == "google/gemma-4-26b-a4b-it-20260403:free"
    assert "response_format" not in transport.calls[3]
    assert transport.calls[3]["provider"] == {"require_parameters": True}
