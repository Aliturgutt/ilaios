"""Independent OpenRouter-backed BRAND review for exact final video artifacts.

This adapter is additive to the existing VISUAL semantic reviewer. It samples the
same immutable final artifact, uses an independent multimodal reviewer, and
returns the canonical ``PerceptualReviewSubmission`` for the BRAND domain.

It does not weaken deterministic logo/cleanliness gates and does not perform
provider generation or any billable action by itself.
"""

from __future__ import annotations

import base64
from hashlib import sha256
from pathlib import Path

from .openrouter_perceptual_reviewer import (
    OpenRouterPerceptualReviewError,
    OpenRouterReviewTransport,
    UrllibOpenRouterReviewTransport,
    _extract_review,
    _sample_frames,
)
from .perceptual_review import PerceptualReviewSubmission, PerceptualReviewerKind
from .video_skills import QaDomain

_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_CRITERIA_ID = "ilaios.video.final-brand-integrity"
_CRITERIA_VERSION = "1.0.0"
_RETRYABLE_CAPABILITY_STATUS_CODES = frozenset({404, 503})
_CRITERIA_TEXT = (
    "Judge BRAND integrity only on the sampled frames from the exact final video. "
    "Reject provider watermarks, stock-platform marks, AI/model logos, unexpected "
    "third-party branding, corrupted or deformed logos, inconsistent identity marks, "
    "or branding that contradicts explicit user requirements. Do not infer a pass from "
    "technical playability or visual quality alone. If the objective contains no explicit "
    "brand requirement, require the artifact to remain free of unexpected provider or "
    "platform branding."
)


class OpenRouterBrandPerceptualReviewer:
    """Produce independent BRAND evidence from sampled final-video frames."""

    def __init__(
        self,
        api_key: str,
        model_id: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 90.0,
        threshold: float = 0.90,
        sample_count: int = 4,
        transport: OpenRouterReviewTransport | None = None,
    ) -> None:
        if not api_key or api_key != api_key.strip():
            raise OpenRouterPerceptualReviewError("api_key must be non-blank and trimmed")
        if not model_id or model_id != model_id.strip():
            raise OpenRouterPerceptualReviewError("model_id must be non-blank and trimmed")
        if not base_url or base_url != base_url.strip():
            raise OpenRouterPerceptualReviewError("base_url must be non-blank and trimmed")
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
        return f"openrouter-brand-review:{self._model_id}"

    def review(
        self,
        *,
        video_path: Path,
        objective: str,
        artifact_sha256: str,
        producer_id: str,
        review_id: str,
    ) -> PerceptualReviewSubmission:
        for name, value in (
            ("objective", objective),
            ("producer_id", producer_id),
            ("review_id", review_id),
        ):
            if not value or value != value.strip():
                raise OpenRouterPerceptualReviewError(
                    f"{name} must be non-blank and trimmed"
                )
        if len(artifact_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in artifact_sha256
        ):
            raise OpenRouterPerceptualReviewError(
                "artifact_sha256 must be lowercase SHA-256"
            )
        if self.reviewer_id == producer_id:
            raise OpenRouterPerceptualReviewError(
                "perceptual reviewer must be independent from artifact producer"
            )

        frames = _sample_frames(video_path, self._sample_count)
        frame_refs = tuple(
            f"brand-frame-sha256:{sha256(frame).hexdigest()}" for frame in frames
        )
        content: list[dict[str, object]] = [
            {
                "type": "text",
                "text": (
                    f"{_CRITERIA_TEXT}\n\nUSER OBJECTIVE:\n{objective}\n\n"
                    "Return only JSON with exactly score, detail, repair_target. "
                    "Score from 0 to 1. A passing artifact must satisfy the BRAND criteria."
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
                "name": "ilaios_video_brand_review",
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
                f"OpenRouter brand review failed with HTTP {response.status_code}"
            )
        result = _extract_review(response.payload)
        score = result["score"]
        detail = result["detail"]
        repair_target = result["repair_target"]
        assert isinstance(score, float)
        assert isinstance(detail, str)
        assert isinstance(repair_target, str)
        passed = score >= self._threshold
        return PerceptualReviewSubmission(
            review_id=review_id,
            domain=QaDomain.BRAND,
            artifact_sha256=artifact_sha256,
            reviewer_id=self.reviewer_id,
            producer_id=producer_id,
            reviewer_kind=PerceptualReviewerKind.INDEPENDENT_MODEL,
            criteria_id=_CRITERIA_ID,
            criteria_version=_CRITERIA_VERSION,
            criteria_sha256=sha256(_CRITERIA_TEXT.encode("utf-8")).hexdigest(),
            score=score,
            threshold=self._threshold,
            evidence_references=frame_refs,
            provenance_reference=(
                f"openrouter-brand-review:model={self._model_id}:route={route}:"
                f"artifact={artifact_sha256}"
            ),
            repair_target=None if passed else (repair_target.strip() or "repair-brand-integrity"),
        )
