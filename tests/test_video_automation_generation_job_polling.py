from __future__ import annotations

from collections.abc import Mapping

import pytest

from src.video_automation.generation_batch_planning import (
    EpisodeGenerationBatchPlanner,
    GenerationBatchPolicy,
)
from src.video_automation.generation_dispatch_planning import (
    EpisodeGenerationDispatchPlan,
    EpisodeGenerationDispatchPlanner,
    GenerationProviderBinding,
)
from src.video_automation.generation_execution_tracking import (
    EpisodeGenerationExecutionState,
    EpisodeGenerationExecutionTracker,
    GenerationExecutionStatus,
    GenerationExecutionUpdate,
)
from src.video_automation.generation_job_polling import (
    ArkTaskJsonResponse,
    GenerationJobPollerRegistry,
    GenerationJobPollingCoordinator,
    GenerationJobPollingError,
    ProviderJobObservation,
    ProviderJobStatus,
    SeedanceArkGenerationJobPoller,
)
from src.video_automation.request_manifest import EpisodeRequestManifestBuilder
from src.video_automation.shot_request_planning import ShotGenerationRequest


class _Poller:
    def __init__(
        self,
        provider_id: str = "provider-alpha",
        observation: ProviderJobObservation | None = None,
    ) -> None:
        self._provider_id = provider_id
        self.observation = observation or ProviderJobObservation(
            provider_id=provider_id,
            provider_job_id="job-001",
            status=ProviderJobStatus.RUNNING,
        )
        self.calls: list[str] = []

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def poll(self, provider_job_id: str) -> ProviderJobObservation:
        self.calls.append(provider_job_id)
        return self.observation


class _ArkTransport:
    def __init__(self, response: ArkTaskJsonResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, Mapping[str, str], float]] = []

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> ArkTaskJsonResponse:
        self.calls.append((url, headers, timeout_seconds))
        return self.response


def _request(number: int) -> ShotGenerationRequest:
    suffix = f"{number:02d}"
    return ShotGenerationRequest(
        request_id=f"request-{suffix}",
        idempotency_key=(f"{number:x}" * 64)[:64],
        shot_id=f"shot-{suffix}",
        source_beat_id=f"beat-{suffix}",
        prompt_text=f"approved prompt {suffix}",
        duration_seconds=5.0,
        aspect_ratio="9:16",
        frames_per_second=24,
        output_count=1,
        seed=None,
        metadata={},
    )


def _plan(provider_id: str = "provider-alpha") -> EpisodeGenerationDispatchPlan:
    manifest = EpisodeRequestManifestBuilder().build("episode-001", [_request(1)])
    generation_plan = EpisodeGenerationBatchPlanner(
        GenerationBatchPolicy(max_requests_per_batch=1)
    ).plan(manifest)
    return EpisodeGenerationDispatchPlanner(
        GenerationProviderBinding(provider_id, "model-001")
    ).plan(generation_plan)


def _submitted_state(plan: EpisodeGenerationDispatchPlan) -> EpisodeGenerationExecutionState:
    tracker = EpisodeGenerationExecutionTracker()
    initial = tracker.initialize(plan)
    return tracker.apply(
        plan,
        initial,
        GenerationExecutionUpdate(
            plan.dispatches[0].dispatch_id,
            GenerationExecutionStatus.SUBMITTED,
            provider_job_id="job-001",
        ),
    )


def _running_state(plan: EpisodeGenerationDispatchPlan) -> EpisodeGenerationExecutionState:
    tracker = EpisodeGenerationExecutionTracker()
    submitted = _submitted_state(plan)
    return tracker.apply(
        plan,
        submitted,
        GenerationExecutionUpdate(
            plan.dispatches[0].dispatch_id,
            GenerationExecutionStatus.RUNNING,
            provider_job_id="job-001",
        ),
    )


def test_observation_metadata_is_immutable() -> None:
    observation = ProviderJobObservation(
        "provider-alpha", "job-001", ProviderJobStatus.RUNNING, metadata={"a": "b"}
    )
    with pytest.raises(TypeError):
        observation.metadata["x"] = "y"  # type: ignore[index]


def test_succeeded_observation_requires_output_assets() -> None:
    with pytest.raises(GenerationJobPollingError, match="output_asset_ids"):
        ProviderJobObservation(
            "provider-alpha", "job-001", ProviderJobStatus.SUCCEEDED
        )


def test_failed_observation_requires_error_code() -> None:
    with pytest.raises(GenerationJobPollingError, match="error_code"):
        ProviderJobObservation("provider-alpha", "job-001", ProviderJobStatus.FAILED)


def test_registry_returns_provider_ids_in_sorted_order() -> None:
    registry = GenerationJobPollerRegistry((_Poller("zeta"), _Poller("alpha")))
    assert registry.list_provider_ids() == ("alpha", "zeta")


def test_registry_rejects_duplicate_provider_id() -> None:
    with pytest.raises(GenerationJobPollingError, match="already registered"):
        GenerationJobPollerRegistry((_Poller(), _Poller()))


def test_coordinator_polls_submitted_record() -> None:
    plan = _plan()
    poller = _Poller()
    GenerationJobPollingCoordinator(GenerationJobPollerRegistry((poller,))).poll(
        plan, _submitted_state(plan)
    )
    assert poller.calls == ["job-001"]


def test_queued_observation_keeps_submitted_state_without_update() -> None:
    plan = _plan()
    poller = _Poller(
        observation=ProviderJobObservation(
            "provider-alpha", "job-001", ProviderJobStatus.QUEUED
        )
    )
    updates = GenerationJobPollingCoordinator(
        GenerationJobPollerRegistry((poller,))
    ).poll(plan, _submitted_state(plan))
    assert updates == ()


def test_running_observation_produces_running_update() -> None:
    plan = _plan()
    updates = GenerationJobPollingCoordinator(
        GenerationJobPollerRegistry((_Poller(),))
    ).poll(plan, _submitted_state(plan))
    assert updates[0].status is GenerationExecutionStatus.RUNNING
    assert updates[0].provider_job_id == "job-001"


def test_succeeded_observation_produces_asset_update() -> None:
    plan = _plan()
    poller = _Poller(
        observation=ProviderJobObservation(
            "provider-alpha",
            "job-001",
            ProviderJobStatus.SUCCEEDED,
            output_asset_ids=("https://assets.test/video.mp4",),
        )
    )
    update = GenerationJobPollingCoordinator(
        GenerationJobPollerRegistry((poller,))
    ).poll(plan, _submitted_state(plan))[0]
    assert update.status is GenerationExecutionStatus.SUCCEEDED
    assert update.output_asset_ids == ("https://assets.test/video.mp4",)


def test_failed_observation_produces_failed_update() -> None:
    plan = _plan()
    poller = _Poller(
        observation=ProviderJobObservation(
            "provider-alpha",
            "job-001",
            ProviderJobStatus.FAILED,
            error_code="provider_error",
            error_message="failed",
        )
    )
    update = GenerationJobPollingCoordinator(
        GenerationJobPollerRegistry((poller,))
    ).poll(plan, _submitted_state(plan))[0]
    assert update.status is GenerationExecutionStatus.FAILED
    assert update.error_code == "provider_error"


def test_cancelled_observation_produces_cancelled_update() -> None:
    plan = _plan()
    poller = _Poller(
        observation=ProviderJobObservation(
            "provider-alpha", "job-001", ProviderJobStatus.CANCELLED
        )
    )
    update = GenerationJobPollingCoordinator(
        GenerationJobPollerRegistry((poller,))
    ).poll(plan, _submitted_state(plan))[0]
    assert update.status is GenerationExecutionStatus.CANCELLED


def test_pending_record_is_not_polled() -> None:
    plan = _plan()
    poller = _Poller()
    state = EpisodeGenerationExecutionTracker().initialize(plan)
    updates = GenerationJobPollingCoordinator(
        GenerationJobPollerRegistry((poller,))
    ).poll(plan, state)
    assert updates == ()
    assert poller.calls == []


def test_terminal_record_is_not_polled() -> None:
    plan = _plan()
    tracker = EpisodeGenerationExecutionTracker()
    submitted = _submitted_state(plan)
    succeeded = tracker.apply(
        plan,
        submitted,
        GenerationExecutionUpdate(
            plan.dispatches[0].dispatch_id,
            GenerationExecutionStatus.SUCCEEDED,
            provider_job_id="job-001",
            output_asset_ids=("asset-001",),
        ),
    )
    poller = _Poller()
    assert GenerationJobPollingCoordinator(
        GenerationJobPollerRegistry((poller,))
    ).poll(plan, succeeded) == ()
    assert poller.calls == []


def test_missing_provider_poller_is_rejected() -> None:
    plan = _plan()
    with pytest.raises(GenerationJobPollingError, match="not registered"):
        GenerationJobPollingCoordinator(GenerationJobPollerRegistry()).poll(
            plan, _submitted_state(plan)
        )


def test_mismatched_observation_provider_is_rejected() -> None:
    plan = _plan()
    poller = _Poller(
        observation=ProviderJobObservation(
            "other-provider", "job-001", ProviderJobStatus.RUNNING
        )
    )
    with pytest.raises(GenerationJobPollingError, match="provider_id"):
        GenerationJobPollingCoordinator(
            GenerationJobPollerRegistry((poller,))
        ).poll(plan, _submitted_state(plan))


def test_seedance_poller_queries_task_endpoint_and_maps_running() -> None:
    transport = _ArkTransport(ArkTaskJsonResponse(200, {"status": "running"}))
    poller = SeedanceArkGenerationJobPoller("secret", transport=transport)
    observation = poller.poll("task-001")
    assert transport.calls[0][0].endswith("/contents/generations/tasks/task-001")
    assert transport.calls[0][1]["Authorization"] == "Bearer secret"
    assert observation.status is ProviderJobStatus.RUNNING


def test_seedance_poller_maps_succeeded_video_url() -> None:
    transport = _ArkTransport(
        ArkTaskJsonResponse(
            200,
            {
                "status": "succeeded",
                "content": {
                    "video_url": "https://assets.test/video.mp4",
                    "last_frame_url": "https://assets.test/frame.jpg",
                },
            },
        )
    )
    observation = SeedanceArkGenerationJobPoller(
        "secret", transport=transport
    ).poll("task-001")
    assert observation.output_asset_ids == ("https://assets.test/video.mp4",)
    assert observation.metadata["last_frame_url"] == "https://assets.test/frame.jpg"
