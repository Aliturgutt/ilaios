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


class _CapabilityFallbackTransport:
    def __init__(self, fallback_status: int = 200) -> None:
        self.requests: list[Mapping[str, object]] = []
        self._fallback_status = fallback_status

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
        if len(self.requests) == 1:
            return OpenRouterReviewResponse(404, {"error": {"message": "no endpoints found"}})
        return OpenRouterReviewResponse(
            self._fallback_status,
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"visual_brief":"Fallback preserved the reference appearance."}'
                        }
                    }
                ]
            }
            if self._fallback_status == 200
            else {"error": {"message": "no compatible free vision endpoint"}},
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


def test_reference_analyzer_retries_404_without_schema_on_same_free_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.video_automation.reference_image_analysis._downscale_to_jpeg",
        lambda content: b"normalized-jpeg-" + content,
    )
    transport = _CapabilityFallbackTransport()
    analyzer = OpenRouterReferenceImageAnalyzer(
        "secret",
        "openrouter/free",
        transport=transport,
    )

    brief = analyzer.analyze((_reference(1), _reference(2)))

    assert brief.text == "Fallback preserved the reference appearance."
    assert len(transport.requests) == 2
    strict_request, fallback_request = transport.requests
    assert strict_request["model"] == "openrouter/free"
    assert fallback_request["model"] == "openrouter/free"
    assert "response_format" in strict_request
    assert "response_format" not in fallback_request
    assert fallback_request["provider"] == {"require_parameters": True}
    assert fallback_request["messages"] == strict_request["messages"]


def test_reference_analyzer_fallback_remains_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.video_automation.reference_image_analysis._downscale_to_jpeg",
        lambda content: b"normalized-jpeg-" + content,
    )
    transport = _CapabilityFallbackTransport(fallback_status=404)
    analyzer = OpenRouterReferenceImageAnalyzer(
        "secret",
        "openrouter/free",
        transport=transport,
    )

    with pytest.raises(ReferenceImageAnalysisError, match="HTTP 404"):
        analyzer.analyze((_reference(1),))

    assert len(transport.requests) == 2
    assert all(request["model"] == "openrouter/free" for request in transport.requests)


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
