"""Structured continuity state for cinematic shot production.

The module records film-agnostic continuity facts between ordered shots. It does
not generate media, call providers, infer creative decisions, or encode a
specific film, character, story, or publishing platform.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace


class ContinuityError(ValueError):
    """Raised when continuity state or transitions are invalid."""


@dataclass(frozen=True, slots=True)
class CharacterContinuity:
    """Stable on-screen identity and appearance for one character."""

    character_id: str
    identity: str
    appearance: str
    costume: str

    def __post_init__(self) -> None:
        _require_non_blank("character_id", self.character_id)
        _require_non_blank("identity", self.identity)
        _require_non_blank("appearance", self.appearance)
        _require_non_blank("costume", self.costume)


@dataclass(frozen=True, slots=True)
class ContinuityState:
    """Complete structured continuity snapshot for one cinematic shot."""

    shot_id: str
    characters: tuple[CharacterContinuity, ...] = ()
    location: str | None = None
    objects: tuple[str, ...] = ()
    technology: tuple[str, ...] = ()
    timeline: str | None = None
    lighting: str | None = None
    visual_style: str | None = None
    camera_state: str | None = None
    scene_state: str | None = None
    previous_shot_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_blank("shot_id", self.shot_id)
        _require_optional_non_blank("location", self.location)
        _require_optional_non_blank("timeline", self.timeline)
        _require_optional_non_blank("lighting", self.lighting)
        _require_optional_non_blank("visual_style", self.visual_style)
        _require_optional_non_blank("camera_state", self.camera_state)
        _require_optional_non_blank("scene_state", self.scene_state)
        _require_optional_non_blank("previous_shot_id", self.previous_shot_id)
        _require_unique_characters(self.characters)
        _require_unique_non_blank("objects", self.objects)
        _require_unique_non_blank("technology", self.technology)
        if self.previous_shot_id == self.shot_id:
            raise ContinuityError("previous_shot_id must differ from shot_id")

    def character_map(self) -> Mapping[str, CharacterContinuity]:
        """Return characters keyed by stable character identifier."""

        return {character.character_id: character for character in self.characters}


@dataclass(frozen=True, slots=True)
class ContinuityUpdate:
    """Explicit authorized changes applied when advancing to the next shot."""

    characters: tuple[CharacterContinuity, ...] | None = None
    location: str | None = None
    objects: tuple[str, ...] | None = None
    technology: tuple[str, ...] | None = None
    timeline: str | None = None
    lighting: str | None = None
    visual_style: str | None = None
    camera_state: str | None = None
    scene_state: str | None = None
    clear_location: bool = False
    clear_timeline: bool = False
    clear_lighting: bool = False
    clear_visual_style: bool = False
    clear_camera_state: bool = False
    clear_scene_state: bool = False

    def __post_init__(self) -> None:
        _require_optional_non_blank("location", self.location)
        _require_optional_non_blank("timeline", self.timeline)
        _require_optional_non_blank("lighting", self.lighting)
        _require_optional_non_blank("visual_style", self.visual_style)
        _require_optional_non_blank("camera_state", self.camera_state)
        _require_optional_non_blank("scene_state", self.scene_state)
        if self.characters is not None:
            _require_unique_characters(self.characters)
        if self.objects is not None:
            _require_unique_non_blank("objects", self.objects)
        if self.technology is not None:
            _require_unique_non_blank("technology", self.technology)
        _require_no_set_and_clear("location", self.location, self.clear_location)
        _require_no_set_and_clear("timeline", self.timeline, self.clear_timeline)
        _require_no_set_and_clear("lighting", self.lighting, self.clear_lighting)
        _require_no_set_and_clear(
            "visual_style", self.visual_style, self.clear_visual_style
        )
        _require_no_set_and_clear(
            "camera_state", self.camera_state, self.clear_camera_state
        )
        _require_no_set_and_clear(
            "scene_state", self.scene_state, self.clear_scene_state
        )


@dataclass(frozen=True, slots=True)
class ContinuityTransition:
    """Auditable transition between two ordered shot continuity snapshots."""

    previous: ContinuityState
    current: ContinuityState
    changed_fields: tuple[str, ...]


class ContinuityTracker:
    """Advance continuity through ordered shots using explicit updates only."""

    def start(self, state: ContinuityState) -> ContinuityState:
        """Validate and return an initial state with no predecessor."""

        if state.previous_shot_id is not None:
            raise ContinuityError(
                "initial continuity state cannot have previous_shot_id"
            )
        return state

    def advance(
        self,
        previous: ContinuityState,
        *,
        shot_id: str,
        update: ContinuityUpdate | None = None,
    ) -> ContinuityTransition:
        """Create the next state by preserving all unspecified continuity fields."""

        _require_non_blank("shot_id", shot_id)
        if shot_id == previous.shot_id:
            raise ContinuityError("next shot_id must differ from previous shot_id")

        change = update or ContinuityUpdate()
        current = ContinuityState(
            shot_id=shot_id,
            characters=(
                previous.characters if change.characters is None else change.characters
            ),
            location=_next_optional(
                previous.location, change.location, change.clear_location
            ),
            objects=previous.objects if change.objects is None else change.objects,
            technology=(
                previous.technology
                if change.technology is None
                else change.technology
            ),
            timeline=_next_optional(
                previous.timeline, change.timeline, change.clear_timeline
            ),
            lighting=_next_optional(
                previous.lighting, change.lighting, change.clear_lighting
            ),
            visual_style=_next_optional(
                previous.visual_style,
                change.visual_style,
                change.clear_visual_style,
            ),
            camera_state=_next_optional(
                previous.camera_state,
                change.camera_state,
                change.clear_camera_state,
            ),
            scene_state=_next_optional(
                previous.scene_state,
                change.scene_state,
                change.clear_scene_state,
            ),
            previous_shot_id=previous.shot_id,
        )
        return ContinuityTransition(
            previous=previous,
            current=current,
            changed_fields=_changed_fields(previous, current),
        )

    def rebind_shot(
        self,
        state: ContinuityState,
        *,
        shot_id: str,
        previous_shot_id: str | None,
    ) -> ContinuityState:
        """Return the same continuity facts bound to explicit shot identifiers."""

        return replace(
            state,
            shot_id=shot_id,
            previous_shot_id=previous_shot_id,
        )


def _next_optional(
    previous: str | None,
    value: str | None,
    clear: bool,
) -> str | None:
    if clear:
        return None
    return previous if value is None else value


def _changed_fields(
    previous: ContinuityState,
    current: ContinuityState,
) -> tuple[str, ...]:
    fields = (
        "characters",
        "location",
        "objects",
        "technology",
        "timeline",
        "lighting",
        "visual_style",
        "camera_state",
        "scene_state",
    )
    return tuple(
        field
        for field in fields
        if getattr(previous, field) != getattr(current, field)
    )


def _require_non_blank(name: str, value: str) -> None:
    if not value.strip():
        raise ContinuityError(f"{name} must not be blank")


def _require_optional_non_blank(name: str, value: str | None) -> None:
    if value is not None:
        _require_non_blank(name, value)


def _require_unique_characters(characters: Iterable[CharacterContinuity]) -> None:
    identifiers = [character.character_id for character in characters]
    if len(set(identifiers)) != len(identifiers):
        raise ContinuityError("character_id values must be unique")


def _require_unique_non_blank(name: str, values: Iterable[str]) -> None:
    normalized: list[str] = []
    for value in values:
        _require_non_blank(name, value)
        normalized.append(value)
    if len(set(normalized)) != len(normalized):
        raise ContinuityError(f"{name} values must be unique")


def _require_no_set_and_clear(name: str, value: str | None, clear: bool) -> None:
    if value is not None and clear:
        raise ContinuityError(f"{name} cannot be set and cleared together")
