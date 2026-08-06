"""Deterministic provider execution orchestration for generation dispatch plans.

This module bridges approved generation dispatch contracts to already-registered
provider implementations. It does not select providers, poll jobs, retry work,
download media, or infer execution state. Successful provider submissions can be
translated into explicit SUBMITTED execution updates for the existing execution
tracker.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from types import MappingProxyType

from .generation_dispatch_planning import (
    EpisodeGenerationDispatchPlan,
    GenerationBatchDispatch,
)
from .generation_execution_tracking import (
    GenerationExecutionStatus,
    GenerationExecutionUpdate,
)
from .models import ProviderRequest, ProviderResult
from .provider_registry import ProviderRegistry


class ProviderExecutionError(ValueError):
    """Raised when a dispatch cannot be executed through the provider contract."""


@dataclass(frozen=True, slots=True)
class ProviderDispatchSubmission:
    """Normalized evidence for one provider submission attempt."""

    dispatch_id: str
    provider_id: str
    request_id: str
    success: bool
    provider_job_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_blank("dispatch_id", self.dispatch_id)
        _require_non_blank("provider_id", self.provider_id)
        _require_non_blank("request_id", self.request_id)
        _validate_optional_non_blank("provider_job_id", self.provider_job_id)
        _validate_optional_non_blank("error_code", self.error_code)
        _validate_optional_non_blank("error_message", self.error_message)
        if self.success:
            if self.provider_job_id is None:
                raise ProviderExecutionError(
                    "successful provider submission requires provider_job_id"
                )
            if self.error_code is not None or self.error_message is not None:
                raise ProviderExecutionError(
                    "successful provider submission must not contain an error"
                )
        else:
            if self.provider_job_id is not None:
                raise ProviderExecutionError(
                    "failed provider submission must not contain provider_job_id"
                )
            if self.error_message is None:
                raise ProviderExecutionError(
                    "failed provider submission requires error_message"
                )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    def to_submitted_update(self) -> GenerationExecutionUpdate:
        """Translate a successful submission into an explicit tracking update."""

        if not self.success or self.provider_job_id is None:
            raise ProviderExecutionError(
                "only successful provider submissions can become submitted updates"
            )
        return GenerationExecutionUpdate(
            dispatch_id=self.dispatch_id,
            status=GenerationExecutionStatus.SUBMITTED,
            provider_job_id=self.provider_job_id,
            metadata=self.metadata,
        )


@dataclass(frozen=True, slots=True)
class EpisodeProviderExecutionReport:
    """Ordered immutable provider-submission evidence for one dispatch plan."""

    execution_report_id: str
    dispatch_plan_id: str
    episode_id: str
    submissions: tuple[ProviderDispatchSubmission, ...]
    successful_count: int
    failed_count: int
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_blank("execution_report_id", self.execution_report_id)
        _require_non_blank("dispatch_plan_id", self.dispatch_plan_id)
        _require_non_blank("episode_id", self.episode_id)
        if not self.submissions:
            raise ProviderExecutionError("submissions must not be empty")
        dispatch_ids = tuple(item.dispatch_id for item in self.submissions)
        if len(dispatch_ids) != len(set(dispatch_ids)):
            raise ProviderExecutionError("submission dispatch_ids must be unique")
        expected_successful = sum(item.success for item in self.submissions)
        expected_failed = len(self.submissions) - expected_successful
        if self.successful_count != expected_successful:
            raise ProviderExecutionError(
                "successful_count must equal successful submission count"
            )
        if self.failed_count != expected_failed:
            raise ProviderExecutionError(
                "failed_count must equal failed submission count"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    @property
    def all_submitted(self) -> bool:
        """Return whether every provider submission succeeded."""

        return self.failed_count == 0


class ProviderExecutionOrchestrator:
    """Execute approved dispatches against already-registered providers."""

    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    def execute(
        self, dispatch_plan: EpisodeGenerationDispatchPlan
    ) -> EpisodeProviderExecutionReport:
        """Submit each dispatch in plan order without provider selection or retries."""

        self._preflight(dispatch_plan)
        submissions = tuple(
            self._execute_dispatch(dispatch_plan, dispatch)
            for dispatch in dispatch_plan.dispatches
        )
        canonical = _canonical_report_material(dispatch_plan, submissions)
        digest = sha256(canonical.encode("utf-8")).hexdigest()
        return EpisodeProviderExecutionReport(
            execution_report_id=f"provider-execution-{digest[:16]}",
            dispatch_plan_id=dispatch_plan.dispatch_plan_id,
            episode_id=dispatch_plan.episode_id,
            submissions=submissions,
            successful_count=sum(item.success for item in submissions),
            failed_count=sum(not item.success for item in submissions),
            metadata={
                "dispatch_count": str(len(dispatch_plan.dispatches)),
                "request_count": str(dispatch_plan.request_count),
            },
        )

    def _preflight(self, dispatch_plan: EpisodeGenerationDispatchPlan) -> None:
        for dispatch in dispatch_plan.dispatches:
            try:
                provider = self._registry.get(dispatch.provider_id)
            except KeyError as exc:
                raise ProviderExecutionError(
                    f"provider not registered: {dispatch.provider_id}"
                ) from exc
            if not provider.capabilities.supports(dispatch.operation):
                raise ProviderExecutionError(
                    f"provider does not support operation: {dispatch.operation}"
                )

    def _execute_dispatch(
        self,
        dispatch_plan: EpisodeGenerationDispatchPlan,
        dispatch: GenerationBatchDispatch,
    ) -> ProviderDispatchSubmission:
        provider = self._registry.get(dispatch.provider_id)
        request = _build_provider_request(dispatch_plan, dispatch)
        try:
            result = provider.execute(request)
        except Exception as exc:  # noqa: BLE001
            message = str(exc).strip() or exc.__class__.__name__
            return ProviderDispatchSubmission(
                dispatch_id=dispatch.dispatch_id,
                provider_id=dispatch.provider_id,
                request_id=request.request_id,
                success=False,
                error_code="provider_exception",
                error_message=message,
                metadata=_submission_metadata(dispatch),
            )
        _validate_provider_result(dispatch, request, result)
        if result.success:
            if result.external_id is None:
                raise ProviderExecutionError(
                    "successful provider result requires external_id for tracking"
                )
            return ProviderDispatchSubmission(
                dispatch_id=dispatch.dispatch_id,
                provider_id=dispatch.provider_id,
                request_id=request.request_id,
                success=True,
                provider_job_id=result.external_id,
                metadata=_submission_metadata(dispatch),
            )
        return ProviderDispatchSubmission(
            dispatch_id=dispatch.dispatch_id,
            provider_id=dispatch.provider_id,
            request_id=request.request_id,
            success=False,
            error_code=result.error_code,
            error_message=result.error_message,
            metadata=_submission_metadata(dispatch),
        )


def _build_provider_request(
    dispatch_plan: EpisodeGenerationDispatchPlan,
    dispatch: GenerationBatchDispatch,
) -> ProviderRequest:
    items = [
        {
            "sequence_number": item.sequence_number,
            "request_id": item.request_id,
            "idempotency_key": item.idempotency_key,
            "shot_id": item.shot_id,
            "prompt_text": item.prompt_text,
            "duration_seconds": item.duration_seconds,
            "aspect_ratio": item.aspect_ratio,
            "frames_per_second": item.frames_per_second,
            "output_count": item.output_count,
            "seed": item.seed,
        }
        for item in dispatch.items
    ]
    return ProviderRequest(
        request_id=dispatch.dispatch_id,
        job_id=dispatch_plan.dispatch_plan_id,
        provider_name=dispatch.provider_id,
        operation=dispatch.operation,
        payload={
            "model_id": dispatch.model_id,
            "batch_id": dispatch.batch_id,
            "batch_number": dispatch.batch_number,
            "max_parallel_requests": dispatch.max_parallel_requests,
            "request_count": len(dispatch.items),
            "items_json": json.dumps(
                items,
                sort_keys=True,
                separators=(",", ":"),
            ),
        },
    )


def _validate_provider_result(
    dispatch: GenerationBatchDispatch,
    request: ProviderRequest,
    result: ProviderResult,
) -> None:
    if result.request_id != request.request_id:
        raise ProviderExecutionError("provider result request_id does not match request")
    if result.provider_name != dispatch.provider_id:
        raise ProviderExecutionError(
            "provider result provider_name does not match dispatch provider_id"
        )


def _submission_metadata(dispatch: GenerationBatchDispatch) -> Mapping[str, str]:
    return {
        "batch_id": dispatch.batch_id,
        "batch_number": str(dispatch.batch_number),
        "model_id": dispatch.model_id,
        "operation": dispatch.operation,
    }


def _canonical_report_material(
    dispatch_plan: EpisodeGenerationDispatchPlan,
    submissions: tuple[ProviderDispatchSubmission, ...],
) -> str:
    lines = [f"dispatch_plan_id={dispatch_plan.dispatch_plan_id}"]
    lines.extend(
        f"dispatch_id={item.dispatch_id}|provider_id={item.provider_id}|"
        f"request_id={item.request_id}|success={item.success}|"
        f"provider_job_id={item.provider_job_id or ''}|"
        f"error_code={item.error_code or ''}|error_message={item.error_message or ''}"
        for item in submissions
    )
    return "\n".join(lines)


def _freeze_metadata(metadata: Mapping[str, str]) -> Mapping[str, str]:
    normalized = dict(metadata)
    for key, value in normalized.items():
        _require_non_blank("metadata key", key)
        _require_non_blank(f"metadata value for {key}", value)
    return MappingProxyType(normalized)


def _validate_optional_non_blank(name: str, value: str | None) -> None:
    if value is not None:
        _require_non_blank(name, value)


def _require_non_blank(name: str, value: str) -> None:
    if not value.strip():
        raise ProviderExecutionError(f"{name} must not be blank")
