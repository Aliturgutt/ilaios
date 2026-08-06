from __future__ import annotations

import json
from collections.abc import Callable

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
    GenerationExecutionStatus,
)
from src.video_automation.models import ProviderRequest, ProviderResult
from src.video_automation.provider_execution import (
    EpisodeProviderExecutionReport,
    ProviderDispatchSubmission,
    ProviderExecutionError,
    ProviderExecutionOrchestrator,
)
from src.video_automation.provider_registry import ProviderRegistry
from src.video_automation.providers import ProviderCapabilities
from src.video_automation.request_manifest import EpisodeRequestManifestBuilder
from src.video_automation.shot_request_planning import ShotGenerationRequest


class _Provider:
    def __init__(
        self,
        name: str = "provider-alpha",
        operations: tuple[str, ...] = ("video.generate",),
        handler: Callable[[ProviderRequest], ProviderResult] | None = None,
    ) -> None:
        self._capabilities = ProviderCapabilities(name, operations, False)
        self._handler = handler
        self.requests: list[ProviderRequest] = []

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self.requests.append(request)
        if self._handler is not None:
            return self._handler(request)
        return ProviderResult(
            request_id=request.request_id,
            provider_name=request.provider_name,
            success=True,
            external_id=f"job-{len(self.requests):03d}",
        )


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


def _dispatch_plan(
    count: int = 2,
    *,
    requests_per_batch: int = 1,
    provider_id: str = "provider-alpha",
    operation: str = "video.generate",
) -> EpisodeGenerationDispatchPlan:
    manifest = EpisodeRequestManifestBuilder().build(
        "episode-001", [_request(number) for number in range(1, count + 1)]
    )
    generation_plan = EpisodeGenerationBatchPlanner(
        GenerationBatchPolicy(max_requests_per_batch=requests_per_batch)
    ).plan(manifest)
    return EpisodeGenerationDispatchPlanner(
        GenerationProviderBinding(
            provider_id,
            "model-cinematic-v1",
            operation=operation,
        )
    ).plan(generation_plan)


def _registry(provider: _Provider) -> ProviderRegistry:
    return ProviderRegistry((provider,))


def test_execute_calls_registered_provider_once_per_dispatch() -> None:
    provider = _Provider()
    report = ProviderExecutionOrchestrator(_registry(provider)).execute(
        _dispatch_plan(3)
    )
    assert len(provider.requests) == 3
    assert report.successful_count == 3


def test_execute_preserves_dispatch_order() -> None:
    plan = _dispatch_plan(3)
    report = ProviderExecutionOrchestrator(_registry(_Provider())).execute(plan)
    assert [item.dispatch_id for item in report.submissions] == [
        dispatch.dispatch_id for dispatch in plan.dispatches
    ]


def test_provider_request_identity_matches_dispatch() -> None:
    provider = _Provider()
    plan = _dispatch_plan(1)
    ProviderExecutionOrchestrator(_registry(provider)).execute(plan)
    request = provider.requests[0]
    dispatch = plan.dispatches[0]
    assert request.request_id == dispatch.dispatch_id
    assert request.job_id == plan.dispatch_plan_id
    assert request.provider_name == dispatch.provider_id
    assert request.operation == dispatch.operation


def test_provider_request_contains_explicit_model_and_batch_policy() -> None:
    provider = _Provider()
    plan = _dispatch_plan(1)
    ProviderExecutionOrchestrator(_registry(provider)).execute(plan)
    payload = provider.requests[0].payload
    assert payload["model_id"] == "model-cinematic-v1"
    assert payload["batch_number"] == 1
    assert payload["request_count"] == 1


def test_provider_request_serializes_items_in_manifest_order() -> None:
    provider = _Provider()
    ProviderExecutionOrchestrator(_registry(provider)).execute(
        _dispatch_plan(2, requests_per_batch=2)
    )
    items = json.loads(str(provider.requests[0].payload["items_json"]))
    assert [item["shot_id"] for item in items] == ["shot-01", "shot-02"]
    assert [item["prompt_text"] for item in items] == [
        "approved prompt 01",
        "approved prompt 02",
    ]


def test_report_counts_successful_and_failed_submissions() -> None:
    def handler(request: ProviderRequest) -> ProviderResult:
        if request.request_id.endswith("000"):
            raise AssertionError("unreachable")
        success = len(provider.requests) == 1
        if success:
            return ProviderResult(
                request.request_id,
                request.provider_name,
                True,
                external_id="job-001",
            )
        return ProviderResult(
            request.request_id,
            request.provider_name,
            False,
            error_code="rejected",
            error_message="provider rejected request",
        )

    provider = _Provider(handler=handler)
    report = ProviderExecutionOrchestrator(_registry(provider)).execute(
        _dispatch_plan(2)
    )
    assert report.successful_count == 1
    assert report.failed_count == 1
    assert not report.all_submitted


def test_report_id_is_deterministic_for_same_provider_results() -> None:
    def build() -> EpisodeProviderExecutionReport:
        provider = _Provider(
            handler=lambda request: ProviderResult(
                request.request_id,
                request.provider_name,
                True,
                external_id="job-fixed",
            )
        )
        return ProviderExecutionOrchestrator(_registry(provider)).execute(
            _dispatch_plan(1)
        )

    assert build().execution_report_id == build().execution_report_id


def test_missing_provider_is_rejected_before_any_execution() -> None:
    provider = _Provider("provider-other")
    with pytest.raises(ProviderExecutionError, match="provider not registered"):
        ProviderExecutionOrchestrator(_registry(provider)).execute(_dispatch_plan(2))
    assert provider.requests == []


def test_unsupported_operation_is_rejected_before_execution() -> None:
    provider = _Provider(operations=("image.generate",))
    with pytest.raises(ProviderExecutionError, match="does not support operation"):
        ProviderExecutionOrchestrator(_registry(provider)).execute(_dispatch_plan(1))
    assert provider.requests == []


def test_mismatched_result_request_id_is_rejected() -> None:
    provider = _Provider(
        handler=lambda request: ProviderResult(
            "wrong-request",
            request.provider_name,
            True,
            external_id="job-001",
        )
    )
    with pytest.raises(ProviderExecutionError, match="request_id"):
        ProviderExecutionOrchestrator(_registry(provider)).execute(_dispatch_plan(1))


def test_mismatched_result_provider_name_is_rejected() -> None:
    provider = _Provider(
        handler=lambda request: ProviderResult(
            request.request_id,
            "provider-wrong",
            True,
            external_id="job-001",
        )
    )
    with pytest.raises(ProviderExecutionError, match="provider_name"):
        ProviderExecutionOrchestrator(_registry(provider)).execute(_dispatch_plan(1))


def test_success_without_external_id_is_rejected() -> None:
    provider = _Provider(
        handler=lambda request: ProviderResult(
            request.request_id,
            request.provider_name,
            True,
        )
    )
    with pytest.raises(ProviderExecutionError, match="external_id"):
        ProviderExecutionOrchestrator(_registry(provider)).execute(_dispatch_plan(1))


def test_failed_provider_result_becomes_failed_submission() -> None:
    provider = _Provider(
        handler=lambda request: ProviderResult(
            request.request_id,
            request.provider_name,
            False,
            error_code="quota",
            error_message="quota exceeded",
        )
    )
    report = ProviderExecutionOrchestrator(_registry(provider)).execute(
        _dispatch_plan(1)
    )
    submission = report.submissions[0]
    assert not submission.success
    assert submission.error_code == "quota"
    assert submission.error_message == "quota exceeded"


def test_provider_exception_is_normalized_without_retry() -> None:
    def raise_error(request: ProviderRequest) -> ProviderResult:
        raise RuntimeError("service unavailable")

    provider = _Provider(handler=raise_error)
    report = ProviderExecutionOrchestrator(_registry(provider)).execute(
        _dispatch_plan(1)
    )
    submission = report.submissions[0]
    assert submission.error_code == "provider_exception"
    assert submission.error_message == "service unavailable"
    assert len(provider.requests) == 1


def test_successful_submission_translates_to_submitted_tracking_update() -> None:
    report = ProviderExecutionOrchestrator(_registry(_Provider())).execute(
        _dispatch_plan(1)
    )
    update = report.submissions[0].to_submitted_update()
    assert update.status is GenerationExecutionStatus.SUBMITTED
    assert update.provider_job_id == "job-001"


def test_failed_submission_cannot_translate_to_submitted_update() -> None:
    submission = ProviderDispatchSubmission(
        dispatch_id="dispatch-001",
        provider_id="provider-alpha",
        request_id="request-001",
        success=False,
        error_code="rejected",
        error_message="provider rejected request",
    )
    with pytest.raises(ProviderExecutionError, match="only successful"):
        submission.to_submitted_update()


def test_submission_and_report_metadata_are_immutable() -> None:
    report = ProviderExecutionOrchestrator(_registry(_Provider())).execute(
        _dispatch_plan(1)
    )
    with pytest.raises(TypeError):
        report.metadata["extra"] = "value"  # type: ignore[index]
    with pytest.raises(TypeError):
        report.submissions[0].metadata["extra"] = "value"  # type: ignore[index]
