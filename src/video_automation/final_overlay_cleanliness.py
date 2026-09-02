"""Independent final-overlay cleanliness evidence for canonical Video delivery.

This module samples the exact final MP4 and asks an independent multimodal reviewer
for explicit watermark/provider-overlay findings. It does not manufacture a pass,
change acceptance authority, perform provider generation, or permit paid routing by
itself. Callers remain responsible for selecting an explicitly free reviewer model.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .openrouter_perceptual_reviewer import (
    OpenRouterPerceptualReviewError,
    OpenRouterReviewTransport,
    UrllibOpenRouterReviewTransport,
    _sample_frames,
)

_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_RETRYABLE_CAPABILITY_STATUS_CODES = frozenset({404, 503})
_CRITERIA_ID = "ilaios.video.final-overlay-cleanliness"
_CRITERIA_VERSION = "1.0.0"
_CRITERIA_TEXT = (
    "Inspect only the sampled frames from the exact final video artifact. Report whether "
    "any visible stock watermark, provider/platform overlay, AI/model/provider logo, or "
    "unexpected branding overlay is present. Do not infer absence from technical quality. "
    "Each detection field must be an explicit boolean grounded in the sampled frames."
)
_REQUIRED_KEYS = frozenset(
    {
        "stock_watermark_detected",
        "provider_overlay_detected",
        "ai_provider_logo_detected",
        "unexpected_branding_overlay_detected",
        "detail",
    }
)


@dataclass(frozen=True, slots=True)
class FinalOverlayCleanlinessEvidence:
    """Exact-artifact structured evidence for forbidden visible overlays."""

    evidence_id: str
    artifact_sha256: str
    reviewer_id: str
    criteria_id: str
    criteria_version: str
    criteria_sha256: str
    evidence_references: tuple[str, ...]
    provenance_reference: str
    stock_watermark_detected: bool
    provider_overlay_detected: bool
    ai_provider_logo_detected: bool
    unexpected_branding_overlay_detected: bool
    detail: str

    @property
    def passed(self) -> bool:
        return not any(
            (
                self.stock_watermark_detected,
                self.provider_overlay_detected,
                self.ai_provider_logo_detected,
                self.unexpected_branding_overlay_detected,
            )
        )


class OpenRouterFinalOverlayCleanlinessReviewer:
    """Produce structured final-overlay evidence from sampled exact-artifact frames."""

    def __init__(
        self,
        api_key: str,
        model_id: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 90.0,
        sample_count: int = 4,
        transport: OpenRouterReviewTransport | None = None,
    ) -> None:
        if not api_key or api_key != api_key.strip():
            raise OpenRouterPerceptualReviewError("api_key must be non-blank and trimmed")
        if not model_id or model_id != model_id.strip():
            raise OpenRouterPerceptualReviewError("model_id must be non-blank and trimmed")
        if model_id != "openrouter/free" and not model_id.endswith(":free"):
            raise OpenRouterPerceptualReviewError(
                "final overlay reviewer requires an explicit free model alias"
            )
        if not base_url or base_url != base_url.strip():
            raise OpenRouterPerceptualReviewError("base_url must be non-blank and trimmed")
        if timeout_seconds <= 0:
            raise OpenRouterPerceptualReviewError("timeout_seconds must be positive")
        if sample_count < 2 or sample_count > 8:
            raise OpenRouterPerceptualReviewError("sample_count must be between 2 and 8")
        self._api_key = api_key
        self._model_id = model_id
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._sample_count = sample_count
        self._transport = transport or UrllibOpenRouterReviewTransport()

    @property
    def reviewer_id(self) -> str:
        return f"openrouter-overlay-review:{self._model_id}"

    def review(
        self,
        *,
        video_path: Path,
        artifact_sha256: str,
        evidence_id: str,
    ) -> FinalOverlayCleanlinessEvidence:
        if not evidence_id or evidence_id != evidence_id.strip():
            raise OpenRouterPerceptualReviewError(
                "evidence_id must be non-blank and trimmed"
            )
        if len(artifact_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in artifact_sha256
        ):
            raise OpenRouterPerceptualReviewError(
                "artifact_sha256 must be lowercase SHA-256"
            )
        if not video_path.is_file():
            raise OpenRouterPerceptualReviewError("review video does not exist")
        body = video_path.read_bytes()
        if not body or sha256(body).hexdigest() != artifact_sha256:
            raise OpenRouterPerceptualReviewError(
                "overlay review artifact SHA does not match final MP4 bytes"
            )

        frames = _sample_frames(video_path, self._sample_count)
        frame_refs = tuple(
            f"overlay-frame-sha256:{sha256(frame).hexdigest()}" for frame in frames
        )
        content: list[dict[str, object]] = [
            {
                "type": "text",
                "text": (
                    f"{_CRITERIA_TEXT}\n\n"
                    "Return only JSON with exactly stock_watermark_detected, "
                    "provider_overlay_detected, ai_provider_logo_detected, "
                    "unexpected_branding_overlay_detected, detail."
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
                "stock_watermark_detected": {"type": "boolean"},
                "provider_overlay_detected": {"type": "boolean"},
                "ai_provider_logo_detected": {"type": "boolean"},
                "unexpected_branding_overlay_detected": {"type": "boolean"},
                "detail": {"type": "string"},
            },
            "required": sorted(_REQUIRED_KEYS),
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
                "name": "ilaios_video_final_overlay_cleanliness",
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
        route = "json-schema"
        if response.status_code in _RETRYABLE_CAPABILITY_STATUS_CODES:
            response = self._transport.post_json(
                endpoint,
                headers=headers,
                body=base_body,
                timeout_seconds=self._timeout_seconds,
            )
            route = "prompt-json-fallback"
        if not 200 <= response.status_code < 300:
            raise OpenRouterPerceptualReviewError(
                f"OpenRouter overlay review failed with HTTP {response.status_code}"
            )
        result = _extract_overlay_review(response.payload)
        return FinalOverlayCleanlinessEvidence(
            evidence_id=evidence_id,
            artifact_sha256=artifact_sha256,
            reviewer_id=self.reviewer_id,
            criteria_id=_CRITERIA_ID,
            criteria_version=_CRITERIA_VERSION,
            criteria_sha256=sha256(_CRITERIA_TEXT.encode("utf-8")).hexdigest(),
            evidence_references=frame_refs,
            provenance_reference=(
                f"openrouter-overlay-review:model={self._model_id}:route={route}:"
                f"artifact={artifact_sha256}"
            ),
            stock_watermark_detected=result["stock_watermark_detected"],
            provider_overlay_detected=result["provider_overlay_detected"],
            ai_provider_logo_detected=result["ai_provider_logo_detected"],
            unexpected_branding_overlay_detected=result[
                "unexpected_branding_overlay_detected"
            ],
            detail=result["detail"],
        )


def _extract_overlay_review(payload: Mapping[str, object]) -> dict[str, object]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise OpenRouterPerceptualReviewError("overlay review response is missing choices")
    first = choices[0]
    if not isinstance(first, Mapping):
        raise OpenRouterPerceptualReviewError("overlay review choice is malformed")
    message = first.get("message")
    if not isinstance(message, Mapping):
        raise OpenRouterPerceptualReviewError("overlay review message is malformed")
    raw = message.get("content")
    if not isinstance(raw, str) or not raw.strip():
        raise OpenRouterPerceptualReviewError("overlay review content is missing")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OpenRouterPerceptualReviewError(
            "overlay review content is not valid JSON"
        ) from exc
    if not isinstance(value, dict) or frozenset(value) != _REQUIRED_KEYS:
        raise OpenRouterPerceptualReviewError(
            "overlay review content has an invalid schema"
        )
    for key in _REQUIRED_KEYS - {"detail"}:
        if not isinstance(value.get(key), bool):
            raise OpenRouterPerceptualReviewError(
                f"overlay review field {key} must be boolean"
            )
    detail = value.get("detail")
    if not isinstance(detail, str) or not detail.strip():
        raise OpenRouterPerceptualReviewError("overlay review detail is invalid")
    return {
        "stock_watermark_detected": value["stock_watermark_detected"],
        "provider_overlay_detected": value["provider_overlay_detected"],
        "ai_provider_logo_detected": value["ai_provider_logo_detected"],
        "unexpected_branding_overlay_detected": value[
            "unexpected_branding_overlay_detected"
        ],
        "detail": detail.strip(),
    }
