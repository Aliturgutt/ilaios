"""Deterministic domain models for ILAIOS Video Automation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import TypeAlias

MetadataValue: TypeAlias = str | int | float | bool | None


def _validate_text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")


def _freeze_metadata(
    metadata: Mapping[str, MetadataValue],
) -> Mapping[str, MetadataValue]:
    normalized: dict[str, MetadataValue] = {}
    for key, value in metadata.items():
        _validate_text("metadata key", key)
        normalized[key] = value
    return MappingProxyType(dict(sorted(normalized.items())))


def _validate_utc_datetime(name: str, value: datetime) -> None:
    offset = value.utcoffset()
    if value.tzinfo is None or offset is None:
        raise ValueError(f"{name} must be timezone-aware")
    if offset.total_seconds() != 0:
        raise ValueError(f"{name} must use UTC")


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class VideoFormat(Enum):
    """Canonical output form factor."""

    SHORT_FORM = "short_form"
    LONG_FORM = "long_form"


class MediaType(Enum):
    """Canonical media asset classifications."""

    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"
    VOICE = "voice"
    MUSIC = "music"
    SOUND_EFFECT = "sound_effect"
    SUBTITLE = "subtitle"
    OVERLAY = "overlay"


class JobState(Enum):
    """Canonical asynchronous job states."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_PROVIDER = "WAITING_PROVIDER"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRY_PENDING = "RETRY_PENDING"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class VideoJob:
    """Immutable input contract for one video-production job."""

    job_id: str
    project_id: str
    topic: str
    objective: str
    target_audience: str
    target_platforms: tuple[str, ...]
    language: str
    desired_duration_seconds: int
    video_format: VideoFormat
    aspect_ratio: str
    content_style: str
    publishing_strategy: str
    provider_policy: str
    budget_policy: str
    approval_policy: str
    created_at: datetime

    def __post_init__(self) -> None:
        for name in (
            "job_id",
            "project_id",
            "topic",
            "objective",
            "target_audience",
            "language",
            "aspect_ratio",
            "content_style",
            "publishing_strategy",
            "provider_policy",
            "budget_policy",
            "approval_policy",
        ):
            _validate_text(name, getattr(self, name))

        if self.desired_duration_seconds <= 0:
            raise ValueError("desired_duration_seconds must be greater than 0")
        if not self.target_platforms:
            raise ValueError("target_platforms must not be empty")

        seen: set[str] = set()
        for platform in self.target_platforms:
            _validate_text("target platform", platform)
            if platform in seen:
                raise ValueError(f"duplicate target platform: {platform}")
            seen.add(platform)

        _validate_utc_datetime("created_at", self.created_at)


@dataclass(frozen=True, slots=True)
class ResearchPacket:
    """Structured, auditable research result."""

    job_id: str
    topic_summary: str
    verified_facts: tuple[str, ...]
    source_references: tuple[str, ...]
    key_claims: tuple[str, ...] = ()
    statistics: tuple[str, ...] = ()
    relevant_dates: tuple[str, ...] = ()
    entities: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    uncertain_claims: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_text("job_id", self.job_id)
        _validate_text("topic_summary", self.topic_summary)
        for field_name in (
            "verified_facts",
            "source_references",
            "key_claims",
            "statistics",
            "relevant_dates",
            "entities",
            "risks",
            "uncertain_claims",
        ):
            for value in getattr(self, field_name):
                _validate_text(field_name, value)


@dataclass(frozen=True, slots=True)
class ScriptSection:
    """One stable section of a generated video script."""

    section_id: str
    title: str
    narration: str
    on_screen_text: str | None = None
    estimated_duration_seconds: int = 0

    def __post_init__(self) -> None:
        _validate_text("section_id", self.section_id)
        _validate_text("title", self.title)
        _validate_text("narration", self.narration)
        if self.on_screen_text is not None:
            _validate_text("on_screen_text", self.on_screen_text)
        if self.estimated_duration_seconds < 0:
            raise ValueError("estimated_duration_seconds must be >= 0")


@dataclass(frozen=True, slots=True)
class VideoScript:
    """Structured script consumed by scene planning."""

    job_id: str
    hook: str
    introduction: str
    sections: tuple[ScriptSection, ...]
    cta: str | None
    ending: str
    estimated_duration_seconds: int

    def __post_init__(self) -> None:
        _validate_text("job_id", self.job_id)
        _validate_text("hook", self.hook)
        _validate_text("introduction", self.introduction)
        _validate_text("ending", self.ending)
        if self.cta is not None:
            _validate_text("cta", self.cta)
        if not self.sections:
            raise ValueError("sections must not be empty")
        if self.estimated_duration_seconds <= 0:
            raise ValueError("estimated_duration_seconds must be greater than 0")

        section_ids = [section.section_id for section in self.sections]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("script section identifiers must be unique")


@dataclass(frozen=True, slots=True)
class Scene:
    """Logical scene derived from a script section."""

    scene_id: str
    script_reference: str
    purpose: str
    duration_seconds: float
    visual_description: str
    narration_reference: str
    transition_intent: str
    required_asset_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "scene_id",
            "script_reference",
            "purpose",
            "visual_description",
            "narration_reference",
            "transition_intent",
        ):
            _validate_text(name, getattr(self, name))
        if self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be greater than 0")


@dataclass(frozen=True, slots=True)
class Shot:
    """Executable visual unit belonging to a scene."""

    shot_id: str
    scene_id: str
    shot_type: str
    camera_description: str
    subject: str
    action: str
    environment: str
    framing: str
    movement: str
    estimated_duration_seconds: float
    generation_prompt: str
    required_provider_capability: str

    def __post_init__(self) -> None:
        for name in (
            "shot_id",
            "scene_id",
            "shot_type",
            "camera_description",
            "subject",
            "action",
            "environment",
            "framing",
            "movement",
            "generation_prompt",
            "required_provider_capability",
        ):
            _validate_text(name, getattr(self, name))
        if self.estimated_duration_seconds <= 0:
            raise ValueError("estimated_duration_seconds must be greater than 0")


@dataclass(frozen=True, slots=True)
class AssetRequest:
    """Request for one required media asset."""

    asset_request_id: str
    job_id: str
    shot_id: str
    media_type: MediaType
    description: str
    required_capability: str
    metadata: Mapping[str, MetadataValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "asset_request_id",
            "job_id",
            "shot_id",
            "description",
            "required_capability",
        ):
            _validate_text(name, getattr(self, name))
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class MediaAsset:
    """Normalized reference to an acquired/generated asset."""

    asset_id: str
    job_id: str
    media_type: MediaType
    file_path: str
    checksum_sha256: str
    provider_name: str
    source_reference: str
    validated: bool = False

    def __post_init__(self) -> None:
        for name in (
            "asset_id",
            "job_id",
            "file_path",
            "checksum_sha256",
            "provider_name",
            "source_reference",
        ):
            _validate_text(name, getattr(self, name))
        if len(self.checksum_sha256) != 64:
            raise ValueError("checksum_sha256 must contain 64 hexadecimal characters")
        try:
            int(self.checksum_sha256, 16)
        except ValueError as exc:
            raise ValueError(
                "checksum_sha256 must contain 64 hexadecimal characters"
            ) from exc


@dataclass(frozen=True, slots=True)
class TimelineItem:
    """One deterministic item positioned on the composition timeline."""

    item_id: str
    asset_id: str
    start_seconds: float
    duration_seconds: float
    layer: int

    def __post_init__(self) -> None:
        _validate_text("item_id", self.item_id)
        _validate_text("asset_id", self.asset_id)
        if self.start_seconds < 0:
            raise ValueError("start_seconds must be >= 0")
        if self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be greater than 0")
        if self.layer < 0:
            raise ValueError("layer must be >= 0")


@dataclass(frozen=True, slots=True)
class Timeline:
    """Canonical composition timeline."""

    job_id: str
    items: tuple[TimelineItem, ...]

    def __post_init__(self) -> None:
        _validate_text("job_id", self.job_id)
        if not self.items:
            raise ValueError("items must not be empty")
        item_ids = [item.item_id for item in self.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("timeline item identifiers must be unique")


@dataclass(frozen=True, slots=True)
class RenderArtifact:
    """Technical metadata for a final rendered media artifact."""

    artifact_id: str
    job_id: str
    file_path: str
    checksum_sha256: str
    codec: str
    resolution: str
    duration_seconds: float
    fps: float
    audio_codec: str
    aspect_ratio: str
    size_bytes: int

    def __post_init__(self) -> None:
        for name in (
            "artifact_id",
            "job_id",
            "file_path",
            "checksum_sha256",
            "codec",
            "resolution",
            "audio_codec",
            "aspect_ratio",
        ):
            _validate_text(name, getattr(self, name))
        if self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be greater than 0")
        if self.fps <= 0:
            raise ValueError("fps must be greater than 0")
        if self.size_bytes <= 0:
            raise ValueError("size_bytes must be greater than 0")
        if len(self.checksum_sha256) != 64:
            raise ValueError("checksum_sha256 must contain 64 hexadecimal characters")
        try:
            int(self.checksum_sha256, 16)
        except ValueError as exc:
            raise ValueError(
                "checksum_sha256 must contain 64 hexadecimal characters"
            ) from exc


@dataclass(frozen=True, slots=True)
class PublishJob:
    """One platform-specific publishing request."""

    publish_job_id: str
    job_id: str
    platform: str
    account_id: str
    artifact_id: str
    scheduled_at: datetime
    metadata: Mapping[str, MetadataValue] = field(default_factory=dict)
    state: JobState = JobState.PENDING
    retry_count: int = 0

    def __post_init__(self) -> None:
        for name in (
            "publish_job_id",
            "job_id",
            "platform",
            "account_id",
            "artifact_id",
        ):
            _validate_text(name, getattr(self, name))
        _validate_utc_datetime("scheduled_at", self.scheduled_at)
        if self.retry_count < 0:
            raise ValueError("retry_count must be >= 0")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    """Provider-neutral request envelope."""

    request_id: str
    job_id: str
    provider_name: str
    operation: str
    payload: Mapping[str, MetadataValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("request_id", "job_id", "provider_name", "operation"):
            _validate_text(name, getattr(self, name))
        object.__setattr__(self, "payload", _freeze_metadata(self.payload))


@dataclass(frozen=True, slots=True)
class ProviderResult:
    """Provider-neutral result envelope."""

    request_id: str
    provider_name: str
    success: bool
    external_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    metadata: Mapping[str, MetadataValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_text("request_id", self.request_id)
        _validate_text("provider_name", self.provider_name)
        for name in ("external_id", "error_code", "error_message"):
            value = getattr(self, name)
            if value is not None:
                _validate_text(name, value)
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("successful provider result must not contain an error")
        if not self.success and self.error_message is None:
            raise ValueError("failed provider result requires error_message")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Deterministic validation outcome."""

    validator: str
    passed: bool
    messages: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_text("validator", self.validator)
        for message in self.messages:
            _validate_text("validation message", message)


@dataclass(frozen=True, slots=True)
class CostRecord:
    """Cost evidence for one provider operation."""

    job_id: str
    provider: str
    operation: str
    estimated_cost: float
    actual_cost: float | None
    currency: str
    timestamp: datetime

    def __post_init__(self) -> None:
        for name in ("job_id", "provider", "operation", "currency"):
            _validate_text(name, getattr(self, name))
        if self.estimated_cost < 0:
            raise ValueError("estimated_cost must be >= 0")
        if self.actual_cost is not None and self.actual_cost < 0:
            raise ValueError("actual_cost must be >= 0")
        _validate_utc_datetime("timestamp", self.timestamp)


@dataclass(frozen=True, slots=True)
class JobStateRecord:
    """Auditable record of one job-state transition."""

    job_id: str
    previous_state: JobState | None
    new_state: JobState
    reason: str
    timestamp: datetime

    def __post_init__(self) -> None:
        _validate_text("job_id", self.job_id)
        _validate_text("reason", self.reason)
        _validate_utc_datetime("timestamp", self.timestamp)
        if self.previous_state is self.new_state:
            raise ValueError("job-state transition must change state")
