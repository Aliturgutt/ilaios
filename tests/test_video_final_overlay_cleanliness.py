from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path

import pytest

import src.video_automation.final_overlay_cleanliness as overlay_module
from src.video_automation.final_overlay_cleanliness import (
    OpenRouterFinalOverlayCleanlinessReviewer,
)
from src.video_automation.openrouter_perceptual_reviewer import (
    OpenRouterPerceptualReviewError,
    OpenRouterReviewResponse,
)


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
            raise AssertionError("unexpected overlay review request")
        return self._responses.pop(0)


def _payload(
    *,
    stock_watermark_detected: bool = False,
    provider_overlay_detected: bool = False,
    ai_provider_logo_detected: bool = False,
    unexpected_branding_overlay_detected: bool = False,
) -> dict[str, object]:
    content = json.dumps(
        {
            "stock_watermark_detected": stock_watermark_detected,
            "provider_overlay_detected": provider_overlay_detected,
            "ai_provider_logo_detected": ai_provider_logo_detected,
            "unexpected_branding_overlay_detected": unexpected_branding_overlay_detected,
            "detail": "sampled exact final frames",
        }
    )
    return {"choices": [{"message": {"content": content}}]}


def _review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    transport: _QueuedTransport,
):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"exact-final-video-bytes")
    digest = sha256(video.read_bytes()).hexdigest()
    monkeypatch.setattr(
        overlay_module,
        "_sample_frames",
        lambda path, count: (b"frame-one", b"frame-two"),
    )
    reviewer = OpenRouterFinalOverlayCleanlinessReviewer(
        "secret",
        "openrouter/free",
        sample_count=2,
        transport=transport,
    )
    return reviewer.review(
        video_path=video,
        artifact_sha256=digest,
        evidence_id="overlay-evidence-001",
    )


def test_overlay_reviewer_binds_exact_artifact_and_explicit_clean_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _QueuedTransport([OpenRouterReviewResponse(200, _payload())])

    evidence = _review(tmp_path, monkeypatch, transport)

    assert evidence.passed is True
    assert evidence.artifact_sha256 == sha256(b"exact-final-video-bytes").hexdigest()
    assert evidence.reviewer_id == "openrouter-overlay-review:openrouter/free"
    assert len(evidence.evidence_references) == 2
    assert all(
        reference.startswith("overlay-frame-sha256:")
        for reference in evidence.evidence_references
    )
    response_format = transport.requests[0]["response_format"]
    assert isinstance(response_format, Mapping)
    assert response_format["type"] == "json_schema"


def test_overlay_reviewer_reports_detected_provider_overlay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _QueuedTransport(
        [OpenRouterReviewResponse(200, _payload(provider_overlay_detected=True))]
    )

    evidence = _review(tmp_path, monkeypatch, transport)

    assert evidence.passed is False
    assert evidence.provider_overlay_detected is True


def test_overlay_reviewer_rejects_wrong_artifact_sha(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video = tmp_path / "final.mp4"
    video.write_bytes(b"exact-final-video-bytes")
    monkeypatch.setattr(
        overlay_module,
        "_sample_frames",
        lambda path, count: (b"frame-one", b"frame-two"),
    )
    reviewer = OpenRouterFinalOverlayCleanlinessReviewer(
        "secret",
        "openrouter/free",
        sample_count=2,
        transport=_QueuedTransport([]),
    )

    with pytest.raises(OpenRouterPerceptualReviewError, match="artifact SHA"):
        reviewer.review(
            video_path=video,
            artifact_sha256="a" * 64,
            evidence_id="overlay-evidence-002",
        )


def test_overlay_reviewer_rejects_non_free_model() -> None:
    with pytest.raises(OpenRouterPerceptualReviewError, match="explicit free"):
        OpenRouterFinalOverlayCleanlinessReviewer(
            "secret",
            "provider/paid-model",
        )


def test_overlay_reviewer_fallback_remains_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _QueuedTransport(
        [
            OpenRouterReviewResponse(404, {"error": {"message": "unsupported"}}),
            OpenRouterReviewResponse(200, _payload()),
        ]
    )

    evidence = _review(tmp_path, monkeypatch, transport)

    assert evidence.passed is True
    assert len(transport.requests) == 2
    assert "response_format" in transport.requests[0]
    assert "response_format" not in transport.requests[1]
    assert "route=prompt-json-fallback" in evidence.provenance_reference
