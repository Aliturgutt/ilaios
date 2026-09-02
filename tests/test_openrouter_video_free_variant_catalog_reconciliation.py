from __future__ import annotations

from collections.abc import Mapping

from src.video_automation.free_provider_production_certification import (
    build_free_certification_request,
)
from src.video_automation.openrouter_video_provider import (
    SEEDANCE_FREE_MODEL_ID,
    OpenRouterByteResponse,
    OpenRouterJsonResponse,
    OpenRouterTransport,
    OpenRouterVideoGenerationProvider,
)


class _VariantCatalogTransport(OpenRouterTransport):
    def __init__(self, *, variant_price: str = "0") -> None:
        self.variant_price = variant_price
        self.post_calls: list[Mapping[str, object]] = []
        self.get_urls: list[str] = []

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        del url, headers, timeout_seconds
        self.post_calls.append(body)
        return OpenRouterJsonResponse(202, {"id": "job-free-variant", "status": "pending"})

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        del headers, timeout_seconds
        self.get_urls.append(url)
        if url.endswith("/videos/models"):
            return OpenRouterJsonResponse(
                200,
                {
                    "data": [
                        {
                            "id": "bytedance/seedance-2.0-fast",
                            "pricing_skus": {"per-video-second": "0.04035"},
                        }
                    ]
                },
            )
        if url.endswith("/model/bytedance/seedance-2.0-fast%3Afree"):
            return OpenRouterJsonResponse(
                200,
                {
                    "data": {
                        "id": SEEDANCE_FREE_MODEL_ID,
                        "pricing": {
                            "prompt": self.variant_price,
                            "completion": self.variant_price,
                            "request": self.variant_price,
                        },
                    }
                },
            )
        raise AssertionError(f"unexpected GET {url}")

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        raise AssertionError("content retrieval is not part of submission preflight")


def _request():
    return build_free_certification_request(
        model_id=SEEDANCE_FREE_MODEL_ID,
        run_id="variant-catalog",
        run_attempt="1",
        candidate_index=1,
    )


def test_free_variant_uses_base_video_capability_and_exact_zero_price_variant() -> None:
    transport = _VariantCatalogTransport()
    result = OpenRouterVideoGenerationProvider(
        "test-secret",
        transport=transport,
    ).execute(_request())

    assert result.success is True
    assert result.external_id == "job-free-variant"
    assert result.metadata["catalog_zero_cost_evidence_source"] == (
        "openrouter_model_variant+videos_models"
    )
    assert len(transport.post_calls) == 1
    assert transport.post_calls[0]["model"] == SEEDANCE_FREE_MODEL_ID


def test_nonzero_exact_variant_price_fails_before_video_post() -> None:
    transport = _VariantCatalogTransport(variant_price="0.01")
    result = OpenRouterVideoGenerationProvider(
        "test-secret",
        transport=transport,
    ).execute(_request())

    assert result.success is False
    assert result.error_code == "FREE_VIDEO_PRICING_NONZERO"
    assert transport.post_calls == []
