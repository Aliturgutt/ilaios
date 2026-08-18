"""First-party ILAIOS Video Factory prompting and continuity primitives.

This module is independently authored for ILAIOS. It contains no provider SDK calls,
no provider-selection authority, no policy/approval authority, and no external side
effects. Provider choice remains owned by the canonical M05 ProviderSelectionEngine.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256

from .video_skills import VideoSkillError


class VideoInputMode(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    REFERENCE = "reference"
    FIRST_LAST_FRAME = "first_last_frame"
    SOURCE_EDIT = "source_edit"
    EXTEND = "extend"


class ReferenceRole(str, Enum):
    IDENTITY = "identity"
    WARDROBE = "wardrobe"
    PRODUCT = "product"
    ENVIRONMENT = "environment"
    OPENING_FRAME = "opening_frame"
    ENDING_FRAME = "ending_frame"
    MOTION = "motion"
    CAMERA = "camera"
    AUDIO = "audio"


def _clean(name: str, value: str) -> str:
    if not value or value != value.strip():
        raise VideoSkillError(f"{name} must be non-blank and trimmed")
    return value


def _unique(name: str, values: tuple[str, ...], *, allow_empty: bool = False) -> None:
    if not allow_empty and not values:
        raise VideoSkillError(f"{name} must not be empty")
    if len(values) != len(set(values)):
        raise VideoSkillError(f"{name} values must be unique")
    for value in values:
        _clean(name, value)


@dataclass(frozen=True, slots=True)
class VideoPromptBrief:
    brief_id: str
    objective: str
    input_mode: VideoInputMode
    duration_seconds: float
    visual_style: str
    required_beats: tuple[str, ...]
    audio_intent: str = "natural production sound"
    ending_state: str = "stable deliberate final frame"

    def __post_init__(self) -> None:
        for name in ("brief_id", "objective", "visual_style", "audio_intent", "ending_state"):
            _clean(name, getattr(self, name))
        if not 0 < self.duration_seconds <= 60:
            raise VideoSkillError("duration_seconds must be within (0, 60]")
        _unique("required_beats", self.required_beats)
        if len(self.required_beats) > 12:
            raise VideoSkillError("required_beats exceeds bounded planning limit")


@dataclass(frozen=True, slots=True)
class DirectedVideoBrief:
    brief_id: str
    objective: str
    input_mode: VideoInputMode
    duration_seconds: float
    visual_style: str
    beats: tuple[str, ...]
    camera_intent: str
    audio_intent: str
    ending_state: str
    continuity_keys: tuple[str, ...]


class VideoDirector:
    """Normalize creative intent into bounded provider-neutral direction."""

    def direct(
        self,
        brief: VideoPromptBrief,
        *,
        camera_intent: str,
        continuity_keys: tuple[str, ...],
    ) -> DirectedVideoBrief:
        _clean("camera_intent", camera_intent)
        _unique("continuity_keys", continuity_keys)
        return DirectedVideoBrief(
            brief_id=brief.brief_id,
            objective=brief.objective,
            input_mode=brief.input_mode,
            duration_seconds=brief.duration_seconds,
            visual_style=brief.visual_style,
            beats=brief.required_beats,
            camera_intent=camera_intent,
            audio_intent=brief.audio_intent,
            ending_state=brief.ending_state,
            continuity_keys=continuity_keys,
        )


@dataclass(frozen=True, slots=True)
class ReferenceAsset:
    asset_id: str
    role: ReferenceRole
    content_sha256: str
    controls: tuple[str, ...]
    exclusions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _clean("asset_id", self.asset_id)
        if len(self.content_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.content_sha256
        ):
            raise VideoSkillError("reference asset digest must be lowercase SHA-256")
        _unique("controls", self.controls)
        _unique("exclusions", self.exclusions, allow_empty=True)


@dataclass(frozen=True, slots=True)
class ReferencePlan:
    assets: tuple[ReferenceAsset, ...]
    immutable_asset_ids: tuple[str, ...]
    plan_sha256: str


class ReferenceAssetPlanner:
    """Validate reference roles without uploading, staging, or dispatching assets."""

    def plan(self, assets: tuple[ReferenceAsset, ...]) -> ReferencePlan:
        if not assets:
            raise VideoSkillError("reference planning requires at least one asset")
        if len(assets) > 20:
            raise VideoSkillError("reference planning exceeds Video Factory input bound")
        ids = tuple(item.asset_id for item in assets)
        digests = tuple(item.content_sha256 for item in assets)
        if len(ids) != len(set(ids)) or len(digests) != len(set(digests)):
            raise VideoSkillError("reference assets must have unique IDs and content")
        opening = [item for item in assets if item.role is ReferenceRole.OPENING_FRAME]
        ending = [item for item in assets if item.role is ReferenceRole.ENDING_FRAME]
        if len(opening) > 1 or len(ending) > 1:
            raise VideoSkillError("opening and ending frame roles are singular")
        material = "\n".join(
            f"{item.asset_id}|{item.role.value}|{item.content_sha256}|{','.join(item.controls)}|{','.join(item.exclusions)}"
            for item in assets
        )
        return ReferencePlan(
            assets=assets,
            immutable_asset_ids=ids,
            plan_sha256=sha256(material.encode("utf-8")).hexdigest(),
        )


@dataclass(frozen=True, slots=True)
class VideoModelCandidate:
    model_id: str
    supported_modes: frozenset[VideoInputMode]
    max_duration_seconds: float
    supports_audio: bool
    supports_reference_assets: bool
    supports_first_last_frame: bool

    def __post_init__(self) -> None:
        _clean("model_id", self.model_id)
        if self.max_duration_seconds <= 0:
            raise VideoSkillError("model max duration must be positive")
        if not self.supported_modes:
            raise VideoSkillError("model candidate requires at least one input mode")


@dataclass(frozen=True, slots=True)
class ModelRoutingRequest:
    input_mode: VideoInputMode
    duration_seconds: float
    require_audio: bool = False
    require_reference_assets: bool = False
    require_first_last_frame: bool = False


@dataclass(frozen=True, slots=True)
class ModelRoutingRecommendation:
    model_id: str
    reason: str
    advisory_only: bool = True


class VideoModelRoutingAdvisor:
    """Recommend a model capability match; never choose or invoke a provider."""

    def recommend(
        self,
        request: ModelRoutingRequest,
        candidates: tuple[VideoModelCandidate, ...],
    ) -> ModelRoutingRecommendation:
        if request.duration_seconds <= 0:
            raise VideoSkillError("routing duration must be positive")
        eligible = [
            candidate
            for candidate in candidates
            if request.input_mode in candidate.supported_modes
            and request.duration_seconds <= candidate.max_duration_seconds
            and (not request.require_audio or candidate.supports_audio)
            and (
                not request.require_reference_assets
                or candidate.supports_reference_assets
            )
            and (
                not request.require_first_last_frame
                or candidate.supports_first_last_frame
            )
        ]
        if not eligible:
            raise VideoSkillError("no model candidate satisfies requested capabilities")
        selected = sorted(eligible, key=lambda candidate: candidate.model_id)[0]
        return ModelRoutingRecommendation(
            model_id=selected.model_id,
            reason="deterministic capability match; canonical M05 still selects provider",
        )


@dataclass(frozen=True, slots=True)
class ContinuityBeat:
    index: int
    action: str
    inherited_state: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ContinuityPlan:
    brief_id: str
    continuity_keys: tuple[str, ...]
    beats: tuple[ContinuityBeat, ...]
    ending_state: str


class VideoContinuityPlanner:
    """Make state inheritance explicit across ordered video beats."""

    def plan(self, directed: DirectedVideoBrief) -> ContinuityPlan:
        beats = tuple(
            ContinuityBeat(index=index, action=action, inherited_state=directed.continuity_keys)
            for index, action in enumerate(directed.beats, start=1)
        )
        return ContinuityPlan(
            brief_id=directed.brief_id,
            continuity_keys=directed.continuity_keys,
            beats=beats,
            ending_state=directed.ending_state,
        )


@dataclass(frozen=True, slots=True)
class PromptPackage:
    brief_id: str
    prompt_text: str
    external_duration_seconds: float
    model_id: str | None
    reference_plan_sha256: str | None


class VideoPromptComposer:
    """Compose a provider-neutral production prompt from governed upstream plans."""

    def compose(
        self,
        directed: DirectedVideoBrief,
        continuity: ContinuityPlan,
        *,
        model_id: str | None = None,
        reference_plan: ReferencePlan | None = None,
    ) -> PromptPackage:
        if continuity.brief_id != directed.brief_id:
            raise VideoSkillError("continuity plan does not belong to directed brief")
        if continuity.continuity_keys != directed.continuity_keys:
            raise VideoSkillError("continuity keys drifted between planning stages")
        if model_id is not None:
            _clean("model_id", model_id)
        beat_text = " Then ".join(beat.action for beat in continuity.beats)
        invariants = ", ".join(continuity.continuity_keys)
        prompt = (
            f"{directed.visual_style}. Objective: {directed.objective}. "
            f"Camera: {directed.camera_intent}. Action progression: {beat_text}. "
            f"Preserve throughout: {invariants}. Audio: {directed.audio_intent}. "
            f"Finish on: {directed.ending_state}."
        )
        return PromptPackage(
            brief_id=directed.brief_id,
            prompt_text=prompt,
            external_duration_seconds=directed.duration_seconds,
            model_id=model_id,
            reference_plan_sha256=(
                None if reference_plan is None else reference_plan.plan_sha256
            ),
        )
