from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path

import pytest

import src.video_automation.reference_consistency_review as review_module
from services.integrations.native_reference_receipt_runtime import _reference_bindings
from src.video_automation.openrouter_perceptual_reviewer import OpenRouterReviewResponse
from src.video_automation.reference_consistency_review import (
    OpenRouterReferenceConsistencyReviewer,
    ReferenceConsistencyReview,
)
from src.video_automation.reference_image_analysis import ReferenceImageInput


class _Transport:
    def __init__(self) -> None:
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
        document = {
            "score": 0.93,
            "subject_score": None,
            "product_score": None,
            "logo_score": None,
            "detail": "Both exact boundary frames preserve the requested composition.",
            "repair_target": "preserve exact opening and closing composition",
        }
        return OpenRouterReviewResponse(
            200,
            {"choices": [{"message": {"content": json.dumps(document)}}]},
        )


def _reference(role: str, marker: bytes) -> ReferenceImageInput:
    return ReferenceImageInput(
        content=marker,
        mime_type="image/png",
        sha256_hex=sha256(marker).hexdigest(),
        role=role,
    )


def test_issue330_uses_one_review_call_and_binds_exact_boundary_frames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(review_module, "_normalize_reference", lambda content: b"jpeg-ref")
    monkeypatch.setattr(
        review_module,
        "_sample_video_frames",
        lambda path, count: tuple(f"interior-{index}".encode() for index in range(count)),
    )
    monkeypatch.setattr(
        review_module,
        "_sample_boundary_frames",
        lambda path, references: (
            ("first_frame", b"exact-first"),
            ("last_frame", b"exact-last"),
        ),
    )
    transport = _Transport()
    reviewer = OpenRouterReferenceConsistencyReviewer(
        "test-key",
        "openrouter/free",
        transport=transport,
    )
    video = tmp_path / "result.mp4"
    video.write_bytes(b"video")
    first = _reference("first_frame", b"first-reference")
    last = _reference("last_frame", b"last-reference")

    result = reviewer.review(video_path=video, references=(first, last))

    assert result.passed
    assert len(transport.calls) == 1
    assert result.criteria_version == "ilaios.video.reference-consistency.v3"
    assert result.reference_roles == ("first_frame", "last_frame")
    assert result.reference_sha256s == (first.sha256_hex, last.sha256_hex)
    assert result.first_frame_sha256 == sha256(b"exact-first").hexdigest()
    assert result.last_frame_sha256 == sha256(b"exact-last").hexdigest()
    prompt = str(transport.calls[0]["messages"])
    assert "CRITERIA_VERSION=ilaios.video.reference-consistency.v3" in prompt
    assert "REFERENCE 1; ROLE=first_frame" in prompt
    assert "REFERENCE 2; ROLE=last_frame" in prompt
    assert "EXACT BOUNDARY FRAME; ROLE=first_frame" in prompt
    assert "EXACT BOUNDARY FRAME; ROLE=last_frame" in prompt


def test_issue330_reference_binding_is_explicitly_ordered_by_role_and_sha() -> None:
    review = ReferenceConsistencyReview(
        reviewer_id="reviewer",
        criteria_version="ilaios.video.reference-consistency.v3",
        score=0.9,
        threshold=0.82,
        subject_score=None,
        product_score=None,
        logo_score=None,
        detail="ok",
        repair_target="preserve boundaries",
        reference_sha256s=("1" * 64, "2" * 64),
        reference_roles=("first_frame", "last_frame"),
        frame_sha256s=("3" * 64,),
        first_frame_sha256="4" * 64,
        last_frame_sha256="5" * 64,
    )

    assert _reference_bindings(review) == [
        {"order": 1, "role": "first_frame", "sha256": "1" * 64},
        {"order": 2, "role": "last_frame", "sha256": "2" * 64},
    ]
