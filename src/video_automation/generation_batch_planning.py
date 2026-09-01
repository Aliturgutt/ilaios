"""Deterministic batch planning for episode shot-generation manifests.

This module partitions an approved :class:`EpisodeRequestManifest` into
immutable execution batches while preserving manifest order. It does not
select providers, call external services, render media, retry work, or mutate
requests.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType

from .request_manifest import EpisodeRequestManifest, ShotRequestEntry


class GenerationBatchPlanningError(ValueError):
    """Raised when a request manifest cannot form a valid batch plan."""


@dataclass(frozen=True, slots=True)
class GenerationBatchPolicy:
    """Explicit deterministic limits for grouping manifest requests."""

    max_requests_per_batch: int = 4

    def __post_init__(self) -> None:
        if self.max_requests_per_batch <= 0:
            raise GenerationBatchPlanningError(
                "max_requests_per_batch must be greater than zero"
            )


@dataclass(frozen=True, slots=True)
class GenerationBatch:
    """One ordered immutable batch of manifest entries."""

    batch_id: str
    batch_number: int
    entries: tuple[ShotRequestEntry, ...]
    total_duration_seconds: float

    def __post_init__(self) -> None:
        _require_non_blank("batch_id", self.batch_id)
        if self.batch_number <= 0:
            raise GenerationBatchPlanningError("batch_number must be greater than zero")
        if not self.entries:
            raise GenerationBatchPlanningError("entries must not be empty")
        if self.total_duration_seconds <= 0:
            raise GenerationBatchPlanningError(
                "total_duration_seconds must be greater than zero"
            )
        _validate_entry_order(self.entries)


@dataclass(frozen=True, slots=True)
class EpisodeGenerationBatchPlan:
    """Provider-neutral execution batches for one episode manifest."""

    plan_id: str
    manifest_id: str
    episode_id: str
    batches: tuple[GenerationBatch, ...]
    batch_count: int
    request_count: int
    total_duration_seconds: float
    metadata: Mapping[str, str]

    def __post_init__(self) -> None:
        _require_non_blank("plan_id", self.plan_id)
        _require_non_blank("manifest_id", self.manifest_id)
        _require_non_blank("episode_id", self.episode_id)
        if not self.batches:
            raise GenerationBatchPlanningError("batches must not be empty")
        if self.batch_count != len(self.batches):
            raise GenerationBatchPlanningError("batch_count must equal batches length")
        actual_request_count = sum(len(batch.entries) for batch in self.batches)
        if self.request_count != actual_request_count:
            raise GenerationBatchPlanningError(
                "request_count must equal the number of batched entries"
            )
        if self.total_duration_seconds <= 0:
            raise GenerationBatchPlanningError(
                "total_duration_seconds must be greater than zero"
            )
        expected_numbers = tuple(range(1, len(self.batches) + 1))
        actual_numbers = tuple(batch.batch_number for batch in self.batches)
        if actual_numbers != expected_numbers:
            raise GenerationBatchPlanningError(
                "batch_numbers must be contiguous and start at one"
            )
        normalized = dict(self.metadata)
        for key, value in normalized.items():
            _require_non_blank("metadata key", key)
            _require_non_blank(f"metadata value for {key}", value)
        object.__setattr__(self, "metadata", MappingProxyType(normalized))


class EpisodeGenerationBatchPlanner:
    """Partition approved manifests into stable ordered batches."""

    def __init__(self, policy: GenerationBatchPolicy | None = None) -> None:
        self._policy = policy or GenerationBatchPolicy()

    def plan(self, manifest: EpisodeRequestManifest) -> EpisodeGenerationBatchPlan:
        """Create deterministic batches without provider selection or I/O."""

        size = self._policy.max_requests_per_batch
        batches: list[GenerationBatch] = []
        for offset in range(0, len(manifest.entries), size):
            entries = manifest.entries[offset : offset + size]
            batch_number = len(batches) + 1
            canonical = _canonical_batch_material(manifest.manifest_id, batch_number, entries)
            digest = sha256(canonical.encode("utf-8")).hexdigest()
            batches.append(
                GenerationBatch(
                    batch_id=f"generation-batch-{digest[:16]}",
                    batch_number=batch_number,
                    entries=entries,
                    total_duration_seconds=sum(
                        entry.request.duration_seconds for entry in entries
                    ),
                )
            )

        batch_tuple = tuple(batches)
        canonical_plan = _canonical_plan_material(manifest, batch_tuple, size)
        plan_digest = sha256(canonical_plan.encode("utf-8")).hexdigest()
        metadata = {
            "first_request_id": manifest.entries[0].request.request_id,
            "last_request_id": manifest.entries[-1].request.request_id,
            "max_requests_per_batch": str(size),
        }
        return EpisodeGenerationBatchPlan(
            plan_id=f"generation-plan-{plan_digest[:16]}",
            manifest_id=manifest.manifest_id,
            episode_id=manifest.episode_id,
            batches=batch_tuple,
            batch_count=len(batch_tuple),
            request_count=manifest.request_count,
            total_duration_seconds=manifest.total_duration_seconds,
            metadata=metadata,
        )


def _validate_entry_order(entries: tuple[ShotRequestEntry, ...]) -> None:
    sequence_numbers = tuple(entry.sequence_number for entry in entries)
    if sequence_numbers != tuple(sorted(sequence_numbers)):
        raise GenerationBatchPlanningError(
            "entries must preserve ascending manifest sequence order"
        )
    if len(sequence_numbers) != len(set(sequence_numbers)):
        raise GenerationBatchPlanningError("entry sequence_numbers must be unique")


def _canonical_batch_material(
    manifest_id: str,
    batch_number: int,
    entries: tuple[ShotRequestEntry, ...],
) -> str:
    lines = [f"manifest_id={manifest_id}", f"batch_number={batch_number}"]
    lines.extend(
        f"sequence={entry.sequence_number}|request_id={entry.request.request_id}"
        for entry in entries
    )
    return "\n".join(lines)


def _canonical_plan_material(
    manifest: EpisodeRequestManifest,
    batches: tuple[GenerationBatch, ...],
    max_requests_per_batch: int,
) -> str:
    lines = [
        f"manifest_id={manifest.manifest_id}",
        f"episode_id={manifest.episode_id}",
        f"max_requests_per_batch={max_requests_per_batch}",
    ]
    lines.extend(
        f"batch_number={batch.batch_number}|batch_id={batch.batch_id}"
        for batch in batches
    )
    return "\n".join(lines)


def _require_non_blank(name: str, value: str) -> None:
    if not value.strip():
        raise GenerationBatchPlanningError(f"{name} must not be blank")
