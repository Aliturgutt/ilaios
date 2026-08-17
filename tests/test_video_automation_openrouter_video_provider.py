from __future__ import annotations

import json
from collections.abc import Mapping

import pytest

from src.video_automation.generation_job_polling import ProviderJobStatus
from src.video_automation.models import ProviderRequest
from src.video_automation.openrouter_video_provider import (
    SEEDANCE_FREE_MODEL_ID,
    OpenRouterByteResponse,
    OpenRouterGeneratedAssetRetriever,
    OpenRouterJsonResponse,
    OpenRouterTransport,
    OpenRouterVideoGenerationJobPoller,
    OpenRouterVideoGenerationProvider,
    OpenRouterVideoProviderError,
)


class _Transport(OpenRouterTransport):
    def __init__(
        self,
        *,
        post_response: OpenRouterJsonResponse | None = None,
        get_response: OpenRouterJsonResponse | None = None,
        byte_response: OpenRouterByteResponse | None = None,
    ) -> None:
        self.post_response = post_response or OpenRouterJsonResponse(
            202,
            {"id": "job-001", "status": "pending"},
        )
        self.get_response = get_response or OpenRouterJsonResponse(
            200,
            {"id": "job-001", "status": "completed"},
        )
        self.byte_response = byte_response or OpenRouterByteResponse(
            200,
            b"mp4-bytes",
            "video/mp4",
            "https://openrouter.ai/api/v1/videos/job-001/content",
        )
        self.post_calls: list[
            tuple[str, Mapping[str, str], Mapping[str, object], float]
        ] = []
        self.get_calls: list[tuple[str, Mapping[str, str], float]] = []
        self.byte_calls: list[tuple[str, Mapping[str, str], float]] = []

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        self.post_calls.append((url, headers, body, timeout_seconds))
        return self.post_response

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        self.get_calls.append((url, headers, timeout_seconds))
        if url.endswith("/videos/models"):
            return OpenRouterJsonResponse(
                200,
                {
                    "data": [
                        {
                            "id": SEEDANCE_FREE_MODEL_ID,
                            "pricing_skus": {"per-video-second": "0"},
                        }
                    ]
                },
            )
        return self.get_response

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        self.byte_calls.append((url, headers, timeout_seconds))
        return self.byte_response


def _request(
    *,
    provider_name: str = "openrouter-video-free",
    operation: str = "video.generate",
    model_id: str = SEEDANCE_FREE_MODEL_ID,
    duration_seconds: float = 4.0,
    resolution: str | None = None,
    output_count: int = 1,
) -> ProviderRequest:
    item: dict[str, object] = {
        "sequence_number": 1,
        "request_id": "request-01",
        "idempotency_key": "a" * 64,
        "shot_id": "shot-01",
        "prompt_text": "cinematic graphite geometry with cyan light",
        "duration_seconds": duration_seconds,
        "aspect_ratio": "16:9",
        "frames_per_second": 24,
        "output_count": output_count,
        "seed": None,
    }
    if resolution is not None:
        item["resolution"] = resolution
    return ProviderRequest(
        request_id="dispatch-001",
        job_id="dispatch-plan-001",
        provider_name=provider_name,
        operation=operation,
        payload={
            "model_id": model_id,
            "batch_id": "batch-001",
            "batch_number": 1,
            "max_parallel_requests": 1,
            "request_count": 1,
            "items_json": json.dumps(
                [item],
                sort_keys=True,
                separators=(",", ":"),
            ),
        },
    )


def test_capabilities_are_explicitly_free_only() -> None:
    provider = OpenRouterVideoGenerationProvider("secret", transport=_Transport())
    assert provider.capabilities.provider_name == "openrouter-video-free"
    assert provider.capabilities.operations == ("video.generate",)
    assert not provider.capabilities.is_paid
    assert provider.capabilities.metadata["backend"] == "openrouter"
    assert provider.capabilities.metadata["cost_policy"] == "free_only"


def test_submit_uses_official_video_endpoint_and_bearer_auth() -> None:
    transport = _Transport()
    result = OpenRouterVideoGenerationProvider(
        "secret",
        transport=transport,
    ).execute(_request())
    assert result.success
    url, headers, _, timeout = transport.post_calls[0]
    assert url == "https://openrouter.ai/api/v1/videos"
    assert headers["Authorization"] == "Bearer secret"
    assert headers["Content-Type"] == "application/json"
    assert timeout > 0
    assert "secret" not in str(result.metadata)


def test_submit_maps_seedance_free_request_with_free_only_policy() -> None:
    transport = _Transport()
    result = OpenRouterVideoGenerationProvider("secret", transport=transport).execute(
        _request()
    )
    assert result.success
    body = transport.post_calls[0][2]
    assert body == {
        "model": "bytedance/seedance-2.0-fast:free",
        "prompt": "cinematic graphite geometry with cyan light",
        "aspect_ratio": "16:9",
        "duration": 4,
        "resolution": "480p",
        "generate_audio": False,
    }
    assert result.metadata["cost_policy"] == "free_only"
    assert result.metadata["model_id"] == SEEDANCE_FREE_MODEL_ID


def test_paid_seedance_model_is_rejected_before_network() -> None:
    transport = _Transport()
    result = OpenRouterVideoGenerationProvider("secret", transport=transport).execute(
        _request(model_id="bytedance/seedance-2.0-fast")
    )
    assert not result.success
    assert result.error_code == "invalid_request"
    assert ":free" in (result.error_message or "")
    assert transport.post_calls == []


def test_any_nonfree_model_is_rejected_before_network() -> None:
    transport = _Transport()
    result = OpenRouterVideoGenerationProvider("secret", transport=transport).execute(
        _request(model_id="provider/video-model")
    )
    assert not result.success
    assert result.error_code == "invalid_request"
    assert "paid or unpriced model IDs are forbidden" in (result.error_message or "")
    assert transport.post_calls == []


def test_submit_respects_explicit_resolution_and_audio_policy() -> None:
    transport = _Transport()
    OpenRouterVideoGenerationProvider(
        "secret",
        default_resolution="720p",
        generate_audio=True,
        transport=transport,
    ).execute(_request(resolution="720p"))
    body = transport.post_calls[0][2]
    assert body["resolution"] == "720p"
    assert body["generate_audio"] is True


def test_submit_returns_openrouter_job_id() -> None:
    result = OpenRouterVideoGenerationProvider(
        "secret",
        transport=_Transport(
            post_response=OpenRouterJsonResponse(
                202,
                {
                    "id": "job-real-shaped",
                    "status": "pending",
                    "generation_id": "gen-001",
                },
            )
        ),
    ).execute(_request())
    assert result.success
    assert result.external_id == "job-real-shaped"
    assert result.metadata["generation_id"] == "gen-001"


def test_submit_normalizes_provider_error_without_leaking_key() -> None:
    result = OpenRouterVideoGenerationProvider(
        "secret",
        transport=_Transport(
            post_response=OpenRouterJsonResponse(
                429,
                {"error": {"code": 429, "message": "Free model rate limited"}},
            )
        ),
    ).execute(_request())
    assert not result.success
    assert result.error_code == "429"
    assert result.error_message == "Free model rate limited"
    assert "secret" not in str(result)


def test_submit_rejects_fractional_duration_before_network() -> None:
    transport = _Transport()
    result = OpenRouterVideoGenerationProvider("secret", transport=transport).execute(
        _request(duration_seconds=4.5)
    )
    assert not result.success
    assert result.error_code == "invalid_request"
    assert "whole number" in (result.error_message or "")
    assert transport.post_calls == []


def test_submit_rejects_provider_mismatch_and_multiple_outputs() -> None:
    provider = OpenRouterVideoGenerationProvider("secret", transport=_Transport())
    mismatch = provider.execute(_request(provider_name="openrouter-video"))
    assert not mismatch.success
    assert mismatch.error_code == "invalid_request"
    outputs = provider.execute(_request(output_count=2))
    assert not outputs.success
    assert "output_count=1" in (outputs.error_message or "")


def test_poller_maps_pending_and_completed_states() -> None:
    pending_transport = _Transport(
        get_response=OpenRouterJsonResponse(
            200,
            {"id": "job-001", "status": "pending"},
        )
    )
    pending = OpenRouterVideoGenerationJobPoller(
        "secret",
        transport=pending_transport,
    ).poll("job-001")
    assert pending.status is ProviderJobStatus.QUEUED
    assert pending.output_asset_ids == ()

    completed_transport = _Transport(
        get_response=OpenRouterJsonResponse(
            200,
            {
                "id": "job-001",
                "status": "completed",
                "generation_id": "gen-001",
                "usage": {"cost": 0},
            },
        )
    )
    completed = OpenRouterVideoGenerationJobPoller(
        "secret",
        transport=completed_transport,
    ).poll("job-001")
    assert completed.status is ProviderJobStatus.SUCCEEDED
    assert completed.output_asset_ids == (
        "https://openrouter.ai/api/v1/videos/job-001/content",
    )
    assert completed.metadata["generation_id"] == "gen-001"
    assert completed.metadata["usage_json"] == '{"cost":0}'


def test_poller_maps_failure_and_rejects_unknown_status() -> None:
    failed = OpenRouterVideoGenerationJobPoller(
        "secret",
        transport=_Transport(
            get_response=OpenRouterJsonResponse(
                200,
                {
                    "id": "job-001",
                    "status": "failed",
                    "error": {
                        "code": "free_capacity_unavailable",
                        "message": "generation failed",
                    },
                },
            )
        ),
    ).poll("job-001")
    assert failed.status is ProviderJobStatus.FAILED
    assert failed.error_code == "free_capacity_unavailable"
    assert failed.error_message == "generation failed"

    with pytest.raises(OpenRouterVideoProviderError, match="unsupported OpenRouter"):
        OpenRouterVideoGenerationJobPoller(
            "secret",
            transport=_Transport(
                get_response=OpenRouterJsonResponse(
                    200,
                    {"id": "job-001", "status": "mystery"},
                )
            ),
        ).poll("job-001")


def test_asset_retriever_uses_authenticated_content_endpoint() -> None:
    transport = _Transport()
    retriever = OpenRouterGeneratedAssetRetriever("secret", transport=transport)
    payload = retriever.retrieve(
        "https://openrouter.ai/api/v1/videos/job-001/content"
    )
    assert payload.body == b"mp4-bytes"
    assert payload.content_type == "video/mp4"
    assert payload.file_extension == ".mp4"
    url, headers, timeout = transport.byte_calls[0]
    assert url.endswith("/videos/job-001/content")
    assert headers["Authorization"] == "Bearer secret"
    assert timeout > 0


def test_asset_retriever_rejects_noncanonical_url_and_wrong_media_type() -> None:
    retriever = OpenRouterGeneratedAssetRetriever("secret", transport=_Transport())
    with pytest.raises(OpenRouterVideoProviderError, match="canonical HTTPS"):
        retriever.retrieve("https://example.test/video.mp4")

    with pytest.raises(OpenRouterVideoProviderError, match="content type"):
        OpenRouterGeneratedAssetRetriever(
            "secret",
            transport=_Transport(
                byte_response=OpenRouterByteResponse(
                    200,
                    b"not-video",
                    "application/octet-stream",
                    "https://openrouter.ai/api/v1/videos/job-001/content",
                )
            ),
        ).retrieve("https://openrouter.ai/api/v1/videos/job-001/content")


def test_invalid_constructor_values_fail_closed() -> None:
    with pytest.raises(OpenRouterVideoProviderError, match="api_key"):
        OpenRouterVideoGenerationProvider(" ")
    with pytest.raises(OpenRouterVideoProviderError, match="timeout_seconds"):
        OpenRouterVideoGenerationJobPoller("key", timeout_seconds=0)
