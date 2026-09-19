"""Deterministic episode-level manifests for planned shot requests.

This module groups already-approved :class:`ShotGenerationRequest` objects into
an immutable, auditable execution manifest. It does not select providers, call
external services, render media, retry work, or reorder requests implicitly.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from types import MappingProxyType

from .shot_request_planning import ShotGenerationRequest


class RequestManifestError(ValueError):
    """Raised when shot requests cannot form a valid episode manifest."""


class CaptionMode(str, Enum):
    """User-facing subtitle policy carried through the production manifest.

    OFF means no caption/subtitle stage may be forced. ON means captions are an
    explicit deliverable. AUTO permits the canonical orchestrator to enable
    captions only when product intent, dialogue/accessibility requirements, or a
    downstream delivery profile explicitly calls for them.
    """

    OFF = "off"
    AUTO = "auto"
    ON = "on"


@dataclass(frozen=True, slots=True)
class ShotRequestEntry:
    """Ordered reference to one planned shot-generation request."""

    sequence_number: int
    request: ShotGenerationRequest

    def __post_init__(self) -> None:
        if self.sequence_number <= 0:
            raise RequestManifestError("sequence_number must be greater than zero")


@dataclass(frozen=True, slots=True)
class EpisodeRequestManifest:
    """Immutable provider-neutral request manifest for one episode."""

    manifest_id: str
    episode_id: str
    entries: tuple[ShotRequestEntry, ...]
    total_duration_seconds: float
    request_count: int
    metadata: Mapping[str, str]
    caption_mode: CaptionMode = CaptionMode.OFF

    def __post_init__(self) -> None:
        _require_non_blank("manifest_id", self.manifest_id)
        _require_non_blank("episode_id", self.episode_id)
        if not self.entries:
            raise RequestManifestError("entries must not be empty")
        if self.request_count != len(self.entries):
            raise RequestManifestError("request_count must equal entries length")
        if self.total_duration_seconds <= 0:
            raise RequestManifestError(
                "total_duration_seconds must be greater than zero"
            )
        if not isinstance(self.caption_mode, CaptionMode):
            raise RequestManifestError("caption_mode must be a CaptionMode")
        _validate_entries(self.entries)
        normalized = dict(self.metadata)
        for key, value in normalized.items():
            _require_non_blank("metadata key", key)
            _require_non_blank(f"metadata value for {key}", value)
        object.__setattr__(self, "metadata", MappingProxyType(normalized))

    @property
    def captions_explicitly_required(self) -> bool:
        """True only when the user/product contract explicitly requests captions."""

        return self.caption_mode is CaptionMode.ON

    @property
    def captions_explicitly_disabled(self) -> bool:
        """True when downstream orchestration must skip caption production."""

        return self.caption_mode is CaptionMode.OFF


class EpisodeRequestManifestBuilder:
    """Build stable episode manifests without provider selection or I/O."""

    def build(
        self,
        episode_id: str,
        requests: Sequence[ShotGenerationRequest],
        *,
        caption_mode: CaptionMode = CaptionMode.OFF,
    ) -> EpisodeRequestManifest:
        """Preserve request order and the explicit subtitle preference."""

        _require_non_blank("episode_id", episode_id)
        if not requests:
            raise RequestManifestError("requests must not be empty")
        if not isinstance(caption_mode, CaptionMode):
            raise RequestManifestError("caption_mode must be a CaptionMode")

        entries = tuple(
            ShotRequestEntry(sequence_number=index, request=request)
            for index, request in enumerate(requests, start=1)
        )
        _validate_entries(entries)
        canonical = _canonical_manifest_material(
            episode_id,
            entries,
            caption_mode=caption_mode,
        )
        digest = sha256(canonical.encode("utf-8")).hexdigest()
        total_duration = sum(entry.request.duration_seconds for entry in entries)
        metadata = {
            "first_shot_id": entries[0].request.shot_id,
            "last_shot_id": entries[-1].request.shot_id,
            "request_keys_sha256": sha256(
                "\n".join(entry.request.idempotency_key for entry in entries).encode(
                    "utf-8"
                )
            ).hexdigest(),
            "caption_mode": caption_mode.value,
        }
        return EpisodeRequestManifest(
            manifest_id=f"episode-manifest-{digest[:16]}",
            episode_id=episode_id,
            entries=entries,
            total_duration_seconds=total_duration,
            request_count=len(entries),
            metadata=metadata,
            caption_mode=caption_mode,
        )


def _validate_entries(entries: tuple[ShotRequestEntry, ...]) -> None:
    expected_sequence = tuple(range(1, len(entries) + 1))
    actual_sequence = tuple(entry.sequence_number for entry in entries)
    if actual_sequence != expected_sequence:
        raise RequestManifestError(
            "entry sequence_numbers must be contiguous and start at one"
        )

    request_ids = [entry.request.request_id for entry in entries]
    if len(request_ids) != len(set(request_ids)):
        raise RequestManifestError("request_id values must be unique")

    shot_ids = [entry.request.shot_id for entry in entries]
    if len(shot_ids) != len(set(shot_ids)):
        raise RequestManifestError("shot_id values must be unique")

    idempotency_keys = [entry.request.idempotency_key for entry in entries]
    if len(idempotency_keys) != len(set(idempotency_keys)):
        raise RequestManifestError("idempotency_key values must be unique")


def _canonical_manifest_material(
    episode_id: str,
    entries: tuple[ShotRequestEntry, ...],
    *,
    caption_mode: CaptionMode,
) -> str:
    lines = [f"episode_id={episode_id}", f"caption_mode={caption_mode.value}"]
    lines.extend(
        "|".join(
            (
                f"sequence={entry.sequence_number}",
                f"request_id={entry.request.request_id}",
                f"shot_id={entry.request.shot_id}",
                f"idempotency_key={entry.request.idempotency_key}",
                f"duration_seconds={_format_duration(entry.request.duration_seconds)}",
            )
        )
        for entry in entries
    )
    return "\n".join(lines)


def _format_duration(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _require_non_blank(name: str, value: str) -> None:
    if not value.strip():
        raise RequestManifestError(f"{name} must not be blank")
