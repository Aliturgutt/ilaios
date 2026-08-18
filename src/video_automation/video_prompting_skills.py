"""Provider-neutral ILAIOS Video Factory prompting skill primitives.

These primitives prepare structured direction, prompts, reference roles, continuity
state, and model-routing advice. They do not select providers, invoke models,
mutate media, authorize spend, or bypass the canonical Video Factory governance
and M05 provider-selection boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Iterable


class VideoPromptSkillError(ValueError):
    """A provider-neutral Video Factory prompting contract is invalid."""


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise VideoPromptSkillError(f"{name} must be non-blank and trimmed")


def _unique_text(name: str, values: tuple[str, ...], *, allow_empty: bool = False) -> None:
    if not values and not allow_empty:
        raise VideoPromptSkillError(f"{name} must not be empty")
    for value in values:
        _text(name, value)
    if len(values) != len(set(values)):
        raise VideoPromptSkillError(f"{name} values must be unique")


def _digest(lines: Iterable[str]) -> str:
    return sha256("\n".join(lines).encode("utf-8")).hexdigest()


class VideoInputMode(str, Enum):
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    REFERENCE_TO_VIDEO = "reference_to_video"
    FIRST_LAST_FRAME = "first_last_frame"
    EDIT = "edit"
    EXTEND = "extend"


class PromptForm(str, Enum):
    SINGLE_SHOT = "single_shot"
    MULTI_SHOT = "multi_shot"
    TIMED_SEQUENCE = "timed_sequence"
    SCREENPLAY = "screenplay"


class ReferenceKind(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


@dataclass(frozen=True, slots=True)
class DirectorBrief:
    brief_id: str
    objective: str
    subject: str
    setting: str
    action_arc: tuple[str, ...]
    camera_intent: str
    visual_treatment: str
    audio_intent: str
    ending_state: str
    continuity_invariants: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "brief_id",
            "objective",
            "subject",
            "setting",
            "camera_intent",
            "visual_treatment",
            "audio_intent",
            "ending_state",
        ):
            _text(name, getattr(self, name))
        _unique_text("action_arc", self.action_arc)
        _unique_text("continuity_invariants", self.continuity_invariants)


@dataclass(frozen=True, slots=True)
class DirectorPlan:
    brief_id: str
    shot_intent: str
    action_arc: tuple[str, ...]
    camera_intent: str
    visual_treatment: str
    audio_intent: str
    ending_state: str
    continuity_invariants: tuple[str, ...]
    plan_sha256: str


class VideoDirector:
    """Normalize creative intent without creating provider or execution authority."""

    def plan(self, brief: DirectorBrief) -> DirectorPlan:
        shot_intent = f"{brief.subject} in {brief.setting}: {brief.objective}"
        digest = _digest(
            (
                brief.brief_id,
                shot_intent,
                *brief.action_arc,
                brief.camera_intent,
                brief.visual_treatment,
                brief.audio_intent,
                brief.ending_state,
                *brief.continuity_invariants,
            )
        )
        return DirectorPlan(
            brief.brief_id,
            shot_intent,
            brief.action_arc,
            brief.camera_intent,
            brief.visual_treatment,
            brief.audio_intent,
            brief.ending_state,
            brief.continuity_invariants,
            digest,
        )


@dataclass(frozen=True, slots=True)
class ReferenceDirective:
    reference_id: str
    kind: ReferenceKind
    controls: str
    preserve: tuple[str, ...]
    exclude: tuple[str, ...]
    content_sha256: str | None = None

    def __post_init__(self) -> None:
        _text("reference_id", self.reference_id)
        _text("controls", self.controls)
        _unique_text("preserve", self.preserve)
        _unique_text("exclude", self.exclude, allow_empty=True)
        if set(self.preserve) & set(self.exclude):
            raise VideoPromptSkillError("reference preserve/exclude rules must not conflict")
        if self.content_sha256 is not None:
            if len(self.content_sha256) != 64 or any(
                character not in "0123456789abcdef"
                for character in self.content_sha256
            ):
                raise VideoPromptSkillError(
                    "reference content_sha256 must be lowercase SHA-256"
                )


@dataclass(frozen=True, slots=True)
class ReferenceAssetPlan:
    directives: tuple[ReferenceDirective, ...]
    plan_sha256: str


class ReferenceAssetPlanner:
    """Bind semantic reference roles; never ingest, upload, or dispatch asset bytes."""

    def plan(self, directives: Iterable[ReferenceDirective]) -> ReferenceAssetPlan:
        items = tuple(directives)
        if not items:
            raise VideoPromptSkillError("reference plan requires at least one directive")
        ids = tuple(item.reference_id for item in items)
        if len(ids) != len(set(ids)):
            raise VideoPromptSkillError("reference_id values must be unique")
        digests = tuple(
            item.content_sha256 for item in items if item.content_sha256 is not None
        )
        if len(digests) != len(set(digests)):
            raise VideoPromptSkillError("reference content digests must be unique")
        ordered = tuple(sorted(items, key=lambda item: item.reference_id))
        digest = _digest(
            (
                part
                for item in ordered
                for part in (
                    item.reference_id,
                    item.kind.value,
                    item.controls,
                    *item.preserve,
                    "--exclude--",
                    *item.exclude,
                    item.content_sha256 or "",
                )
            )
        )
        return ReferenceAssetPlan(ordered, digest)


@dataclass(frozen=True, slots=True)
class ContinuityState:
    continuity_id: str
    invariants: tuple[str, ...]
    object_state: tuple[str, ...]
    screen_direction: tuple[str, ...]
    ending_state: str

    def __post_init__(self) -> None:
        _text("continuity_id", self.continuity_id)
        _unique_text("invariants", self.invariants)
        _unique_text("object_state", self.object_state, allow_empty=True)
        _unique_text("screen_direction", self.screen_direction, allow_empty=True)
        _text("ending_state", self.ending_state)

    @property
    def digest(self) -> str:
        return _digest(
            (
                self.continuity_id,
                *self.invariants,
                "--objects--",
                *self.object_state,
                "--direction--",
                *self.screen_direction,
                self.ending_state,
            )
        )


class ContinuityPlanner:
    """Create stable continuity state from explicit caller-provided invariants."""

    def build(
        self,
        *,
        continuity_id: str,
        invariants: Iterable[str],
        object_state: Iterable[str] = (),
        screen_direction: Iterable[str] = (),
        ending_state: str,
    ) -> ContinuityState:
        return ContinuityState(
            continuity_id,
            tuple(invariants),
            tuple(object_state),
            tuple(screen_direction),
            ending_state,
        )


@dataclass(frozen=True, slots=True)
class VideoPromptRequest:
    prompt_id: str
    input_mode: VideoInputMode
    form: PromptForm
    shot_intent: str
    action_arc: tuple[str, ...]
    camera_intent: str
    visual_treatment: str
    audio_intent: str
    ending_state: str
    continuity: ContinuityState | None = None
    references: ReferenceAssetPlan | None = None

    def __post_init__(self) -> None:
        for name in (
            "prompt_id",
            "shot_intent",
            "camera_intent",
            "visual_treatment",
            "audio_intent",
            "ending_state",
        ):
            _text(name, getattr(self, name))
        _unique_text("action_arc", self.action_arc)
        if self.input_mode in {
            VideoInputMode.REFERENCE_TO_VIDEO,
            VideoInputMode.FIRST_LAST_FRAME,
        } and self.references is None:
            raise VideoPromptSkillError(
                "reference-driven modes require an admitted reference plan"
            )


@dataclass(frozen=True, slots=True)
class VideoPromptResult:
    prompt_id: str
    prompt: str
    prompt_sha256: str


class VideoPromptComposer:
    """Compose a provider-neutral production note from already-admitted intent."""

    def compose(self, request: VideoPromptRequest) -> VideoPromptResult:
        sections: list[str] = []
        if request.input_mode is VideoInputMode.IMAGE_TO_VIDEO:
            sections.append(
                "OPENING ANCHOR: preserve the supplied first image as the authority "
                "for identity, wardrobe, environment, palette, and opening composition."
            )
        elif request.input_mode is VideoInputMode.FIRST_LAST_FRAME:
            sections.append(
                "FRAME PATH: begin from the admitted first-frame reference and converge "
                "on the admitted final-frame reference without resetting identity or state."
            )
        elif request.input_mode is VideoInputMode.EDIT:
            sections.append(
                "EDIT BOUNDARY: preserve successful identity, timing, camera, lighting, "
                "and scene state; change only the explicitly requested target."
            )
        elif request.input_mode is VideoInputMode.EXTEND:
            sections.append(
                "CONTINUATION BOUNDARY: preserve the completed prior state and begin with "
                "the first new action; do not replay completed action."
            )

        if request.references is not None:
            sections.append(
                "REFERENCE ROLES: "
                + " | ".join(
                    f"{item.reference_id} controls only {item.controls}; "
                    f"preserve {', '.join(item.preserve)}"
                    + (
                        f"; exclude {', '.join(item.exclude)}"
                        if item.exclude
                        else ""
                    )
                    for item in request.references.directives
                )
            )

        sections.extend(
            (
                f"SHOT: {request.shot_intent}",
                "ACTION: " + " -> ".join(request.action_arc),
                f"CAMERA: {request.camera_intent}",
                f"VISUAL: {request.visual_treatment}",
            )
        )
        if request.continuity is not None:
            continuity_bits = [*request.continuity.invariants]
            continuity_bits.extend(request.continuity.object_state)
            continuity_bits.extend(request.continuity.screen_direction)
            sections.append("CONTINUITY: " + " | ".join(continuity_bits))
        sections.extend(
            (
                f"AUDIO: {request.audio_intent}",
                f"ENDING STATE: {request.ending_state}",
            )
        )
        prompt = "\n".join(sections)
        _forbid_generation_controls(prompt)
        return VideoPromptResult(
            request.prompt_id,
            prompt,
            sha256(prompt.encode("utf-8")).hexdigest(),
        )


@dataclass(frozen=True, slots=True)
class ModelCapabilityProfile:
    model_id: str
    supported_modes: frozenset[VideoInputMode]
    supports_native_audio: bool
    supports_reference_assets: bool
    supports_multi_shot: bool
    supports_timed_sequence: bool

    def __post_init__(self) -> None:
        _text("model_id", self.model_id)
        if not self.supported_modes:
            raise VideoPromptSkillError("model profile requires supported_modes")


@dataclass(frozen=True, slots=True)
class ModelRoutingRequest:
    input_mode: VideoInputMode
    prompt_form: PromptForm
    requires_native_audio: bool = False
    requires_reference_assets: bool = False


@dataclass(frozen=True, slots=True)
class ModelRoutingAdvice:
    candidate_model_ids: tuple[str, ...]
    rationale: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.candidate_model_ids:
            raise VideoPromptSkillError("routing advice requires at least one candidate")
        if len(self.candidate_model_ids) != len(set(self.candidate_model_ids)):
            raise VideoPromptSkillError("routing candidates must be unique")
        if len(self.candidate_model_ids) != len(self.rationale):
            raise VideoPromptSkillError("routing rationale must align with candidates")


class ModelRoutingAdvisor:
    """Filter model capabilities only; canonical M05 still selects the provider."""

    def advise(
        self,
        request: ModelRoutingRequest,
        profiles: Iterable[ModelCapabilityProfile],
    ) -> ModelRoutingAdvice:
        candidates: list[tuple[str, str]] = []
        for profile in profiles:
            if request.input_mode not in profile.supported_modes:
                continue
            if request.requires_native_audio and not profile.supports_native_audio:
                continue
            if request.requires_reference_assets and not profile.supports_reference_assets:
                continue
            if (
                request.prompt_form is PromptForm.MULTI_SHOT
                and not profile.supports_multi_shot
            ):
                continue
            if (
                request.prompt_form is PromptForm.TIMED_SEQUENCE
                and not profile.supports_timed_sequence
            ):
                continue
            reasons = [f"supports {request.input_mode.value}"]
            if request.requires_native_audio:
                reasons.append("native audio")
            if request.requires_reference_assets:
                reasons.append("reference assets")
            if request.prompt_form is PromptForm.MULTI_SHOT:
                reasons.append("multi-shot")
            if request.prompt_form is PromptForm.TIMED_SEQUENCE:
                reasons.append("timed sequence")
            candidates.append((profile.model_id, ", ".join(reasons)))
        if not candidates:
            raise VideoPromptSkillError(
                "no model capability profile satisfies the requested prompt contract"
            )
        candidates.sort(key=lambda item: item[0])
        return ModelRoutingAdvice(
            tuple(item[0] for item in candidates),
            tuple(item[1] for item in candidates),
        )


_FORBIDDEN_CONTROL_LABELS = (
    "model name:",
    "model version:",
    "aspect ratio:",
    "resolution:",
    "api parameter:",
)


def _forbid_generation_controls(prompt: str) -> None:
    lowered = prompt.lower()
    for label in _FORBIDDEN_CONTROL_LABELS:
        if label in lowered:
            raise VideoPromptSkillError(
                "generation controls must remain outside provider-neutral prompt text"
            )
