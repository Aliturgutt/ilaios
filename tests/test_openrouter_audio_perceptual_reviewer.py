from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path

import pytest

from src.video_automation.openrouter_audio_perceptual_reviewer import (
    OpenRouterAudioPerceptualReviewer,
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
            raise AssertionError("unexpected audio review request")
        return self._responses.pop(0)


def _payload(score: float, repair_target: str = "") -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"score":'
                        f"{score}"
                        ',"detail":"audio evidence",'
                        f'"repair_target":"{repair_target}"'
                        "}"
                    )
                }
            }
        ]
    }


def _video(tmp_path: Path) -> tuple[Path, str]:
    path = tmp_path / "final.mp4"
    path.write_bytes(b"exact-final-video-bytes")
    return path, sha256(path.read_bytes()).hexdigest()


def test_audio_reviewer_binds_exact_artifact_and_audio_evidence(tmp_path: Path) -> None:
    video_path, artifact_sha = _video(tmp_path)
    audio = b"RIFF-fake-review-audio"
    transport = _QueuedTransport([OpenRouterReviewResponse(200, _payload(0.94))])
    reviewer = OpenRouterAudioPerceptualReviewer(
        "secret",
        "audio-capable-model",
        transport=transport,
        audio_extractor=lambda path: audio,
    )

    submission = reviewer.review(
        video_path=video_path,
        objective="Documentary narration with balanced music and intelligible speech.",
        artifact_sha256=artifact_sha,
        producer_id="ilaios-provider-video-factory",
        review_id="audio-review-001",
    )

    assert submission.domain is QaDomain.AUDIO
    assert submission.artifact_sha256 == artifact_sha
    assert submission.passed is True
    assert submission.threshold == pytest.approx(0.86)
    assert submission.evidence_references == (
        f"final-video-sha256:{artifact_sha}",
        f"audio-wav-sha256:{sha256(audio).hexdigest()}",
    )
    messages = transport.requests[0]["messages"]
    assert isinstance(messages, tuple)
    content = messages[0]["content"]
    assert isinstance(content, tuple)
    assert content[1]["type"] == "input_audio"
    input_audio = content[1]["input_audio"]
    assert isinstance(input_audio, Mapping)
    assert input_audio["format"] == "wav"


def test_audio_reviewer_fails_closed_below_threshold(tmp_path: Path) -> None:
    video_path, artifact_sha = _video(tmp_path)
    reviewer = OpenRouterAudioPerceptualReviewer(
        "secret",
        "audio-capable-model",
        transport=_QueuedTransport(
            [OpenRouterReviewResponse(200, _payload(0.41, "repair-mix-and-ducking"))]
        ),
        audio_extractor=lambda path: b"audio",
    )

    submission = reviewer.review(
        video_path=video_path,
        objective="Clear voice over restrained music.",
        artifact_sha256=artifact_sha,
        producer_id="ilaios-provider-video-factory",
        review_id="audio-review-002",
    )

    assert submission.passed is False
    assert submission.repair_target == "repair-mix-and-ducking"


def test_audio_reviewer_rejects_artifact_digest_mismatch(tmp_path: Path) -> None:
    video_path, _ = _video(tmp_path)
    reviewer = OpenRouterAudioPerceptualReviewer(
        "secret",
        "audio-capable-model",
        transport=_QueuedTransport([]),
        audio_extractor=lambda path: b"audio",
    )

    with pytest.raises(OpenRouterPerceptualReviewError, match="digest does not match"):
        reviewer.review(
            video_path=video_path,
            objective="Audio integrity.",
            artifact_sha256="a" * 64,
            producer_id="ilaios-provider-video-factory",
            review_id="audio-review-003",
        )


def test_audio_reviewer_rejects_non_independent_producer(tmp_path: Path) -> None:
    video_path, artifact_sha = _video(tmp_path)
    reviewer = OpenRouterAudioPerceptualReviewer(
        "secret",
        "audio-capable-model",
        transport=_QueuedTransport([]),
        audio_extractor=lambda path: b"audio",
    )

    with pytest.raises(OpenRouterPerceptualReviewError, match="independent"):
        reviewer.review(
            video_path=video_path,
            objective="Audio integrity.",
            artifact_sha256=artifact_sha,
            producer_id=reviewer.reviewer_id,
            review_id="audio-review-004",
        )
