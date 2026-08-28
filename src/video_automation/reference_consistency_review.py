"""Independent visual-consistency QA for reference-conditioned video.

This reviewer compares admitted reference images with sampled frames from the
finished video. It evaluates only visible continuity. Subject checks are not
biometric identity verification and must never infer sensitive traits.
"""

from __future__ import annotations

import base64
import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .media_technical_validation import FfprobeMediaTechnicalProbe
from .openrouter_perceptual_reviewer import (
    OpenRouterReviewTransport,
    OpenRouterReviewResponse,
    UrllibOpenRouterReviewTransport,
)
from .reference_image_analysis import ReferenceImageInput

_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_THRESHOLD = 0.82
_CRITICAL_ROLE_THRESHOLD = 0.80
_MAX_REVIEW_REFERENCES = 6
_SAMPLE_COUNT = 4
_RETRYABLE_CAPABILITY_STATUS_CODES = frozenset({404, 503})
_FREE_VISION_FALLBACK_MODEL_ID = "google/gemma-4-26b-a4b-it-20260403:free"
_CRITICAL_ROLES = frozenset({"subject", "product", "logo"})
_BOUNDARY_ROLES = frozenset({"first_frame", "last_frame"})
_CRITERIA_VERSION = "ilaios.video.reference-consistency.v3"
_RESULT_KEYS = frozenset(
    {
        "score",
        "subject_score",
        "product_score",
        "logo_score",
        "detail",
        "repair_target",
    }
)
_CRITERIA_TEXT = (
    "Compare the supplied user reference images with the sampled frames from the generated "
    "video. Judge only observable visual consistency. For SUBJECT references compare visible "
    "appearance cues such as silhouette, clothing, hair, accessories, colors and distinctive "
    "non-sensitive visual details; do not identify a real person, perform biometric matching, "
    "or infer sensitive traits. For PRODUCT references compare geometry, proportions, materials, "
    "colors and visible markings. For LOGO references compare visible shape, text/mark structure, "
    "colors and placement when the logo is expected to appear. FIRST_FRAME and LAST_FRAME "
    "references must be compared specifically against the labeled exact boundary frame supplied "
    "for that role. Penalize substitutions, distorted logos, contradictory geometry/colors/"
    "materials, boundary-frame drift, or severe continuity drift."
)


class ReferenceConsistencyReviewError(RuntimeError):
    """Raised when independent reference-consistency evidence cannot be established."""


@dataclass(frozen=True, slots=True)
class ReferenceConsistencyReview:
    reviewer_id: str
    criteria_version: str
    score: float
    threshold: float
    subject_score: float | None
    product_score: float | None
    logo_score: float | None
    detail: str
    repair_target: str
    reference_sha256s: tuple[str, ...]
    reference_roles: tuple[str, ...]
    frame_sha256s: tuple[str, ...]
    first_frame_sha256: str | None
    last_frame_sha256: str | None

    @property
    def passed(self) -> bool:
        if self.score < self.threshold:
            return False
        for value in (self.subject_score, self.product_score, self.logo_score):
            if value is not None and value < _CRITICAL_ROLE_THRESHOLD:
                return False
        return True


class OpenRouterReferenceConsistencyReviewer:
    """Review visible subject/product/logo continuity using an independent model."""

    def __init__(
        self,
        api_key: str,
        model_id: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 120.0,
        threshold: float = _DEFAULT_THRESHOLD,
        transport: OpenRouterReviewTransport | None = None,
    ) -> None:
        _text("api_key", api_key)
        _text("model_id", model_id)
        _text("base_url", base_url)
        if model_id != "openrouter/free" and not model_id.endswith(":free"):
            raise ReferenceConsistencyReviewError(
                "reference consistency review must use an explicitly free model"
            )
        if timeout_seconds <= 0:
            raise ReferenceConsistencyReviewError("review timeout must be positive")
        if not _DEFAULT_THRESHOLD <= threshold <= 1.0:
            raise ReferenceConsistencyReviewError(
                f"reference consistency threshold must be >= {_DEFAULT_THRESHOLD:.2f}"
            )
        self._api_key = api_key
        self._model_id = model_id
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._threshold = threshold
        self._transport = transport or UrllibOpenRouterReviewTransport()

    @property
    def reviewer_id(self) -> str:
        return f"openrouter-reference-consistency:{self._model_id}"

    def review(
        self,
        *,
        video_path: Path,
        references: Sequence[ReferenceImageInput],
    ) -> ReferenceConsistencyReview:
        if not references:
            raise ReferenceConsistencyReviewError("reference consistency requires references")
        selected = _select_references(references)
        frames = _sample_video_frames(video_path, _SAMPLE_COUNT)
        boundaries = _sample_boundary_frames(video_path, selected)
        applicable_roles = frozenset(reference.role for reference in selected) & _CRITICAL_ROLES
        content: list[dict[str, object]] = [
            {
                "type": "text",
                "text": (
                    f"CRITERIA_VERSION={_CRITERIA_VERSION}\n{_CRITERIA_TEXT}\n\n"
                    f"APPLICABLE CRITICAL ROLES: {', '.join(sorted(applicable_roles)) or 'none'}\n"
                    "Return a strict JSON object. score is overall reference fidelity from 0 to 1. "
                    "subject_score/product_score/logo_score must be null when that role is absent, "
                    "otherwise 0 to 1. detail must cite visible reasons only. repair_target must be "
                    "a concise regeneration target."
                ),
            }
        ]
        for index, reference in enumerate(selected, start=1):
            normalized = _normalize_reference(reference.content)
            content.append(
                {
                    "type": "text",
                    "text": f"REFERENCE {index}; ROLE={reference.role}; SHA256={reference.sha256_hex}",
                }
            )
            content.append(_image_part(normalized))
        content.append(
            {
                "type": "text",
                "text": "The following images are chronological interior samples from the finished video.",
            }
        )
        content.extend(_image_part(frame) for frame in frames)
        for role, frame in boundaries:
            content.append(
                {
                    "type": "text",
                    "text": f"EXACT BOUNDARY FRAME; ROLE={role}",
                }
            )
            content.append(_image_part(frame))
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
                "name": "ilaios_video_reference_consistency_review",
                "strict": True,
                "schema": _response_schema(),
            },
        }
        response = self._transport.post_json(
            f"{self._base_url}/chat/completions",
            headers=headers,
            body=strict_body,
            timeout_seconds=self._timeout_seconds,
        )
        if response.status_code == 429:
            response = self._transport.post_json(
                f"{self._base_url}/chat/completions",
                headers=headers,
                body=strict_body,
                timeout_seconds=self._timeout_seconds,
            )
        review_model_id = self._model_id
        if response.status_code in _RETRYABLE_CAPABILITY_STATUS_CODES:
            response = self._transport.post_json(
                f"{self._base_url}/chat/completions",
                headers=headers,
                body=base_body,
                timeout_seconds=self._timeout_seconds,
            )
        if (
            response.status_code in _RETRYABLE_CAPABILITY_STATUS_CODES
            and self._model_id == "openrouter/free"
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
            if response.status_code in _RETRYABLE_CAPABILITY_STATUS_CODES:
                fallback_base_body = dict(base_body)
                fallback_base_body["model"] = review_model_id
                response = self._transport.post_json(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    body=fallback_base_body,
                    timeout_seconds=self._timeout_seconds,
                )
        if not 200 <= response.status_code < 300:
            raise ReferenceConsistencyReviewError(
                f"reference consistency review failed with HTTP {response.status_code}"
            )
        result = _extract_result(response)
        _validate_role_scores(result, applicable_roles)
        boundary_hashes = {role: sha256(frame).hexdigest() for role, frame in boundaries}
        return ReferenceConsistencyReview(
            reviewer_id=f"openrouter-reference-consistency:{review_model_id}",
            criteria_version=_CRITERIA_VERSION,
            score=_required_score(result, "score"),
            threshold=self._threshold,
            subject_score=_optional_score(result, "subject_score"),
            product_score=_optional_score(result, "product_score"),
            logo_score=_optional_score(result, "logo_score"),
            detail=_required_text(result, "detail"),
            repair_target=_required_text(result, "repair_target"),
            reference_sha256s=tuple(reference.sha256_hex for reference in selected),
            reference_roles=tuple(reference.role for reference in selected),
            frame_sha256s=tuple(sha256(frame).hexdigest() for frame in frames),
            first_frame_sha256=boundary_hashes.get("first_frame"),
            last_frame_sha256=boundary_hashes.get("last_frame"),
        )


def _select_references(
    references: Sequence[ReferenceImageInput],
) -> tuple[ReferenceImageInput, ...]:
    critical = [reference for reference in references if reference.role in _CRITICAL_ROLES]
    remaining = [reference for reference in references if reference.role not in _CRITICAL_ROLES]
    selected = tuple((critical + remaining)[:_MAX_REVIEW_REFERENCES])
    if not selected:
        raise ReferenceConsistencyReviewError("no reference image is available for review")
    return selected


def _response_schema() -> dict[str, object]:
    nullable_score = {"anyOf": [{"type": "number", "minimum": 0, "maximum": 1}, {"type": "null"}]}
    return {
        "type": "object",
        "properties": {
            "score": {"type": "number", "minimum": 0, "maximum": 1},
            "subject_score": nullable_score,
            "product_score": nullable_score,
            "logo_score": nullable_score,
            "detail": {"type": "string"},
            "repair_target": {"type": "string"},
        },
        "required": sorted(_RESULT_KEYS),
        "additionalProperties": False,
    }


def _extract_result(response: OpenRouterReviewResponse) -> dict[str, object]:
    choices = response.payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ReferenceConsistencyReviewError("review response is missing choices")
    first = choices[0]
    if not isinstance(first, Mapping):
        raise ReferenceConsistencyReviewError("review choice is malformed")
    message = first.get("message")
    if not isinstance(message, Mapping):
        raise ReferenceConsistencyReviewError("review message is malformed")
    raw = message.get("content")
    if not isinstance(raw, str) or not raw.strip():
        raise ReferenceConsistencyReviewError("review content is missing")
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ReferenceConsistencyReviewError("review content is invalid JSON") from error
    if not isinstance(result, dict) or frozenset(result) != _RESULT_KEYS:
        raise ReferenceConsistencyReviewError("review content has unexpected keys")
    return result


def _validate_role_scores(result: Mapping[str, object], applicable: frozenset[str]) -> None:
    mapping = {
        "subject": "subject_score",
        "product": "product_score",
        "logo": "logo_score",
    }
    for role, key in mapping.items():
        value = result.get(key)
        if role in applicable and value is None:
            raise ReferenceConsistencyReviewError(f"{role} consistency score is missing")
        if role not in applicable and value is not None:
            raise ReferenceConsistencyReviewError(f"{role} consistency score must be null")
        if value is not None:
            _score_value(value, key)


def _required_score(result: Mapping[str, object], key: str) -> float:
    return _score_value(result.get(key), key)


def _optional_score(result: Mapping[str, object], key: str) -> float | None:
    value = result.get(key)
    return None if value is None else _score_value(value, key)


def _score_value(value: object, key: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReferenceConsistencyReviewError(f"{key} must be numeric")
    normalized = float(value)
    if not 0 <= normalized <= 1:
        raise ReferenceConsistencyReviewError(f"{key} must be between 0 and 1")
    return normalized


def _required_text(result: Mapping[str, object], key: str) -> str:
    value = result.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise ReferenceConsistencyReviewError(f"{key} is invalid")
    return value.strip()


def _image_part(jpeg: bytes) -> dict[str, object]:
    return {
        "type": "image_url",
        "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")},
    }


def _normalize_reference(content: bytes) -> bytes:
    return _ffmpeg_image(
        (
            "ffmpeg",
            "-v",
            "error",
            "-i",
            "pipe:0",
            "-frames:v",
            "1",
            "-an",
            "-sn",
            "-map_metadata",
            "-1",
            "-vf",
            "scale=w='min(768,iw)':h='min(768,ih)':force_original_aspect_ratio=decrease",
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "-q:v",
            "5",
            "pipe:1",
        ),
        input_bytes=content,
    )


def _sample_video_frames(path: Path, count: int) -> tuple[bytes, ...]:
    if not path.is_file():
        raise ReferenceConsistencyReviewError("review video does not exist")
    observation = FfprobeMediaTechnicalProbe(timeout_seconds=30).probe(path)
    positions = tuple(
        observation.duration_seconds * (index + 1) / (count + 1) for index in range(count)
    )
    return tuple(_sample_frame(path, position) for position in positions)


def _sample_boundary_frames(
    path: Path,
    references: Sequence[ReferenceImageInput],
) -> tuple[tuple[str, bytes], ...]:
    required = frozenset(reference.role for reference in references) & _BOUNDARY_ROLES
    if not required:
        return ()
    if not path.is_file():
        raise ReferenceConsistencyReviewError("review video does not exist")
    observation = FfprobeMediaTechnicalProbe(timeout_seconds=30).probe(path)
    duration = observation.duration_seconds
    if duration <= 0:
        raise ReferenceConsistencyReviewError("review video duration is invalid")
    frames: list[tuple[str, bytes]] = []
    if "first_frame" in required:
        frames.append(("first_frame", _sample_frame(path, 0.0)))
    if "last_frame" in required:
        frames.append(("last_frame", _sample_frame(path, max(duration - 0.001, 0.0))))
    return tuple(frames)


def _sample_frame(path: Path, position: float) -> bytes:
    return _ffmpeg_image(
        (
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
            "scale=768:-2",
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "pipe:1",
        )
    )


def _ffmpeg_image(command: tuple[str, ...], *, input_bytes: bytes | None = None) -> bytes:
    try:
        completed = subprocess.run(
            command,
            input=input_bytes,
            check=False,
            capture_output=True,
            timeout=45,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise ReferenceConsistencyReviewError("ffmpeg reference QA sampling failed") from error
    if completed.returncode != 0 or not completed.stdout:
        raise ReferenceConsistencyReviewError("ffmpeg did not produce reference QA image")
    if len(completed.stdout) > 1_310_720:
        raise ReferenceConsistencyReviewError("reference QA image remains oversized")
    return completed.stdout


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise ReferenceConsistencyReviewError(f"{name} must be trimmed text")
