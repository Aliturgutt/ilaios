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


class _Transport:
    def __init__(self, document: Mapping[str, object]) -> None:
        self.document = document
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
        return OpenRouterReviewResponse(
            200,
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(self.document, separators=(",", ":"))
                        }
                    }
                ]
            },
        )


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


def _reference(role: str, marker: bytes) -> ReferenceImageInput:
    return ReferenceImageInput(
        content=marker,
        mime_type="image/png",
        sha256_hex=sha256(marker).hexdigest(),
        role=role,
    )


def _patch_media(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(review_module, "_normalize_reference", lambda content: b"jpeg-ref")
    monkeypatch.setattr(
        review_module,
        "_sample_video_frames",
        lambda path, count: tuple(f"frame-{index}".encode() for index in range(count)),
    )


def _passing_product_document() -> dict[str, object]:
    return {
        "score": 0.91,
        "subject_score": None,
        "product_score": 0.90,
        "logo_score": None,
        "detail": "Visible product geometry remains consistent.",
        "repair_target": "preserve product geometry",
    }


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


def test_reference_consistency_requires_strong_threshold() -> None:
    with pytest.raises(ReferenceConsistencyReviewError, match="threshold must be >= 0.82"):
        OpenRouterReferenceConsistencyReviewer(
            "test-key",
            "openrouter/free",
            threshold=0.79,
        )


def test_product_and_logo_consistency_passes_only_when_each_critical_score_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_media(monkeypatch)
    transport = _Transport(
        {
            "score": 0.91,
            "subject_score": None,
            "product_score": 0.90,
            "logo_score": 0.88,
            "detail": "Visible product geometry and logo placement remain consistent.",
            "repair_target": "preserve product geometry and logo",
        }
    )
    reviewer = OpenRouterReferenceConsistencyReviewer(
        "test-key",
        "openrouter/free",
        transport=transport,
    )
    video = tmp_path / "result.mp4"
    video.write_bytes(b"video")

    result = reviewer.review(
        video_path=video,
        references=(
            _reference("product", b"product-reference"),
            _reference("logo", b"logo-reference"),
        ),
    )

    assert result.passed
    assert result.product_score == pytest.approx(0.90)
    assert result.logo_score == pytest.approx(0.88)
    assert result.subject_score is None
    assert len(result.frame_sha256s) == 4
    message = transport.calls[0]["messages"]
    prompt_text = str(message)
    assert "PRODUCT" in prompt_text
    assert "LOGO" in prompt_text
    assert "do not identify a real person" in prompt_text
    assert "biometric matching" in prompt_text


def test_low_critical_role_score_rejects_even_when_overall_score_is_high(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_media(monkeypatch)
    transport = _Transport(
        {
            "score": 0.95,
            "subject_score": None,
            "product_score": 0.79,
            "logo_score": None,
            "detail": "Overall scene matches but product shape drifted.",
            "repair_target": "restore exact visible product geometry",
        }
    )
    reviewer = OpenRouterReferenceConsistencyReviewer(
        "test-key",
        "openrouter/free",
        transport=transport,
    )
    video = tmp_path / "result.mp4"
    video.write_bytes(b"video")

    result = reviewer.review(
        video_path=video,
        references=(_reference("product", b"product-reference"),),
    )

    assert not result.passed
    assert result.score == pytest.approx(0.95)
    assert result.product_score == pytest.approx(0.79)


def test_subject_review_is_visual_consistency_not_identity_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_media(monkeypatch)
    transport = _Transport(
        {
            "score": 0.86,
            "subject_score": 0.85,
            "product_score": None,
            "logo_score": None,
            "detail": "Visible clothing, hair and silhouette remain consistent.",
            "repair_target": "preserve visible subject appearance",
        }
    )
    reviewer = OpenRouterReferenceConsistencyReviewer(
        "test-key",
        "openrouter/free",
        transport=transport,
    )
    video = tmp_path / "result.mp4"
    video.write_bytes(b"video")

    result = reviewer.review(
        video_path=video,
        references=(_reference("subject", b"subject-reference"),),
    )

    assert result.passed
    assert result.subject_score == pytest.approx(0.85)
    prompt_text = str(transport.calls[0]["messages"])
    assert "sensitive traits" in prompt_text
    assert "biometric" in prompt_text


def test_missing_applicable_critical_score_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_media(monkeypatch)
    transport = _Transport(
        {
            "score": 0.90,
            "subject_score": None,
            "product_score": None,
            "logo_score": None,
            "detail": "Ambiguous result.",
            "repair_target": "regenerate",
        }
    )
    reviewer = OpenRouterReferenceConsistencyReviewer(
        "test-key",
        "openrouter/free",
        transport=transport,
    )
    video = tmp_path / "result.mp4"
    video.write_bytes(b"video")

    with pytest.raises(ReferenceConsistencyReviewError, match="product consistency score is missing"):
        reviewer.review(
            video_path=video,
            references=(_reference("product", b"product-reference"),),
        )


def test_capability_404_retries_same_free_multimodal_review_without_response_format(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_media(monkeypatch)
    transport = _SequenceTransport(
        [
            _response(404),
            _response(200, _passing_product_document()),
        ]
    )
    reviewer = OpenRouterReferenceConsistencyReviewer(
        "test-key",
        "openrouter/free",
        transport=transport,
    )
    video = tmp_path / "result.mp4"
    video.write_bytes(b"video")

    result = reviewer.review(
        video_path=video,
        references=(_reference("product", b"product-reference"),),
    )

    assert result.passed
    assert len(transport.calls) == 2
    first, second = transport.calls
    assert first["model"] == second["model"] == "openrouter/free"
    assert first["messages"] == second["messages"]
    assert first["provider"] == second["provider"] == {"require_parameters": True}
    assert "response_format" in first
    assert "response_format" not in second


def test_persistent_capability_404_still_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_media(monkeypatch)
    transport = _SequenceTransport(
        [_response(404), _response(404), _response(404), _response(404)]
    )
    reviewer = OpenRouterReferenceConsistencyReviewer(
        "test-key",
        "openrouter/free",
        transport=transport,
    )
    video = tmp_path / "result.mp4"
    video.write_bytes(b"video")

    with pytest.raises(ReferenceConsistencyReviewError, match="failed with HTTP 404"):
        reviewer.review(
            video_path=video,
            references=(_reference("product", b"product-reference"),),
        )

    assert len(transport.calls) == 4
    assert transport.calls[0]["model"] == transport.calls[1]["model"] == "openrouter/free"
    assert transport.calls[2]["model"] == transport.calls[3]["model"] == "google/gemma-4-26b-a4b-it-20260403:free"
    assert "response_format" in transport.calls[0]
    assert "response_format" not in transport.calls[1]
    assert "response_format" in transport.calls[2]
    assert "response_format" not in transport.calls[3]
