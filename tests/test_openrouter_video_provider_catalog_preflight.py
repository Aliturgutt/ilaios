from __future__ import annotations

import json
from collections.abc import Mapping

from src.video_automation.models import ProviderRequest
from src.video_automation.openrouter_video_provider import (
    SEEDANCE_FREE_MODEL_ID,
    OpenRouterByteResponse,
    OpenRouterJsonResponse,
    OpenRouterTransport,
    OpenRouterVideoGenerationProvider,
    OpenRouterVideoProviderError,
)


class _CatalogTransport(OpenRouterTransport):
    def __init__(
        self,
        *,
        catalog_payload: Mapping[str, object],
        catalog_status: int = 200,
        catalog_failure: Exception | None = None,
    ) -> None:
        self.catalog_payload = catalog_payload
        self.catalog_status = catalog_status
        self.catalog_failure = catalog_failure
        self.post_count = 0
        self.catalog_count = 0

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        del url, headers, body, timeout_seconds
        self.post_count += 1
        return OpenRouterJsonResponse(
            202,
            {
                "id": "job-catalog-test",
                "status": "pending",
                "generation_id": "gen-catalog-test",
            },
        )

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        del headers, timeout_seconds
        if not url.endswith("/videos/models"):
            raise AssertionError(f"unexpected GET: {url}")
        self.catalog_count += 1
        if self.catalog_failure is not None:
            raise self.catalog_failure
        return OpenRouterJsonResponse(self.catalog_status, self.catalog_payload)

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        del url, headers, timeout_seconds
        raise AssertionError("catalog preflight test must not retrieve media")


def _request(model_id: str = SEEDANCE_FREE_MODEL_ID) -> ProviderRequest:
    item = {
        "sequence_number": 1,
        "request_id": "request-catalog-test",
        "idempotency_key": "b" * 64,
        "shot_id": "shot-catalog-test",
        "prompt_text": "cinematic futuristic city in rain",
        "duration_seconds": 4,
        "aspect_ratio": "16:9",
        "frames_per_second": 24,
        "output_count": 1,
        "seed": None,
        "resolution": "480p",
    }
    return ProviderRequest(
        request_id="dispatch-catalog-test",
        job_id="plan-catalog-test",
        provider_name="openrouter-video-free",
        operation="video.generate",
        payload={
            "model_id": model_id,
            "request_count": 1,
            "items_json": json.dumps([item], sort_keys=True, separators=(",", ":")),
        },
    )


def _catalog_entry(
    model_id: str = SEEDANCE_FREE_MODEL_ID,
    pricing_skus: object = None,
) -> dict[str, object]:
    if pricing_skus is None:
        pricing_skus = {"per-video-second": "0"}
    return {"id": model_id, "pricing_skus": pricing_skus}


def test_exact_catalog_model_with_explicit_zero_price_allows_post() -> None:
    transport = _CatalogTransport(
        catalog_payload={"data": [_catalog_entry()]},
    )

    result = OpenRouterVideoGenerationProvider(
        "test-secret",
        transport=transport,
    ).execute(_request())

    assert result.success
    assert transport.catalog_count == 1
    assert transport.post_count == 1
    assert result.metadata["catalog_zero_cost"] is True
    assert result.metadata["catalog_zero_cost_evidence_source"] == "openrouter_videos_models"
    assert "test-secret" not in str(result)


def test_base_paid_model_does_not_satisfy_exact_free_alias() -> None:
    transport = _CatalogTransport(
        catalog_payload={
            "data": [
                _catalog_entry(
                    model_id="bytedance/seedance-2.0-fast",
                    pricing_skus={"per-video-second": "0.05"},
                )
            ]
        },
    )

    result = OpenRouterVideoGenerationProvider(
        "test-secret",
        transport=transport,
    ).execute(_request())

    assert not result.success
    assert result.error_code == "FREE_VIDEO_VARIANT_UNAVAILABLE"
    assert transport.post_count == 0
    assert "test-secret" not in str(result)


def _assert_nonzero_price_blocks(price: object) -> None:
    transport = _CatalogTransport(
        catalog_payload={
            "data": [_catalog_entry(pricing_skus={"per-video-second": price})]
        },
    )

    result = OpenRouterVideoGenerationProvider(
        "test-secret",
        transport=transport,
    ).execute(_request())

    assert not result.success
    assert result.error_code == "FREE_VIDEO_PRICING_NONZERO"
    assert transport.post_count == 0


def test_nonzero_string_catalog_price_blocks_before_post() -> None:
    _assert_nonzero_price_blocks("0.05")


def test_nonzero_float_catalog_price_blocks_before_post() -> None:
    _assert_nonzero_price_blocks(0.01)


def test_observed_provider_cost_catalog_price_blocks_before_post() -> None:
    _assert_nonzero_price_blocks("0.1704948")


def _assert_malformed_pricing_blocks(pricing_skus: object) -> None:
    entry: dict[str, object] = {"id": SEEDANCE_FREE_MODEL_ID}
    if pricing_skus is not None:
        entry["pricing_skus"] = pricing_skus
    transport = _CatalogTransport(catalog_payload={"data": [entry]})

    result = OpenRouterVideoGenerationProvider(
        "test-secret",
        transport=transport,
    ).execute(_request())

    assert not result.success
    assert result.error_code == "FREE_VIDEO_PRICING_UNKNOWN"
    assert transport.post_count == 0


def test_empty_catalog_pricing_blocks_before_post() -> None:
    _assert_malformed_pricing_blocks({})


def test_missing_catalog_pricing_blocks_before_post() -> None:
    _assert_malformed_pricing_blocks(None)


def test_list_catalog_pricing_blocks_before_post() -> None:
    _assert_malformed_pricing_blocks([])


def test_unknown_catalog_pricing_blocks_before_post() -> None:
    _assert_malformed_pricing_blocks({"per-video-second": "unknown"})


def test_null_catalog_pricing_blocks_before_post() -> None:
    _assert_malformed_pricing_blocks({"per-video-second": None})


def test_negative_catalog_pricing_blocks_before_post() -> None:
    _assert_malformed_pricing_blocks({"per-video-second": -1})


def test_catalog_http_failure_blocks_before_post() -> None:
    transport = _CatalogTransport(
        catalog_status=503,
        catalog_payload={"error": {"message": "unavailable"}},
    )

    result = OpenRouterVideoGenerationProvider(
        "test-secret",
        transport=transport,
    ).execute(_request())

    assert not result.success
    assert result.error_code == "FREE_VIDEO_CATALOG_UNAVAILABLE"
    assert transport.post_count == 0


def test_catalog_transport_failure_blocks_before_post_without_secret_leak() -> None:
    transport = _CatalogTransport(
        catalog_payload={},
        catalog_failure=OpenRouterVideoProviderError(
            "OpenRouter transport error: read timed out"
        ),
    )

    result = OpenRouterVideoGenerationProvider(
        "test-secret",
        transport=transport,
    ).execute(_request())

    assert not result.success
    assert result.error_code == "FREE_VIDEO_CATALOG_UNAVAILABLE"
    assert transport.post_count == 0
    assert "test-secret" not in str(result)


def test_paid_model_is_rejected_before_catalog_lookup() -> None:
    transport = _CatalogTransport(catalog_payload={"data": []})

    result = OpenRouterVideoGenerationProvider(
        "test-secret",
        transport=transport,
    ).execute(_request("bytedance/seedance-2.0-fast"))

    assert not result.success
    assert result.error_code == "invalid_request"
    assert transport.catalog_count == 0
    assert transport.post_count == 0
