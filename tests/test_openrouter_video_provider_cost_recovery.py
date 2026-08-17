from __future__ import annotations

import json
from collections.abc import Mapping
from typing import cast

import pytest

from src.video_automation.generation_job_polling import ProviderJobStatus
from src.video_automation.openrouter_video_provider import (
    OpenRouterByteResponse,
    OpenRouterJsonResponse,
    OpenRouterVideoGenerationJobPoller,
    OpenRouterVideoProviderError,
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


def _usage(observation: object) -> dict[str, object]:
    metadata = cast(Mapping[str, str], getattr(observation, "metadata"))
    return cast(dict[str, object], json.loads(metadata["usage_json"]))


def _evidence(observation: object) -> dict[str, object]:
    metadata = cast(Mapping[str, str], getattr(observation, "metadata"))
    return cast(
        dict[str, object],
        json.loads(metadata["provider_cost_evidence_json"]),
    )


def test_terminal_video_poll_accepts_exact_zero_cost_from_poll_usage() -> None:
    transport = _FakeTransport(
        video_payload={
            "status": "completed",
            "generation_id": "gen-poll-zero",
            "usage": {"cost": 0.0, "is_byok": False},
        }
    )
    poller = OpenRouterVideoGenerationJobPoller("test-secret", transport=transport)

    observation = poller.poll("job-poll-zero")

    assert observation.status is ProviderJobStatus.SUCCEEDED
    usage = _usage(observation)
    evidence = _evidence(observation)
    assert usage["cost"] == 0.0
    assert evidence["source"] == "openrouter_video_poll_usage"
    assert evidence["generation_id"] == "gen-poll-zero"
    assert not any("/generation?id=" in url for url in transport.requested_urls)


def test_terminal_video_poll_recovers_exact_zero_when_poll_usage_lacks_cost() -> None:
    transport = _FakeTransport(
        video_payload={
            "status": "completed",
            "generation_id": "gen-123",
            "usage": {"is_byok": False},
        },
        generation_payload={"data": {"total_cost": 0.0}},
    )
    poller = OpenRouterVideoGenerationJobPoller("test-secret", transport=transport)

    observation = poller.poll("job-123")

    assert observation.status is ProviderJobStatus.SUCCEEDED
    usage = _usage(observation)
    evidence = _evidence(observation)
    assert usage["cost"] == 0.0
    assert evidence["source"] == "openrouter_generation_metadata"
    assert evidence["generation_id"] == "gen-123"
    assert any("/generation?id=gen-123" in url for url in transport.requested_urls)


def test_terminal_video_poll_recovers_exact_zero_when_usage_is_missing() -> None:
    transport = _FakeTransport(
        video_payload={"status": "completed", "generation_id": "gen-no-usage"},
        generation_payload={"data": {"usage": 0.0}},
    )
    poller = OpenRouterVideoGenerationJobPoller("test-secret", transport=transport)

    observation = poller.poll("job-no-usage")

    assert observation.status is ProviderJobStatus.SUCCEEDED
    usage = _usage(observation)
    evidence = _evidence(observation)
    assert usage["cost"] == 0.0
    assert evidence["source"] == "openrouter_generation_metadata"


def test_terminal_video_poll_rejects_nonzero_authoritative_cost() -> None:
    transport = _FakeTransport(
        video_payload={
            "status": "completed",
            "generation_id": "gen-paid",
            "usage": {"cost": 0.125},
        }
    )
    poller = OpenRouterVideoGenerationJobPoller("test-secret", transport=transport)

    with pytest.raises(OpenRouterVideoProviderError, match="PROVIDER_COST_NONZERO"):
        poller.poll("job-paid")


def test_terminal_video_poll_rejects_missing_cost_without_generation_id() -> None:
    transport = _FakeTransport(
        video_payload={"status": "completed", "usage": {"is_byok": False}}
    )
    poller = OpenRouterVideoGenerationJobPoller("test-secret", transport=transport)

    with pytest.raises(OpenRouterVideoProviderError, match="ZERO_COST_EVIDENCE_UNKNOWN"):
        poller.poll("job-missing")


def test_terminal_video_poll_rejects_malformed_cost_when_accounting_is_unusable() -> None:
    transport = _FakeTransport(
        video_payload={
            "status": "completed",
            "generation_id": "gen-malformed",
            "usage": {"cost": {"unexpected": True}},
        },
        generation_payload={"data": {"model": "free-model"}},
    )
    poller = OpenRouterVideoGenerationJobPoller("test-secret", transport=transport)

    with pytest.raises(OpenRouterVideoProviderError, match="ZERO_COST_EVIDENCE_UNKNOWN"):
        poller.poll("job-malformed")


def test_terminal_video_poll_rejects_unavailable_accounting_endpoint() -> None:
    transport = _FakeTransport(
        video_payload={
            "status": "completed",
            "generation_id": "gen-http-failure",
        },
        generation_payload={"error": {"message": "not available"}},
        generation_status=404,
    )
    poller = OpenRouterVideoGenerationJobPoller("test-secret", transport=transport)

    with pytest.raises(OpenRouterVideoProviderError, match="PROVIDER_USAGE_UNAVAILABLE"):
        poller.poll("job-http-failure")


def test_terminal_evidence_sanitizes_secret_like_response_fields() -> None:
    transport = _FakeTransport(
        video_payload={
            "status": "completed",
            "generation_id": "gen-redacted",
            "usage": {"cost": 0},
            "api_key": "credential-should-never-persist",
            "nested": {"Authorization": "Bearer should-never-persist"},
        }
    )
    poller = OpenRouterVideoGenerationJobPoller("test-secret", transport=transport)

    observation = poller.poll("job-redacted")

    serialized = observation.metadata["terminal_response_json"]
    assert "credential-should-never-persist" not in serialized
    assert "Bearer should-never-persist" not in serialized
    assert serialized.count("[REDACTED]") == 2
    evidence = poller.terminal_evidence["job-redacted"]
    assert evidence["cost"] == 0.0
