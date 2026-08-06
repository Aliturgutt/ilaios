"""Tests for canonical M12 Media Acquisition & Generation Orchestrator."""

from __future__ import annotations

from collections import deque
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.video_automation.generated_asset_retrieval import (
    GeneratedAssetPayload,
    GeneratedAssetRetrievalCoordinator,
    GeneratedAssetRetrieverRegistry,
)
from src.video_automation.generation_dispatch_planning import (
    EpisodeGenerationDispatchPlan,
    GenerationBatchDispatch,
    GenerationDispatchItem,
)
from src.video_automation.generation_execution_tracking import (
    EpisodeGenerationExecutionTracker,
    GenerationExecutionStatus,
)
from src.video_automation.generation_job_polling import (
    GenerationJobPollerRegistry,
    GenerationJobPollingCoordinator,
    ProviderJobObservation,
    ProviderJobStatus,
)
from src.video_automation.generation_result_ingestion import (
    EpisodeGenerationResultIngester,
)
from src.video_automation.media_acquisition_orchestrator import (
    MediaAcquisitionGenerationOrchestrator,
    MediaAcquisitionOrchestrationError,
)
from src.video_automation.models import ProviderRequest, ProviderResult
from src.video_automation.provider_execution import ProviderExecutionOrchestrator
from src.video_automation.provider_registry import ProviderRegistry
from src.video_automation.providers import (
    ProviderCapabilities,
    VideoGenerationProvider,
)

PROVIDER_ID = "test-video-provider"
OPERATION = "video.generate"
ASSET_ID = "fixture://generated-video-1"


class FakeVideoProvider(VideoGenerationProvider):
    """Deterministic provider used only by M12 tests."""

    def __init__(self, *, succeed: bool = True) -> None:
        super().__init__(
            ProviderCapabilities(
                provider_name=PROVIDER_ID,
                operations=(OPERATION,),
                is_paid=False,
            )
        )
        self._succeed = succeed
        self.execution_count = 0

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self._validate_request(request)
        self.execution_count += 1

        if not self._succeed:
            return ProviderResult(
                request_id=request.request_id,
                provider_name=request.provider_name,
                success=False,
                error_code="submission_failed",
                error_message="deterministic submission failure",
            )

        return ProviderResult(
            request_id=request.request_id,
            provider_name=request.provider_name,
            success=True,
            external_id=f"provider-job-{request.request_id}",
        )


class SequencePoller:
    """Return explicit observations in supplied order."""

    def __init__(
        self,
        observations: tuple[ProviderJobStatus, ...],
    ) -> None:
        self._observations = deque(observations)
        self.poll_count = 0

    @property
    def provider_id(self) -> str:
        return PROVIDER_ID

    def poll(self, provider_job_id: str) -> ProviderJobObservation:
        self.poll_count += 1

        if self._observations:
            status = self._observations.popleft()
        else:
            status = ProviderJobStatus.RUNNING

        if status is ProviderJobStatus.SUCCEEDED:
            return ProviderJobObservation(
                provider_id=PROVIDER_ID,
                provider_job_id=provider_job_id,
                status=status,
                output_asset_ids=(ASSET_ID,),
            )

        if status is ProviderJobStatus.FAILED:
            return ProviderJobObservation(
                provider_id=PROVIDER_ID,
                provider_job_id=provider_job_id,
                status=status,
                error_code="provider_failed",
                error_message="deterministic provider failure",
            )

        return ProviderJobObservation(
            provider_id=PROVIDER_ID,
            provider_job_id=provider_job_id,
            status=status,
        )


class FakeAssetRetriever:
    """Return deterministic bytes for the normalized generated asset id."""

    @property
    def provider_id(self) -> str:
        return PROVIDER_ID

    def retrieve(self, asset_id: str) -> GeneratedAssetPayload:
        if asset_id != ASSET_ID:
            raise ValueError(f"unexpected asset_id: {asset_id}")

        return GeneratedAssetPayload(
            source_asset_id=asset_id,
            body=b"deterministic-generated-video",
            content_type="video/mp4",
            file_extension=".mp4",
            metadata={"source": "m12-test"},
        )


def _dispatch_plan() -> EpisodeGenerationDispatchPlan:
    item = GenerationDispatchItem(
        sequence_number=1,
        request_id="request-1",
        idempotency_key="idempotency-1",
        shot_id="shot-1",
        prompt_text="Deterministic test shot",
        duration_seconds=4.0,
        aspect_ratio="9:16",
        frames_per_second=30,
        output_count=1,
        seed=123,
    )

    dispatch = GenerationBatchDispatch(
        dispatch_id="dispatch-1",
        batch_id="batch-1",
        batch_number=1,
        provider_id=PROVIDER_ID,
        model_id="test-model",
        operation=OPERATION,
        max_parallel_requests=1,
        items=(item,),
        metadata={
            "generation_plan_id": "generation-plan-1",
            "manifest_id": "manifest-1",
            "episode_id": "episode-1",
        },
    )

    return EpisodeGenerationDispatchPlan(
        dispatch_plan_id="dispatch-plan-1",
        generation_plan_id="generation-plan-1",
        manifest_id="manifest-1",
        episode_id="episode-1",
        dispatches=(dispatch,),
        dispatch_count=1,
        request_count=1,
        metadata={
            "provider_id": PROVIDER_ID,
            "model_id": "test-model",
            "operation": OPERATION,
        },
    )


def _orchestrator(
    storage_root: Path,
    provider: FakeVideoProvider,
    poller: SequencePoller,
    *,
    max_poll_rounds: int = 3,
) -> MediaAcquisitionGenerationOrchestrator:
    provider_registry = ProviderRegistry((provider,))
    poller_registry = GenerationJobPollerRegistry((poller,))
    retriever_registry = GeneratedAssetRetrieverRegistry(
        (FakeAssetRetriever(),)
    )

    return MediaAcquisitionGenerationOrchestrator(
        provider_execution=ProviderExecutionOrchestrator(provider_registry),
        execution_tracker=EpisodeGenerationExecutionTracker(),
        polling=GenerationJobPollingCoordinator(poller_registry),
        result_ingester=EpisodeGenerationResultIngester(),
        asset_retrieval=GeneratedAssetRetrievalCoordinator(
            retriever_registry,
            storage_root,
        ),
        max_poll_rounds=max_poll_rounds,
    )


def test_complete_m12_lifecycle_reuses_existing_components() -> None:
    with TemporaryDirectory() as directory_name:
        storage_root = Path(directory_name) / "assets"
        provider = FakeVideoProvider()
        poller = SequencePoller(
            (
                ProviderJobStatus.RUNNING,
                ProviderJobStatus.SUCCEEDED,
            )
        )

        result = _orchestrator(
            storage_root,
            provider,
            poller,
        ).execute(_dispatch_plan())

        assert result.dispatch_plan_id == "dispatch-plan-1"
        assert result.execution_report.all_submitted is True
        assert result.final_execution_state.is_terminal is True
        assert result.final_execution_state.completed_count == 1
        assert result.final_execution_state.failed_count == 0
        assert result.result_manifest.succeeded_count == 1
        assert len(result.result_manifest.assets) == 1
        assert result.retrieval_manifest.asset_count == 1
        assert result.poll_rounds == 2

        retrieved = result.retrieval_manifest.assets[0]

        assert retrieved.asset_id == ASSET_ID
        assert retrieved.provider_id == PROVIDER_ID
        assert Path(retrieved.local_path).is_file()
        assert (
            Path(retrieved.local_path).read_bytes()
            == b"deterministic-generated-video"
        )

        assert provider.execution_count == 1
        assert poller.poll_count == 2


def test_provider_can_complete_on_first_poll_round() -> None:
    with TemporaryDirectory() as directory_name:
        provider = FakeVideoProvider()
        poller = SequencePoller(
            (ProviderJobStatus.SUCCEEDED,)
        )

        result = _orchestrator(
            Path(directory_name),
            provider,
            poller,
        ).execute(_dispatch_plan())

        assert result.poll_rounds == 1
        assert result.final_execution_state.completed_count == 1


def test_submission_failure_fails_closed_before_polling() -> None:
    with TemporaryDirectory() as directory_name:
        provider = FakeVideoProvider(succeed=False)
        poller = SequencePoller(
            (ProviderJobStatus.SUCCEEDED,)
        )

        with pytest.raises(
            MediaAcquisitionOrchestrationError,
            match="provider submission failed",
        ):
            _orchestrator(
                Path(directory_name),
                provider,
                poller,
            ).execute(_dispatch_plan())

        assert provider.execution_count == 1
        assert poller.poll_count == 0


def test_failed_provider_execution_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        provider = FakeVideoProvider()
        poller = SequencePoller(
            (ProviderJobStatus.FAILED,)
        )

        with pytest.raises(
            MediaAcquisitionOrchestrationError,
            match="failed dispatches",
        ):
            _orchestrator(
                Path(directory_name),
                provider,
                poller,
            ).execute(_dispatch_plan())


def test_polling_is_bounded_and_times_out() -> None:
    with TemporaryDirectory() as directory_name:
        provider = FakeVideoProvider()
        poller = SequencePoller(
            (
                ProviderJobStatus.RUNNING,
                ProviderJobStatus.RUNNING,
                ProviderJobStatus.RUNNING,
            )
        )

        with pytest.raises(
            MediaAcquisitionOrchestrationError,
            match="max_poll_rounds",
        ):
            _orchestrator(
                Path(directory_name),
                provider,
                poller,
                max_poll_rounds=2,
            ).execute(_dispatch_plan())

        assert poller.poll_count == 2


def test_zero_poll_round_limit_is_rejected() -> None:
    with TemporaryDirectory() as directory_name:
        provider = FakeVideoProvider()
        poller = SequencePoller(
            (ProviderJobStatus.SUCCEEDED,)
        )

        with pytest.raises(
            MediaAcquisitionOrchestrationError,
            match="max_poll_rounds",
        ):
            _orchestrator(
                Path(directory_name),
                provider,
                poller,
                max_poll_rounds=0,
            )


def test_retrieval_is_deterministic_for_same_result() -> None:
    with TemporaryDirectory() as directory_name:
        storage_root = Path(directory_name) / "assets"

        first = _orchestrator(
            storage_root,
            FakeVideoProvider(),
            SequencePoller((ProviderJobStatus.SUCCEEDED,)),
        ).execute(_dispatch_plan())

        second = _orchestrator(
            storage_root,
            FakeVideoProvider(),
            SequencePoller((ProviderJobStatus.SUCCEEDED,)),
        ).execute(_dispatch_plan())

        assert (
            first.retrieval_manifest.assets[0].sha256_hex
            == second.retrieval_manifest.assets[0].sha256_hex
        )

        assert (
            first.retrieval_manifest.assets[0].local_path
            == second.retrieval_manifest.assets[0].local_path
        )


def test_orchestrator_does_not_select_provider() -> None:
    with TemporaryDirectory() as directory_name:
        plan = _dispatch_plan()

        assert plan.dispatches[0].provider_id == PROVIDER_ID

        result = _orchestrator(
            Path(directory_name),
            FakeVideoProvider(),
            SequencePoller((ProviderJobStatus.SUCCEEDED,)),
        ).execute(plan)

        assert (
            result.execution_report.submissions[0].provider_id
            == PROVIDER_ID
        )


def test_result_manifest_and_retrieval_manifest_keep_traceability() -> None:
    with TemporaryDirectory() as directory_name:
        result = _orchestrator(
            Path(directory_name),
            FakeVideoProvider(),
            SequencePoller((ProviderJobStatus.SUCCEEDED,)),
        ).execute(_dispatch_plan())

        assert result.result_manifest.dispatch_plan_id == "dispatch-plan-1"
        assert result.result_manifest.episode_id == "episode-1"
        assert result.retrieval_manifest.dispatch_plan_id == "dispatch-plan-1"
        assert result.retrieval_manifest.episode_id == "episode-1"


def test_successful_state_contains_provider_job_and_asset_reference() -> None:
    with TemporaryDirectory() as directory_name:
        result = _orchestrator(
            Path(directory_name),
            FakeVideoProvider(),
            SequencePoller((ProviderJobStatus.SUCCEEDED,)),
        ).execute(_dispatch_plan())

        record = result.final_execution_state.records[0]

        assert record.status is GenerationExecutionStatus.SUCCEEDED
        assert record.provider_job_id == "provider-job-dispatch-1"
        assert record.output_asset_ids == (ASSET_ID,)
