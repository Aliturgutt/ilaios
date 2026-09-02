"""Independent OpenRouter-backed AUDIO review for exact final video artifacts.

The reviewer extracts the audio stream from the exact immutable final MP4,
binds the extracted PCM evidence to the supplied artifact SHA-256, and submits
that audio plus the user objective to an independent audio-capable model. It
returns the canonical ``PerceptualReviewSubmission`` for the AUDIO domain.

No request is made unless an explicit model is configured. The adapter does not
alter media, generate content, or weaken deterministic audio signal checks.
"""

from __future__ import annotations

import base64
import subprocess
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path

from .openrouter_perceptual_reviewer import (
    OpenRouterPerceptualReviewError,
    OpenRouterReviewTransport,
    UrllibOpenRouterReviewTransport,
    _extract_review,
)
from .perceptual_review import PerceptualReviewSubmission, PerceptualReviewerKind
from .video_skills import QaDomain

_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_CRITERIA_ID = "ilaios.video.final-audio-integrity"
_CRITERIA_VERSION = "1.0.0"
_CRITERIA_TEXT = (
    "Judge AUDIO integrity and objective alignment only from the supplied audio extracted "
    "from the exact final video. Reject unintelligible or materially distorted speech, "
    "severe clipping, broken edits, distracting silence/dropouts, incoherent music or SFX, "
    "poor voice/music balance, or audio content that materially contradicts the user "
    "objective. Do not infer a pass from technical stream presence alone."
)
AudioExtractor = Callable[[Path], bytes]


class OpenRouterAudioPerceptualReviewer:
    """Produce independent AUDIO evidence from an exact final-video audio stream."""

    def __init__(
        self,
        api_key: str,
        model_id: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 90.0,
        threshold: float = 0.86,
        transport: OpenRouterReviewTransport | None = None,
        audio_extractor: AudioExtractor | None = None,
    ) -> None:
        for name, value in (("api_key", api_key), ("model_id", model_id), ("base_url", base_url)):
            if not value or value != value.strip():
                raise OpenRouterPerceptualReviewError(f"{name} must be non-blank and trimmed")
        if timeout_seconds <= 0:
            raise OpenRouterPerceptualReviewError("timeout_seconds must be positive")
        if not 0 < threshold <= 1:
            raise OpenRouterPerceptualReviewError("threshold must be in (0, 1]")
        self._api_key = api_key
        self._model_id = model_id
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._threshold = threshold
        self._transport = transport or UrllibOpenRouterReviewTransport()
        self._audio_extractor = audio_extractor or _extract_pcm_wav

    @property
    def reviewer_id(self) -> str:
        return f"openrouter-audio-review:{self._model_id}"

    def review(
        self,
        *,
        video_path: Path,
        objective: str,
        artifact_sha256: str,
        producer_id: str,
        review_id: str,
    ) -> PerceptualReviewSubmission:
        for name, value in (("objective", objective), ("producer_id", producer_id), ("review_id", review_id)):
            if not value or value != value.strip():
                raise OpenRouterPerceptualReviewError(f"{name} must be non-blank and trimmed")
        _require_sha256(artifact_sha256)
        if self.reviewer_id == producer_id:
            raise OpenRouterPerceptualReviewError(
                "perceptual reviewer must be independent from artifact producer"
            )
        if not video_path.is_file():
            raise OpenRouterPerceptualReviewError("audio review video path is not a file")
        actual_sha256 = sha256(video_path.read_bytes()).hexdigest()
        if actual_sha256 != artifact_sha256:
            raise OpenRouterPerceptualReviewError(
                "audio review artifact digest does not match exact final video"
            )

        audio = self._audio_extractor(video_path)
        if not audio:
            raise OpenRouterPerceptualReviewError("final video has no reviewable audio evidence")
        audio_sha256 = sha256(audio).hexdigest()
        content: tuple[dict[str, object], ...] = (
            {
                "type": "text",
                "text": (
                    f"{_CRITERIA_TEXT}\n\nUSER OBJECTIVE:\n{objective}\n\n"
                    "Return only JSON with exactly score, detail, repair_target. Score from 0 "
                    "to 1. A passing artifact must satisfy the AUDIO criteria."
                ),
            },
            {
                "type": "input_audio",
                "input_audio": {
                    "data": base64.b64encode(audio).decode("ascii"),
                    "format": "wav",
                },
            },
        )
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 1},
                "detail": {"type": "string"},
                "repair_target": {"type": "string"},
            },
            "required": ["score", "detail", "repair_target"],
            "additionalProperties": False,
        }
        body: dict[str, object] = {
            "model": self._model_id,
            "messages": ({"role": "user", "content": content},),
            "provider": {"require_parameters": True},
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "ilaios_video_audio_review",
                    "strict": True,
                    "schema": schema,
                },
            },
            "stream": False,
        }
        response = self._transport.post_json(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            body=body,
            timeout_seconds=self._timeout_seconds,
        )
        if not 200 <= response.status_code < 300:
            raise OpenRouterPerceptualReviewError(
                f"OpenRouter audio review failed with HTTP {response.status_code}"
            )
        result = _extract_review(response.payload)
        score = result["score"]
        repair_target = result["repair_target"]
        assert isinstance(score, float)
        assert isinstance(repair_target, str)
        passed = score >= self._threshold
        return PerceptualReviewSubmission(
            review_id=review_id,
            domain=QaDomain.AUDIO,
            artifact_sha256=artifact_sha256,
            reviewer_id=self.reviewer_id,
            producer_id=producer_id,
            reviewer_kind=PerceptualReviewerKind.INDEPENDENT_MODEL,
            criteria_id=_CRITERIA_ID,
            criteria_version=_CRITERIA_VERSION,
            criteria_sha256=sha256(_CRITERIA_TEXT.encode("utf-8")).hexdigest(),
            score=score,
            threshold=self._threshold,
            evidence_references=(
                f"final-video-sha256:{artifact_sha256}",
                f"audio-wav-sha256:{audio_sha256}",
            ),
            provenance_reference=(
                f"openrouter-audio-review:model={self._model_id}:artifact={artifact_sha256}:"
                f"audio={audio_sha256}"
            ),
            repair_target=None if passed else (repair_target.strip() or "repair-audio-integrity"),
        )


def _extract_pcm_wav(video_path: Path) -> bytes:
    completed = subprocess.run(
        (
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "2",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            "pipe:1",
        ),
        check=False,
        capture_output=True,
        timeout=60,
    )
    if completed.returncode != 0 or not completed.stdout:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise OpenRouterPerceptualReviewError(
            "failed to extract final-video audio for independent review"
            + (f": {detail[:240]}" if detail else "")
        )
    return completed.stdout


def _require_sha256(value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise OpenRouterPerceptualReviewError(
            "artifact_sha256 must be lowercase SHA-256"
        )
