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


class _SubmissionTransport(OpenRouterTransport):
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.post_timeouts: list[float] = []
        self.catalog_timeouts: list[float] = []

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        del url, headers, body
        self.post_timeouts.append(timeout_seconds)
        if self.failure is not None:
            raise self.failure
        return OpenRouterJsonResponse(
            202,
            {"id": "job-timeout-test", "status": "pending"},
        )

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        del headers
        if url.endswith("/videos/models"):
            self.catalog_timeouts.append(timeout_seconds)
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
        raise AssertionError("submission timeout test must not poll")

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        del url, headers, timeout_seconds
        raise AssertionError("submission timeout test must not retrieve media")


def _request() -> ProviderRequest:
    item = {
        "sequence_number": 1,
        "request_id": "request-timeout-test",
        "idempotency_key": "a" * 64,
        "shot_id": "shot-timeout-test",
        "prompt_text": "cinematic rain over a futuristic coastal city",
        "duration_seconds": 4,
        "aspect_ratio": "16:9",
        "frames_per_second": 24,
        "output_count": 1,
        "seed": None,
        "resolution": "480p",
    }
    return ProviderRequest(
        request_id="dispatch-timeout-test",
        job_id="plan-timeout-test",
        provider_name="openrouter-video-free",
        operation="video.generate",
        payload={
            "model_id": SEEDANCE_FREE_MODEL_ID,
            "request_count": 1,
            "items_json": json.dumps(
                [item],
                sort_keys=True,
                separators=(",", ":"),
            ),
        },
    )


def test_default_submission_timeout_allows_slow_async_acknowledgement() -> None:
    transport = _SubmissionTransport()

    result = OpenRouterVideoGenerationProvider(
        "test-secret",
        transport=transport,
    ).execute(_request())

    assert result.success
    assert transport.catalog_timeouts == [120.0]
    assert transport.post_timeouts == [120.0]


def test_explicit_submission_timeout_is_preserved() -> None:
    transport = _SubmissionTransport()

    result = OpenRouterVideoGenerationProvider(
        "test-secret",
        timeout_seconds=75.0,
        transport=transport,
    ).execute(_request())

    assert result.success
    assert transport.catalog_timeouts == [75.0]
    assert transport.post_timeouts == [75.0]


def test_direct_read_timeout_fails_closed_without_automatic_resubmission() -> None:
    transport = _SubmissionTransport(TimeoutError("The read operation timed out"))

    result = OpenRouterVideoGenerationProvider(
        "test-secret",
        transport=transport,
    ).execute(_request())

    assert not result.success
    assert result.error_code == "submission_timeout_uncertain"
    assert "120s" in (result.error_message or "")
    assert "automatic resubmission is forbidden" in (result.error_message or "")
    assert "test-secret" not in str(result)
    assert transport.catalog_timeouts == [120.0]
    assert transport.post_timeouts == [120.0]


def test_wrapped_transport_timeout_uses_same_fail_closed_diagnostic() -> None:
    transport = _SubmissionTransport(
        OpenRouterVideoProviderError(
            "OpenRouter transport error: The read operation timed out"
        )
    )

    result = OpenRouterVideoGenerationProvider(
        "test-secret",
        transport=transport,
    ).execute(_request())

    assert not result.success
    assert result.error_code == "submission_timeout_uncertain"
    assert "automatic resubmission is forbidden" in (result.error_message or "")
    assert "test-secret" not in str(result)
    assert transport.catalog_timeouts == [120.0]
    assert transport.post_timeouts == [120.0]
