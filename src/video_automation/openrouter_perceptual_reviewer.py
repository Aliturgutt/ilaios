"""Independent OpenRouter-backed perceptual review for generated video artifacts.

The reviewer samples frames from an already-produced video, sends those immutable
observations together with the exact user objective to a configured multimodal
model, and returns the canonical :mod:`perceptual_review` evidence contract.

It never produces media, never shares identity with the producer, and fails
closed when the reviewer cannot establish prompt alignment.
"""

from __future__ import annotations

import base64
import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from time import sleep
from types import MappingProxyType
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .media_technical_validation import FfprobeMediaTechnicalProbe
from .perceptual_review import (
    PerceptualReviewSubmission,
    PerceptualReviewerKind,
)
from .video_skills import QaDomain

_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_CRITERIA_ID = "ilaios.video.semantic-prompt-alignment"
_CRITERIA_VERSION = "1.0.0"
_RETRYABLE_CAPABILITY_STATUS_CODES = frozenset({404, 503})
_FREE_VISION_FALLBACK_SOURCE_MODEL_ID = "google/gemma-3-27b-it:free"
_FREE_VISION_FALLBACK_MODEL_ID = "google/gemma-4-26b-a4b-it-20260403:free"
_MAX_RATE_LIMIT_RETRY_AFTER_SECONDS = 60.0
_REVIEW_KEYS = frozenset({"score", "detail", "repair_target"})
_CRITERIA_TEXT = (
    "Judge only whether the sampled frames are a faithful visual realization of the "
    "requested video objective. Reject generic motion-graphics, title cards, placeholder "
    "panels, unrelated stock-like imagery, materially wrong subjects/settings/actions, "
    "or severe temporal/identity/continuity defects visible in the samples. Do not award "
    "credit merely because a playable video exists."
)


class OpenRouterPerceptualReviewError(RuntimeError):
    """Raised when independent perceptual evidence cannot be established."""


@dataclass(frozen=True, slots=True)
class OpenRouterReviewResponse:
    status_code: int
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.status_code <= 0:
            raise OpenRouterPerceptualReviewError("status_code must be positive")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


class OpenRouterReviewTransport(Protocol):
    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterReviewResponse: ...


class UrllibOpenRouterReviewTransport:
    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterReviewResponse:
        encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
        request = Request(url, data=encoded, headers=dict(headers), method="POST")
        for attempt in range(2):
            try:
                with urlopen(request, timeout=timeout_seconds) as response:
                    status = int(response.status)
                    raw = response.read().decode("utf-8")
            except HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                if int(exc.code) == 429 and attempt == 0:
                    retry_after = _bounded_retry_after_seconds(exc.headers)
                    if retry_after is not None:
                        sleep(retry_after)
                        continue
                return OpenRouterReviewResponse(int(exc.code), _decode_object(raw))
            except URLError as exc:
                raise OpenRouterPerceptualReviewError(
                    f"OpenRouter perceptual review transport error: {exc.reason}"
                ) from exc
            return OpenRouterReviewResponse(status, _decode_object(raw))
        raise OpenRouterPerceptualReviewError("OpenRouter transport retry state is invalid")


class OpenRouterPerceptualReviewer:
    """Produce independent visual semantic QA evidence from sampled video frames."""

    def __init__(
        self,
        api_key: str,
        model_id: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 90.0,
        threshold: float = 0.78,
        sample_count: int = 4,
        transport: OpenRouterReviewTransport | None = None,
    ) -> None:
        _text("api_key", api_key)
        _text("model_id", model_id)
        _text("base_url", base_url)
        if timeout_seconds <= 0:
            raise OpenRouterPerceptualReviewError("timeout_seconds must be positive")
        if not 0 < threshold <= 1:
            raise OpenRouterPerceptualReviewError("threshold must be in (0, 1]")
        if sample_count < 2 or sample_count > 8:
            raise OpenRouterPerceptualReviewError("sample_count must be between 2 and 8")
        self._api_key = api_key
        self._model_id = model_id
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._threshold = threshold
        self._sample_count = sample_count
        self._transport = transport or UrllibOpenRouterReviewTransport()

    @property
    def reviewer_id(self) -> str:
        return f"openrouter-semantic-review:{self._model_id}"

    def review(
        self,
        *,
        video_path: Path,
        objective: str,
        artifact_sha256: str,
        producer_id: str,
        review_id: str,
    ) -> PerceptualReviewSubmission:
        _text("objective", objective)
        _text("producer_id", producer_id)
        _text("review_id", review_id)
        _sha256("artifact_sha256", artifact_sha256)
        if self.reviewer_id == producer_id:
            raise OpenRouterPerceptualReviewError(
                "perceptual reviewer must be independent from artifact producer"
            )
        frames = _sample_frames(video_path, self._sample_count)
        frame_refs = tuple(f"frame-sha256:{sha256(frame).hexdigest()}" for frame in frames)
        content: list[dict[str, object]] = [
            {
                "type": "text",
                "text": (
                    f"{_CRITERIA_TEXT}\n\nUSER OBJECTIVE:\n{objective}\n\n"
                    "Return a strict score from 0 to 1. A generic explainer, motion-graphics "
                    "template, or unrelated clip must score below the threshold. Return only "
                    "a JSON object with exactly these keys: score, detail, repair_target. "
                    "Do not use markdown fences or add commentary outside the JSON object."
                ),
            }
        ]
        content.extend(
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/jpeg;base64," + base64.b64encode(frame).decode("ascii")
                },
            }
            for frame in frames
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
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        base_body: dict[str, object] = {
            "model": self._model_id,
            "messages": ({"role": "user", "content": content},),
            "provider": {"require_parameters": True},
            "stream": False,
        }
        strict_body = dict(base_body)
        strict_body["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "ilaios_video_semantic_review",
                "strict": True,
                "schema": schema,
            },
        }
        endpoint = f"{self._base_url}/chat/completions"
        response = self._transport.post_json(
            endpoint,
            headers=headers,
            body=strict_body,
            timeout_seconds=self._timeout_seconds,
        )
        review_model_id = self._model_id
        review_route = "json-schema"
        if response.status_code in _RETRYABLE_CAPABILITY_STATUS_CODES:
            response = self._transport.post_json(
                endpoint,
                headers=headers,
                body=base_body,
                timeout_seconds=self._timeout_seconds,
            )
            review_route = "prompt-json-fallback"
        if (
            response.status_code in _RETRYABLE_CAPABILITY_STATUS_CODES
            and self._model_id == _FREE_VISION_FALLBACK_SOURCE_MODEL_ID
        ):
            review_model_id = _FREE_VISION_FALLBACK_MODEL_ID
            fallback_strict_body = dict(strict_body)
            fallback_strict_body["model"] = review_model_id
            response = self._transport.post_json(
                f"{self._base_url}/chat/completions",
                headers=headers,
                body=fallback_strict_body,
                timeout_seconds=self._timeout_seconds,
            )
            review_route = "free-vision-json-schema-fallback"
            if response.status_code in _RETRYABLE_CAPABILITY_STATUS_CODES:
                fallback_base_body = dict(base_body)
                fallback_base_body["model"] = review_model_id
                response = self._transport.post_json(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    body=fallback_base_body,
                    timeout_seconds=self._timeout_seconds,
                )
                review_route = "free-vision-prompt-json-fallback"
        if not 200 <= response.status_code < 300:
            raise OpenRouterPerceptualReviewError(
                f"OpenRouter perceptual review failed with HTTP {response.status_code}"
            )
        try:
            result = _extract_review(response.payload)
        except OpenRouterPerceptualReviewError as exc:
            if review_route != "prompt-json-fallback" or str(exc) != "review content is not valid JSON":
                raise
            response = self._transport.post_json(
                endpoint,
                headers=headers,
                body=base_body,
                timeout_seconds=self._timeout_seconds,
            )
            if not 200 <= response.status_code < 300:
                raise OpenRouterPerceptualReviewError(
                    f"OpenRouter perceptual review failed with HTTP {response.status_code}"
                )
            result = _extract_review(response.payload)
            review_route = "prompt-json-fallback-retry"
        score = result["score"]
        assert isinstance(score, float)
        detail = result["detail"]
        repair_target = result["repair_target"]
        assert isinstance(detail, str)
        assert isinstance(repair_target, str)
        passed = score >= self._threshold
        return PerceptualReviewSubmission(
            review_id=review_id,
            domain=QaDomain.VISUAL,
            artifact_sha256=artifact_sha256,
            reviewer_id=f"openrouter-semantic-review:{review_model_id}",
            producer_id=producer_id,
            reviewer_kind=PerceptualReviewerKind.INDEPENDENT_MODEL,
            criteria_id=_CRITERIA_ID,
            criteria_version=_CRITERIA_VERSION,
            criteria_sha256=sha256(_CRITERIA_TEXT.encode("utf-8")).hexdigest(),
            score=score,
            threshold=self._threshold,
            evidence_references=frame_refs,
            provenance_reference=(
                f"openrouter-review:model={review_model_id}:route={review_route}:"
                f"artifact={artifact_sha256}"
            ),
            repair_target=None if passed else (repair_target.strip() or "regenerate-video"),
        )


def _sample_frames(path: Path, count: int) -> tuple[bytes, ...]:
    if not path.is_file():
        raise OpenRouterPerceptualReviewError("review video does not exist")
    observation = FfprobeMediaTechnicalProbe(timeout_seconds=30).probe(path)
    duration = observation.duration_seconds
    positions = tuple(duration * (index + 1) / (count + 1) for index in range(count))
    frames: list[bytes] = []
    for position in positions:
        command = (
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{position:.3f}",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            "scale=640:-2",
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "pipe:1",
        )
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                timeout=45,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise OpenRouterPerceptualReviewError(
                "ffmpeg frame sampling failed"
            ) from exc
        if completed.returncode != 0 or not completed.stdout:
            raise OpenRouterPerceptualReviewError(
                "ffmpeg did not produce a review frame"
            )
        frames.append(completed.stdout)
    return tuple(frames)


def _extract_review(payload: Mapping[str, object]) -> dict[str, object]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise OpenRouterPerceptualReviewError("review response is missing choices")
    first = choices[0]
    if not isinstance(first, Mapping):
        raise OpenRouterPerceptualReviewError("review choice is malformed")
    message = first.get("message")
    if not isinstance(message, Mapping):
        raise OpenRouterPerceptualReviewError("review message is malformed")
    raw = message.get("content")
    if not isinstance(raw, str) or not raw.strip():
        raise OpenRouterPerceptualReviewError("review content is missing")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OpenRouterPerceptualReviewError("review content is not valid JSON") from exc
    if not isinstance(value, dict):
        raise OpenRouterPerceptualReviewError("review content must be an object")
    if frozenset(value) != _REVIEW_KEYS:
        raise OpenRouterPerceptualReviewError(
            "review content must contain exactly score, detail, and repair_target"
        )
    score = value.get("score")
    detail = value.get("detail")
    repair_target = value.get("repair_target")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise OpenRouterPerceptualReviewError("review score is invalid")
    normalized_score = float(score)
    if not 0 <= normalized_score <= 1:
        raise OpenRouterPerceptualReviewError("review score is outside [0, 1]")
    if not isinstance(detail, str) or not detail.strip():
        raise OpenRouterPerceptualReviewError("review detail is invalid")
    if repair_target is None:
        repair_target = ""
    elif not isinstance(repair_target, str):
        raise OpenRouterPerceptualReviewError("review repair_target is invalid")
    return {
        "score": normalized_score,
        "detail": detail.strip(),
        "repair_target": repair_target,
    }


def _decode_object(raw: str) -> Mapping[str, object]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OpenRouterPerceptualReviewError("OpenRouter returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise OpenRouterPerceptualReviewError("OpenRouter response must be an object")
    return value


def _bounded_retry_after_seconds(headers: object) -> float | None:
    getter = getattr(headers, "get", None)
    if not callable(getter):
        return None
    raw = getter("Retry-After")
    if raw is None:
        return None
    try:
        seconds = float(str(raw).strip())
    except ValueError:
        return None
    if seconds < 0 or seconds > _MAX_RATE_LIMIT_RETRY_AFTER_SECONDS:
        return None
    return seconds


def _sha256(name: str, value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise OpenRouterPerceptualReviewError(f"{name} must be lowercase SHA-256")


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise OpenRouterPerceptualReviewError(f"{name} must be non-blank and trimmed")
