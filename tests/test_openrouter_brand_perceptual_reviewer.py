from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

import src.video_automation.openrouter_brand_perceptual_reviewer as brand_module
from src.video_automation.openrouter_brand_perceptual_reviewer import (
    OpenRouterBrandPerceptualReviewer,
)
from src.video_automation.openrouter_perceptual_reviewer import (
    OpenRouterPerceptualReviewError,
    OpenRouterReviewResponse,
)
from src.video_automation.video_skills import QaDomain


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
            raise AssertionError("unexpected brand review request")
        return self._responses.pop(0)


def _payload(score: float, repair_target: str = "") -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"score":'
                        f"{score}"
                        ',"detail":"brand evidence",'
                        f'"repair_target":"{repair_target}"'
                        "}"
                    )
                }
            }
        ]
    }


def _review(
    monkeypatch: pytest.MonkeyPatch,
    transport: _QueuedTransport,
):
    monkeypatch.setattr(
        brand_module,
        "_sample_frames",
        lambda path, count: (b"brand-frame-one", b"brand-frame-two"),
    )
    reviewer = OpenRouterBrandPerceptualReviewer(
        "secret",
        "openrouter/free",
        sample_count=2,
        transport=transport,
    )
    return reviewer.review(
        video_path=Path("unused.mp4"),
        objective="Create an ILAIOS documentary with no provider watermarks.",
        artifact_sha256="a" * 64,
        producer_id="ilaios-provider-video-factory",
        review_id="brand-review-001",
    )


def test_brand_reviewer_binds_exact_artifact_and_domain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _QueuedTransport([OpenRouterReviewResponse(200, _payload(0.96))])

    submission = _review(monkeypatch, transport)

    assert submission.domain is QaDomain.BRAND
    assert submission.artifact_sha256 == "a" * 64
    assert submission.passed is True
    assert submission.threshold == pytest.approx(0.90)
    assert submission.reviewer_id == "openrouter-brand-review:openrouter/free"
    assert len(submission.evidence_references) == 2
    assert all(reference.startswith("brand-frame-sha256:") for reference in submission.evidence_references)
    assert "artifact=" + "a" * 64 in submission.provenance_reference
    response_format = transport.requests[0]["response_format"]
    assert isinstance(response_format, Mapping)
    assert response_format["type"] == "json_schema"


def test_brand_reviewer_fails_closed_below_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _QueuedTransport(
        [OpenRouterReviewResponse(200, _payload(0.40, "remove-provider-watermark"))]
    )

    submission = _review(monkeypatch, transport)

    assert submission.passed is False
    assert submission.repair_target == "remove-provider-watermark"


def test_brand_reviewer_capability_fallback_remains_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _QueuedTransport(
        [
            OpenRouterReviewResponse(404, {"error": {"message": "unsupported"}}),
            OpenRouterReviewResponse(200, _payload(0.95)),
        ]
    )

    submission = _review(monkeypatch, transport)

    assert submission.passed is True
    assert len(transport.requests) == 2
    assert "response_format" in transport.requests[0]
    assert "response_format" not in transport.requests[1]
    assert "route=prompt-json-fallback" in submission.provenance_reference


def test_brand_reviewer_rejects_non_independent_producer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        brand_module,
        "_sample_frames",
        lambda path, count: (b"one", b"two"),
    )
    reviewer = OpenRouterBrandPerceptualReviewer(
        "secret",
        "openrouter/free",
        sample_count=2,
        transport=_QueuedTransport([]),
    )

    with pytest.raises(OpenRouterPerceptualReviewError, match="independent"):
        reviewer.review(
            video_path=Path("unused.mp4"),
            objective="Brand check.",
            artifact_sha256="b" * 64,
            producer_id=reviewer.reviewer_id,
            review_id="brand-review-002",
        )
