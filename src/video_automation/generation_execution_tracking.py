"""Deterministic execution-state tracking for generation dispatch plans.

This module validates and records execution updates supplied by an external
executor. It does not call providers, submit jobs, poll services, retry work,
generate media, or infer state transitions.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType

from .generation_dispatch_planning import EpisodeGenerationDispatchPlan


class GenerationExecutionTrackingError(ValueError):
    """Raised when a generation execution state or transition is invalid."""


class GenerationExecutionStatus(StrEnum):
    """Allowed lifecycle states for one generation dispatch."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL_STATUSES = frozenset(
    {
        GenerationExecutionStatus.SUCCEEDED,
        GenerationExecutionStatus.FAILED,
        GenerationExecutionStatus.CANCELLED,
    }
)

_ALLOWED_TRANSITIONS: Mapping[
    GenerationExecutionStatus, frozenset[GenerationExecutionStatus]
] = MappingProxyType(
    {
        GenerationExecutionStatus.PENDING: frozenset(
            {
                GenerationExecutionStatus.SUBMITTED,
                GenerationExecutionStatus.CANCELLED,
            }
        ),
        GenerationExecutionStatus.SUBMITTED: frozenset(
            {
                GenerationExecutionStatus.RUNNING,
                GenerationExecutionStatus.SUCCEEDED,
                GenerationExecutionStatus.FAILED,
                GenerationExecutionStatus.CANCELLED,
            }
        ),
        GenerationExecutionStatus.RUNNING: frozenset(
            {
                GenerationExecutionStatus.SUCCEEDED,
                GenerationExecutionStatus.FAILED,
                GenerationExecutionStatus.CANCELLED,
            }
        ),
        GenerationExecutionStatus.SUCCEEDED: frozenset(),
        GenerationExecutionStatus.FAILED: frozenset(),
        GenerationExecutionStatus.CANCELLED: frozenset(),
    }
)


@dataclass(frozen=True, slots=True)
class GenerationExecutionUpdate:
    """Externally supplied update for one dispatch execution."""

    dispatch_id: str
    status: GenerationExecutionStatus
    provider_job_id: str | None = None
    output_asset_ids: tuple[str, ...] = ()
    error_code: str | None = None
    error_message: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_blank("dispatch_id", self.dispatch_id)
        _validate_optional_non_blank("provider_job_id", self.provider_job_id)
        _validate_optional_non_blank("error_code", self.error_code)
        _validate_optional_non_blank("error_message", self.error_message)
        _validate_unique_non_blank_values("output_asset_ids", self.output_asset_ids)
        _validate_status_payload(
            self.status,
            self.provider_job_id,
            self.output_asset_ids,
            self.error_code,
            self.error_message,
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class GenerationDispatchExecution:
    """Current immutable execution record for one planned dispatch."""

    dispatch_id: str
    batch_id: str
    batch_number: int
    status: GenerationExecutionStatus
    revision: int
    provider_job_id: str | None
    output_asset_ids: tuple[str, ...]
    error_code: str | None
    error_message: str | None
    metadata: Mapping[str, str]

    def __post_init__(self) -> None:
        _require_non_blank("dispatch_id", self.dispatch_id)
        _require_non_blank("batch_id", self.batch_id)
        if self.batch_number <= 0:
            raise GenerationExecutionTrackingError(
                "batch_number must be greater than zero"
            )
        if self.revision < 0:
            raise GenerationExecutionTrackingError("revision must not be negative")
        _validate_optional_non_blank("provider_job_id", self.provider_job_id)
        _validate_optional_non_blank("error_code", self.error_code)
        _validate_optional_non_blank("error_message", self.error_message)
        _validate_unique_non_blank_values("output_asset_ids", self.output_asset_ids)
        _validate_status_payload(
            self.status,
            self.provider_job_id,
            self.output_asset_ids,
            self.error_code,
            self.error_message,
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    @property
    def is_terminal(self) -> bool:
        """Return whether this record has reached an immutable terminal state."""

        return self.status in _TERMINAL_STATUSES


@dataclass(frozen=True, slots=True)
class EpisodeGenerationExecutionState:
    """Ordered execution state for every dispatch in one episode plan."""

    execution_state_id: str
    dispatch_plan_id: str
    generation_plan_id: str
    manifest_id: str
    episode_id: str
    records: tuple[GenerationDispatchExecution, ...]
    completed_count: int
    failed_count: int
    cancelled_count: int
    metadata: Mapping[str, str]

    def __post_init__(self) -> None:
        _require_non_blank("execution_state_id", self.execution_state_id)
        _require_non_blank("dispatch_plan_id", self.dispatch_plan_id)
        _require_non_blank("generation_plan_id", self.generation_plan_id)
        _require_non_blank("manifest_id", self.manifest_id)
        _require_non_blank("episode_id", self.episode_id)
        if not self.records:
            raise GenerationExecutionTrackingError("records must not be empty")
        expected_numbers = tuple(range(1, len(self.records) + 1))
        actual_numbers = tuple(record.batch_number for record in self.records)
        if actual_numbers != expected_numbers:
            raise GenerationExecutionTrackingError(
                "record batch_numbers must be contiguous and start at one"
            )
        dispatch_ids = tuple(record.dispatch_id for record in self.records)
        if len(dispatch_ids) != len(set(dispatch_ids)):
            raise GenerationExecutionTrackingError("dispatch_ids must be unique")
        expected_completed = sum(
            record.status is GenerationExecutionStatus.SUCCEEDED
            for record in self.records
        )
        expected_failed = sum(
            record.status is GenerationExecutionStatus.FAILED
            for record in self.records
        )
        expected_cancelled = sum(
            record.status is GenerationExecutionStatus.CANCELLED
            for record in self.records
        )
        if self.completed_count != expected_completed:
            raise GenerationExecutionTrackingError(
                "completed_count must equal succeeded record count"
            )
        if self.failed_count != expected_failed:
            raise GenerationExecutionTrackingError(
                "failed_count must equal failed record count"
            )
        if self.cancelled_count != expected_cancelled:
            raise GenerationExecutionTrackingError(
                "cancelled_count must equal cancelled record count"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    @property
    def is_terminal(self) -> bool:
        """Return whether every dispatch execution is terminal."""

        return all(record.is_terminal for record in self.records)


class EpisodeGenerationExecutionTracker:
    """Create and advance execution state using explicit external updates."""

    def initialize(
        self, dispatch_plan: EpisodeGenerationDispatchPlan
    ) -> EpisodeGenerationExecutionState:
        """Create a pending execution record for each planned dispatch."""

        records = tuple(
            GenerationDispatchExecution(
                dispatch_id=dispatch.dispatch_id,
                batch_id=dispatch.batch_id,
                batch_number=dispatch.batch_number,
                status=GenerationExecutionStatus.PENDING,
                revision=0,
                provider_job_id=None,
                output_asset_ids=(),
                error_code=None,
                error_message=None,
                metadata={
                    "provider_id": dispatch.provider_id,
                    "model_id": dispatch.model_id,
                },
            )
            for dispatch in dispatch_plan.dispatches
        )
        return _build_state(dispatch_plan, records)

    def apply(
        self,
        dispatch_plan: EpisodeGenerationDispatchPlan,
        current: EpisodeGenerationExecutionState,
        update: GenerationExecutionUpdate,
    ) -> EpisodeGenerationExecutionState:
        """Apply one explicit update after validating identity and transition."""

        _validate_state_matches_plan(dispatch_plan, current)
        matching = tuple(
            record for record in current.records if record.dispatch_id == update.dispatch_id
        )
        if not matching:
            raise GenerationExecutionTrackingError(
                f"unknown dispatch_id: {update.dispatch_id}"
            )
        existing = matching[0]
        if update.status not in _ALLOWED_TRANSITIONS[existing.status]:
            raise GenerationExecutionTrackingError(
                f"invalid transition: {existing.status.value} -> {update.status.value}"
            )
        replacement = GenerationDispatchExecution(
            dispatch_id=existing.dispatch_id,
            batch_id=existing.batch_id,
            batch_number=existing.batch_number,
            status=update.status,
            revision=existing.revision + 1,
            provider_job_id=update.provider_job_id,
            output_asset_ids=update.output_asset_ids,
            error_code=update.error_code,
            error_message=update.error_message,
            metadata=update.metadata,
        )
        records = tuple(
            replacement if record.dispatch_id == update.dispatch_id else record
            for record in current.records
        )
        return _build_state(dispatch_plan, records)


def _build_state(
    dispatch_plan: EpisodeGenerationDispatchPlan,
    records: tuple[GenerationDispatchExecution, ...],
) -> EpisodeGenerationExecutionState:
    canonical = _canonical_state_material(dispatch_plan, records)
    digest = sha256(canonical.encode("utf-8")).hexdigest()
    return EpisodeGenerationExecutionState(
        execution_state_id=f"execution-state-{digest[:16]}",
        dispatch_plan_id=dispatch_plan.dispatch_plan_id,
        generation_plan_id=dispatch_plan.generation_plan_id,
        manifest_id=dispatch_plan.manifest_id,
        episode_id=dispatch_plan.episode_id,
        records=records,
        completed_count=sum(
            record.status is GenerationExecutionStatus.SUCCEEDED for record in records
        ),
        failed_count=sum(
            record.status is GenerationExecutionStatus.FAILED for record in records
        ),
        cancelled_count=sum(
            record.status is GenerationExecutionStatus.CANCELLED for record in records
        ),
        metadata={"dispatch_count": str(len(records))},
    )


def _validate_state_matches_plan(
    dispatch_plan: EpisodeGenerationDispatchPlan,
    state: EpisodeGenerationExecutionState,
) -> None:
    if state.dispatch_plan_id != dispatch_plan.dispatch_plan_id:
        raise GenerationExecutionTrackingError(
            "execution state does not belong to dispatch plan"
        )
    expected_ids = tuple(dispatch.dispatch_id for dispatch in dispatch_plan.dispatches)
    actual_ids = tuple(record.dispatch_id for record in state.records)
    if actual_ids != expected_ids:
        raise GenerationExecutionTrackingError(
            "execution records must match dispatch plan order"
        )


def _validate_status_payload(
    status: GenerationExecutionStatus,
    provider_job_id: str | None,
    output_asset_ids: tuple[str, ...],
    error_code: str | None,
    error_message: str | None,
) -> None:
    if status in {
        GenerationExecutionStatus.SUBMITTED,
        GenerationExecutionStatus.RUNNING,
        GenerationExecutionStatus.SUCCEEDED,
    } and provider_job_id is None:
        raise GenerationExecutionTrackingError(
            f"provider_job_id is required for {status.value} status"
        )
    if status is GenerationExecutionStatus.SUCCEEDED and not output_asset_ids:
        raise GenerationExecutionTrackingError(
            "output_asset_ids are required for succeeded status"
        )
    if status is GenerationExecutionStatus.FAILED and error_code is None:
        raise GenerationExecutionTrackingError(
            "error_code is required for failed status"
        )
    if status is not GenerationExecutionStatus.FAILED and (
        error_code is not None or error_message is not None
    ):
        raise GenerationExecutionTrackingError(
            "error details are allowed only for failed status"
        )
    if status is not GenerationExecutionStatus.SUCCEEDED and output_asset_ids:
        raise GenerationExecutionTrackingError(
            "output_asset_ids are allowed only for succeeded status"
        )


def _canonical_state_material(
    dispatch_plan: EpisodeGenerationDispatchPlan,
    records: tuple[GenerationDispatchExecution, ...],
) -> str:
    lines = [f"dispatch_plan_id={dispatch_plan.dispatch_plan_id}"]
    lines.extend(
        f"dispatch_id={record.dispatch_id}|status={record.status.value}|"
        f"revision={record.revision}|provider_job_id={record.provider_job_id or ''}|"
        f"outputs={','.join(record.output_asset_ids)}|"
        f"error_code={record.error_code or ''}"
        for record in records
    )
    return "\n".join(lines)


def _freeze_metadata(metadata: Mapping[str, str]) -> Mapping[str, str]:
    normalized = dict(metadata)
    for key, value in normalized.items():
        _require_non_blank("metadata key", key)
        _require_non_blank(f"metadata value for {key}", value)
    return MappingProxyType(normalized)


def _validate_unique_non_blank_values(name: str, values: tuple[str, ...]) -> None:
    for value in values:
        _require_non_blank(name, value)
    if len(values) != len(set(values)):
        raise GenerationExecutionTrackingError(f"{name} must be unique")


def _validate_optional_non_blank(name: str, value: str | None) -> None:
    if value is not None:
        _require_non_blank(name, value)


def _require_non_blank(name: str, value: str) -> None:
    if not value.strip():
        raise GenerationExecutionTrackingError(f"{name} must not be blank")
