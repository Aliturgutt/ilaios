from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

import pytest

from src.video_automation.openrouter_perceptual_reviewer import OpenRouterReviewResponse
from src.video_automation.reference_image_analysis import (
    OpenRouterReferenceImageAnalyzer,
    ReferenceImageAnalysisError,
    ReferenceImageInput,
)


class _Transport:
    def __init__(self) -> None:
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
        return OpenRouterReviewResponse(
            200,
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"visual_brief":"Preserve the observed subject, product geometry, palette, and lighting."}'
                        }
                    }
                ]
            },
        )


def _reference(index: int) -> ReferenceImageInput:
    content = f"image-{index}".encode()
    return ReferenceImageInput(
        content=content,
        mime_type="image/png",
        sha256_hex=hashlib.sha256(content).hexdigest(),
        role="style",
        instruction=f"reference {index}",
    )


def test_reference_analyzer_batches_private_images_and_preserves_digest_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.video_automation.reference_image_analysis._downscale_to_jpeg",
        lambda content: b"normalized-jpeg-" + content,
    )
    transport = _Transport()
    analyzer = OpenRouterReferenceImageAnalyzer(
        "secret",
        "openrouter/free",
        transport=transport,
    )
    references = tuple(_reference(index) for index in range(6))

    brief = analyzer.analyze(references)

    assert len(transport.requests) == 2
    assert brief.reference_sha256s == tuple(item.sha256_hex for item in references)
    assert "Preserve the observed subject" in brief.text
    assert brief.analyzer_id == "openrouter-reference-analysis:openrouter/free"
    outbound = json.dumps(transport.requests, sort_keys=True)
    for reference in references:
        assert reference.sha256_hex not in outbound


def test_reference_analyzer_rejects_more_than_twenty_images() -> None:
    analyzer = OpenRouterReferenceImageAnalyzer(
        "secret",
        "openrouter/free",
        transport=_Transport(),
    )
    with pytest.raises(ReferenceImageAnalysisError, match="at most 20"):
        analyzer.analyze(tuple(_reference(index) for index in range(21)))


def test_reference_analyzer_rejects_duplicate_image_digests() -> None:
    analyzer = OpenRouterReferenceImageAnalyzer(
        "secret",
        "openrouter/free",
        transport=_Transport(),
    )
    reference = _reference(1)
    with pytest.raises(ReferenceImageAnalysisError, match="duplicate"):
        analyzer.analyze((reference, reference))


def test_reference_analyzer_rejects_billable_model_ids() -> None:
    with pytest.raises(ReferenceImageAnalysisError, match="explicitly free"):
        OpenRouterReferenceImageAnalyzer(
            "secret",
            "vendor/paid-vision-model",
            transport=_Transport(),
        )

    analyzer = OpenRouterReferenceImageAnalyzer(
        "secret",
        "vendor/vision-model:free",
        transport=_Transport(),
    )
    assert analyzer.analyzer_id.endswith(":free")
