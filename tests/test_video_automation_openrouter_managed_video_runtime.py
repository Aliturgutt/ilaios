from __future__ import annotations

from collections.abc import Mapping

import pytest

from src.video_automation.generation_job_polling import ProviderJobStatus
from src.video_automation.openrouter_managed_video_runtime import (
    OpenRouterManagedVideoGenerationJobPoller,
    OpenRouterManagedVideoRuntimeError,
    actual_cost_microusd_from_observation,
)
from src.video_automation.openrouter_video_provider import (
    OpenRouterByteResponse,
    OpenRouterJsonResponse,
    OpenRouterTransport,
)


class _Transport(OpenRouterTransport):
    def __init__(self, response: OpenRouterJsonResponse) -> None:
        self.response = response
        self.get_calls: list[tuple[str, Mapping[str, str], float]] = []

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        raise AssertionError("submission is outside polling test scope")

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        self.get_calls.append((url, headers, timeout_seconds))
        return self.response

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        raise AssertionError("retrieval is outside polling test scope")


class _SequenceTransport(OpenRouterTransport):
    def __init__(self, responses: tuple[OpenRouterJsonResponse, ...]) -> None:
        self.responses = list(responses)
        self.get_calls: list[tuple[str, Mapping[str, str], float]] = []

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        raise AssertionError("submission is outside polling test scope")

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        self.get_calls.append((url, headers, timeout_seconds))
        if not self.responses:
            raise AssertionError("unexpected extra provider metadata request")
        return self.responses.pop(0)

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        raise AssertionError("retrieval is outside polling test scope")


def test_openrouter_in_progress_status_is_normalized_to_running() -> None:
    poller = OpenRouterManagedVideoGenerationJobPoller(
        "server-secret",
        transport=_Transport(
            OpenRouterJsonResponse(
                200,
                {"id": "job-001", "status": "in_progress"},
            )
        ),
    )
    observation = poller.poll("job-001")
    assert observation.status is ProviderJobStatus.RUNNING


def test_completed_observation_binds_content_url_and_provider_usage_cost() -> None:
    poller = OpenRouterManagedVideoGenerationJobPoller(
        "server-secret",
        transport=_Transport(
            OpenRouterJsonResponse(
                200,
                {
                    "id": "job-001",
                    "status": "completed",
                    "generation_id": "generation-001",
                    "usage": {"cost": 0.484},
                },
            )
        ),
    )
    observation = poller.poll("job-001")
    assert observation.status is ProviderJobStatus.SUCCEEDED
    assert observation.output_asset_ids == (
        "https://openrouter.ai/api/v1/videos/job-001/content",
    )
    assert observation.metadata["generation_id"] == "generation-001"
    assert observation.metadata["usage_evidence_source"] == "video-poll"
    assert actual_cost_microusd_from_observation(observation) == 484_000


def test_terminal_poll_recovers_cost_from_generation_metadata() -> None:
    transport = _SequenceTransport(
        (
            OpenRouterJsonResponse(
                200,
                {
                    "id": "job-001",
                    "status": "completed",
                    "generation_id": "generation/001",
                },
            ),
            OpenRouterJsonResponse(
                200,
                {"data": {"id": "generation/001", "total_cost": "0.484001"}},
            ),
        )
    )
    poller = OpenRouterManagedVideoGenerationJobPoller(
        "server-secret",
        transport=transport,
    )

    observation = poller.poll("job-001")

    assert observation.status is ProviderJobStatus.SUCCEEDED
    assert observation.metadata["usage_evidence_source"] == "generation-metadata"
    assert actual_cost_microusd_from_observation(observation) == 484_001
    assert [call[0] for call in transport.get_calls] == [
        "https://openrouter.ai/api/v1/videos/job-001",
        "https://openrouter.ai/api/v1/generation?id=generation%2F001",
    ]


def test_generation_metadata_without_numeric_total_cost_stays_fail_closed() -> None:
    transport = _SequenceTransport(
        (
            OpenRouterJsonResponse(
                200,
                {
                    "id": "job-001",
                    "status": "completed",
                    "generation_id": "generation-001",
                },
            ),
            OpenRouterJsonResponse(200, {"data": {"id": "generation-001"}}),
        )
    )
    observation = OpenRouterManagedVideoGenerationJobPoller(
        "server-secret",
        transport=transport,
    ).poll("job-001")

    with pytest.raises(OpenRouterManagedVideoRuntimeError, match="usage cost evidence"):
        actual_cost_microusd_from_observation(observation)


def test_generation_metadata_http_failure_stays_fail_closed() -> None:
    transport = _SequenceTransport(
        (
            OpenRouterJsonResponse(
                200,
                {
                    "id": "job-001",
                    "status": "completed",
                    "generation_id": "generation-001",
                },
            ),
            OpenRouterJsonResponse(404, {"error": "not found"}),
        )
    )
    observation = OpenRouterManagedVideoGenerationJobPoller(
        "server-secret",
        transport=transport,
    ).poll("job-001")

    with pytest.raises(OpenRouterManagedVideoRuntimeError, match="usage cost evidence"):
        actual_cost_microusd_from_observation(observation)


def test_cost_settlement_requires_terminal_provider_evidence() -> None:
    poller = OpenRouterManagedVideoGenerationJobPoller(
        "server-secret",
        transport=_Transport(
            OpenRouterJsonResponse(200, {"id": "job-001", "status": "pending"})
        ),
    )
    observation = poller.poll("job-001")
    with pytest.raises(OpenRouterManagedVideoRuntimeError, match="terminal"):
        actual_cost_microusd_from_observation(observation)


def test_terminal_observation_without_usage_cost_keeps_reservation_unsettled() -> None:
    poller = OpenRouterManagedVideoGenerationJobPoller(
        "server-secret",
        transport=_Transport(
            OpenRouterJsonResponse(200, {"id": "job-001", "status": "completed"})
        ),
    )
    observation = poller.poll("job-001")
    with pytest.raises(OpenRouterManagedVideoRuntimeError, match="usage cost evidence"):
        actual_cost_microusd_from_observation(observation)


def test_failed_job_preserves_usage_cost_when_provider_reports_it() -> None:
    poller = OpenRouterManagedVideoGenerationJobPoller(
        "server-secret",
        transport=_Transport(
            OpenRouterJsonResponse(
                200,
                {
                    "id": "job-001",
                    "status": "failed",
                    "error": {"code": "provider_error", "message": "failed"},
                    "usage": {"cost": "0.050001"},
                },
            )
        ),
    )
    observation = poller.poll("job-001")
    assert observation.status is ProviderJobStatus.FAILED
    assert observation.error_code == "provider_error"
    assert actual_cost_microusd_from_observation(observation) == 50_001
