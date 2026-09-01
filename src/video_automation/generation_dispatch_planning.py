"""Deterministic dispatch contracts for approved generation batches.

This module binds an approved generation batch plan to an explicitly supplied
provider configuration and produces immutable dispatch contracts. It does not
select providers, call external services, generate media, retry work, or infer
creative content.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType

from .generation_batch_planning import EpisodeGenerationBatchPlan, GenerationBatch
from .request_manifest import ShotRequestEntry


class GenerationDispatchPlanningError(ValueError):
    """Raised when a generation batch plan cannot form valid dispatches."""


@dataclass(frozen=True, slots=True)
class GenerationProviderBinding:
    """Explicit provider and model binding supplied by the caller."""

    provider_id: str
    model_id: str
    operation: str = "video.generate"
    max_parallel_requests: int = 1

    def __post_init__(self) -> None:
        _require_non_blank("provider_id", self.provider_id)
        _require_non_blank("model_id", self.model_id)
        _require_non_blank("operation", self.operation)
        if self.max_parallel_requests <= 0:
            raise GenerationDispatchPlanningError(
                "max_parallel_requests must be greater than zero"
            )


@dataclass(frozen=True, slots=True)
class GenerationDispatchItem:
    """One immutable provider-neutral request entry inside a dispatch."""

    sequence_number: int
    request_id: str
    idempotency_key: str
    shot_id: str
    prompt_text: str
    duration_seconds: float
    aspect_ratio: str
    frames_per_second: int
    output_count: int
    seed: int | None

    def __post_init__(self) -> None:
        if self.sequence_number <= 0:
            raise GenerationDispatchPlanningError(
                "sequence_number must be greater than zero"
            )
        _require_non_blank("request_id", self.request_id)
        _require_non_blank("idempotency_key", self.idempotency_key)
        _require_non_blank("shot_id", self.shot_id)
        _require_non_blank("prompt_text", self.prompt_text)
        _require_non_blank("aspect_ratio", self.aspect_ratio)
        if self.duration_seconds <= 0:
            raise GenerationDispatchPlanningError(
                "duration_seconds must be greater than zero"
            )
        if self.frames_per_second <= 0:
            raise GenerationDispatchPlanningError(
                "frames_per_second must be greater than zero"
            )
        if self.output_count <= 0:
            raise GenerationDispatchPlanningError(
                "output_count must be greater than zero"
            )
        if self.seed is not None and self.seed < 0:
            raise GenerationDispatchPlanningError("seed must be zero or greater")


@dataclass(frozen=True, slots=True)
class GenerationBatchDispatch:
    """One immutable dispatch contract for one approved generation batch."""

    dispatch_id: str
    batch_id: str
    batch_number: int
    provider_id: str
    model_id: str
    operation: str
    max_parallel_requests: int
    items: tuple[GenerationDispatchItem, ...]
    metadata: Mapping[str, str]

    def __post_init__(self) -> None:
        _require_non_blank("dispatch_id", self.dispatch_id)
        _require_non_blank("batch_id", self.batch_id)
        if self.batch_number <= 0:
            raise GenerationDispatchPlanningError(
                "batch_number must be greater than zero"
            )
        _require_non_blank("provider_id", self.provider_id)
        _require_non_blank("model_id", self.model_id)
        _require_non_blank("operation", self.operation)
        if self.max_parallel_requests <= 0:
            raise GenerationDispatchPlanningError(
                "max_parallel_requests must be greater than zero"
            )
        if not self.items:
            raise GenerationDispatchPlanningError("items must not be empty")
        _validate_item_order(self.items)
        normalized = dict(self.metadata)
        for key, value in normalized.items():
            _require_non_blank("metadata key", key)
            _require_non_blank(f"metadata value for {key}", value)
        object.__setattr__(self, "metadata", MappingProxyType(normalized))


@dataclass(frozen=True, slots=True)
class EpisodeGenerationDispatchPlan:
    """Ordered dispatch contracts for one episode generation plan."""

    dispatch_plan_id: str
    generation_plan_id: str
    manifest_id: str
    episode_id: str
    dispatches: tuple[GenerationBatchDispatch, ...]
    dispatch_count: int
    request_count: int
    metadata: Mapping[str, str]

    def __post_init__(self) -> None:
        _require_non_blank("dispatch_plan_id", self.dispatch_plan_id)
        _require_non_blank("generation_plan_id", self.generation_plan_id)
        _require_non_blank("manifest_id", self.manifest_id)
        _require_non_blank("episode_id", self.episode_id)
        if not self.dispatches:
            raise GenerationDispatchPlanningError("dispatches must not be empty")
        if self.dispatch_count != len(self.dispatches):
            raise GenerationDispatchPlanningError(
                "dispatch_count must equal dispatches length"
            )
        actual_request_count = sum(
            len(dispatch.items) for dispatch in self.dispatches
        )
        if self.request_count != actual_request_count:
            raise GenerationDispatchPlanningError(
                "request_count must equal dispatched item count"
            )
        expected_numbers = tuple(range(1, len(self.dispatches) + 1))
        actual_numbers = tuple(
            dispatch.batch_number for dispatch in self.dispatches
        )
        if actual_numbers != expected_numbers:
            raise GenerationDispatchPlanningError(
                "dispatch batch_numbers must be contiguous and start at one"
            )
        normalized = dict(self.metadata)
        for key, value in normalized.items():
            _require_non_blank("metadata key", key)
            _require_non_blank(f"metadata value for {key}", value)
        object.__setattr__(self, "metadata", MappingProxyType(normalized))


class EpisodeGenerationDispatchPlanner:
    """Bind approved batches to an explicit provider without executing them."""

    def __init__(self, binding: GenerationProviderBinding) -> None:
        self._binding = binding

    def plan(
        self, generation_plan: EpisodeGenerationBatchPlan
    ) -> EpisodeGenerationDispatchPlan:
        """Create stable dispatch contracts without external provider calls."""

        dispatches = tuple(
            self._build_dispatch(generation_plan, batch)
            for batch in generation_plan.batches
        )
        canonical = _canonical_dispatch_plan_material(
            generation_plan, self._binding, dispatches
        )
        digest = sha256(canonical.encode("utf-8")).hexdigest()
        metadata = {
            "provider_id": self._binding.provider_id,
            "model_id": self._binding.model_id,
            "operation": self._binding.operation,
        }
        return EpisodeGenerationDispatchPlan(
            dispatch_plan_id=f"dispatch-plan-{digest[:16]}",
            generation_plan_id=generation_plan.plan_id,
            manifest_id=generation_plan.manifest_id,
            episode_id=generation_plan.episode_id,
            dispatches=dispatches,
            dispatch_count=len(dispatches),
            request_count=generation_plan.request_count,
            metadata=metadata,
        )

    def _build_dispatch(
        self,
        generation_plan: EpisodeGenerationBatchPlan,
        batch: GenerationBatch,
    ) -> GenerationBatchDispatch:
        items = tuple(_to_dispatch_item(entry) for entry in batch.entries)
        canonical = _canonical_dispatch_material(
            generation_plan.plan_id, batch, self._binding, items
        )
        digest = sha256(canonical.encode("utf-8")).hexdigest()
        metadata = {
            "generation_plan_id": generation_plan.plan_id,
            "manifest_id": generation_plan.manifest_id,
            "episode_id": generation_plan.episode_id,
        }
        return GenerationBatchDispatch(
            dispatch_id=f"generation-dispatch-{digest[:16]}",
            batch_id=batch.batch_id,
            batch_number=batch.batch_number,
            provider_id=self._binding.provider_id,
            model_id=self._binding.model_id,
            operation=self._binding.operation,
            max_parallel_requests=self._binding.max_parallel_requests,
            items=items,
            metadata=metadata,
        )


def _to_dispatch_item(entry: ShotRequestEntry) -> GenerationDispatchItem:
    request = entry.request
    return GenerationDispatchItem(
        sequence_number=entry.sequence_number,
        request_id=request.request_id,
        idempotency_key=request.idempotency_key,
        shot_id=request.shot_id,
        prompt_text=request.prompt_text,
        duration_seconds=request.duration_seconds,
        aspect_ratio=request.aspect_ratio,
        frames_per_second=request.frames_per_second,
        output_count=request.output_count,
        seed=request.seed,
    )


def _validate_item_order(items: tuple[GenerationDispatchItem, ...]) -> None:
    sequence_numbers = tuple(item.sequence_number for item in items)
    if sequence_numbers != tuple(sorted(sequence_numbers)):
        raise GenerationDispatchPlanningError(
            "items must preserve ascending manifest sequence order"
        )
    if len(sequence_numbers) != len(set(sequence_numbers)):
        raise GenerationDispatchPlanningError(
            "item sequence_numbers must be unique"
        )


def _canonical_dispatch_material(
    generation_plan_id: str,
    batch: GenerationBatch,
    binding: GenerationProviderBinding,
    items: tuple[GenerationDispatchItem, ...],
) -> str:
    lines = [
        f"generation_plan_id={generation_plan_id}",
        f"batch_id={batch.batch_id}",
        f"provider_id={binding.provider_id}",
        f"model_id={binding.model_id}",
        f"operation={binding.operation}",
        f"max_parallel_requests={binding.max_parallel_requests}",
    ]
    lines.extend(
        f"sequence={item.sequence_number}|request_id={item.request_id}|"
        f"idempotency_key={item.idempotency_key}"
        for item in items
    )
    return "\n".join(lines)


def _canonical_dispatch_plan_material(
    generation_plan: EpisodeGenerationBatchPlan,
    binding: GenerationProviderBinding,
    dispatches: tuple[GenerationBatchDispatch, ...],
) -> str:
    lines = [
        f"generation_plan_id={generation_plan.plan_id}",
        f"provider_id={binding.provider_id}",
        f"model_id={binding.model_id}",
        f"operation={binding.operation}",
    ]
    lines.extend(
        f"batch_number={dispatch.batch_number}|dispatch_id={dispatch.dispatch_id}"
        for dispatch in dispatches
    )
    return "\n".join(lines)


def _require_non_blank(name: str, value: str) -> None:
    if not value.strip():
        raise GenerationDispatchPlanningError(f"{name} must not be blank")
