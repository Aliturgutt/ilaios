from __future__ import annotations

import json
from collections.abc import Mapping
from typing import cast

from src.video_automation.generation_job_polling import ProviderJobStatus
from src.video_automation.openrouter_video_provider import (
    OpenRouterByteResponse,
    OpenRouterJsonResponse,
    OpenRouterVideoGenerationJobPoller,
)


class _FakeTransport:
    def __init__(
        self,
        *,
        video_payload: Mapping[str, object],
        generation_payload: Mapping[str, object] | None = None,
        generation_status: int = 200,
    ) -> None:
        self._video_payload = video_payload
        self._generation_payload = generation_payload or {}
        self._generation_status = generation_status
        self.requested_urls: list[str] = []

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        del url, headers, body, timeout_seconds
        raise AssertionError("polling test must not submit provider work")

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        del headers, timeout_seconds
        self.requested_urls.append(url)
        if "/generation?id=" in url:
            return OpenRouterJsonResponse(
                self._generation_status,
                self._generation_payload,
            )
        if "/videos/" in url:
            return OpenRouterJsonResponse(200, self._video_payload)
        raise AssertionError(f"unexpected URL: {url}")

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        del url, headers, timeout_seconds
        raise AssertionError("polling test must not retrieve media bytes")


def test_terminal_video_poll_recovers_exact_zero_cost_from_generation_metadata() -> None:
    transport = _FakeTransport(
        video_payload={
            "status": "completed",
            "generation_id": "gen-123",
        },
        generation_payload={
            "data": {
                "total_cost": 0.0,
            }
        },
    )
    poller = OpenRouterVideoGenerationJobPoller(
        "test-secret",
        transport=transport,
    )

    observation = poller.poll("job-123")

    assert observation.status is ProviderJobStatus.SUCCEEDED
    usage = cast(dict[str, object], json.loads(observation.metadata["usage_json"]))
    assert usage["cost"] == 0.0
    assert usage["source"] == "openrouter_generation_metadata"
    assert usage["generation_id"] == "gen-123"
    assert any("/generation?id=gen-123" in url for url in transport.requested_urls)


def test_terminal_video_poll_preserves_fail_closed_state_without_cost_metadata() -> None:
    transport = _FakeTransport(
        video_payload={
            "status": "completed",
            "generation_id": "gen-missing-cost",
        },
        generation_payload={"data": {"model": "free-model"}},
    )
    poller = OpenRouterVideoGenerationJobPoller(
        "test-secret",
        transport=transport,
    )

    observation = poller.poll("job-456")

    assert observation.status is ProviderJobStatus.SUCCEEDED
    assert "usage_json" not in observation.metadata


def test_terminal_video_poll_does_not_fabricate_cost_when_metadata_request_fails() -> None:
    transport = _FakeTransport(
        video_payload={
            "status": "completed",
            "generation_id": "gen-http-failure",
        },
        generation_payload={"error": {"message": "not available"}},
        generation_status=404,
    )
    poller = OpenRouterVideoGenerationJobPoller(
        "test-secret",
        transport=transport,
    )

    observation = poller.poll("job-789")

    assert observation.status is ProviderJobStatus.SUCCEEDED
    assert "usage_json" not in observation.metadata
