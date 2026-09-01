"""Deterministic provider-agnostic prompt compilation for cinematic shots.

The compiler converts an already-approved cinematic shot and structured
continuity snapshot into an auditable instruction package. It does not invent
creative facts, call providers, render media, or encode a specific film,
character, story, or publishing platform.
"""

from __future__ import annotations

from dataclasses import dataclass

from .continuity import CharacterContinuity, ContinuityState
from .scene_planning import CinematicShot


class PromptCompilationError(ValueError):
    """Raised when approved shot inputs cannot form a valid prompt package."""


@dataclass(frozen=True, slots=True)
class ShotPromptPolicy:
    """Explicit formatting policy for deterministic prompt compilation."""

    include_identifiers: bool = True
    include_empty_sections: bool = False
    section_separator: str = "\n"

    def __post_init__(self) -> None:
        if not self.section_separator:
            raise PromptCompilationError("section_separator must not be empty")


@dataclass(frozen=True, slots=True)
class PromptSection:
    """One named, ordered, auditable instruction section."""

    name: str
    value: str

    def __post_init__(self) -> None:
        _require_non_blank("name", self.name)
        _require_non_blank("value", self.value)


@dataclass(frozen=True, slots=True)
class ShotPromptPackage:
    """Complete deterministic instruction package for one cinematic shot."""

    shot_id: str
    source_beat_id: str
    duration_seconds: float
    sections: tuple[PromptSection, ...]
    prompt_text: str

    def __post_init__(self) -> None:
        _require_non_blank("shot_id", self.shot_id)
        _require_non_blank("source_beat_id", self.source_beat_id)
        if self.duration_seconds <= 0:
            raise PromptCompilationError("duration_seconds must be greater than zero")
        if not self.sections:
            raise PromptCompilationError("at least one prompt section is required")
        _require_non_blank("prompt_text", self.prompt_text)
        names = [section.name for section in self.sections]
        if len(set(names)) != len(names):
            raise PromptCompilationError("prompt section names must be unique")

    def section_map(self) -> dict[str, str]:
        """Return compiled sections keyed by their stable names."""

        return {section.name: section.value for section in self.sections}


class ShotPromptCompiler:
    """Compile approved shot and continuity facts without inference."""

    def __init__(self, policy: ShotPromptPolicy | None = None) -> None:
        self._policy = policy or ShotPromptPolicy()

    def compile(
        self,
        shot: CinematicShot,
        continuity: ContinuityState,
    ) -> ShotPromptPackage:
        """Create a stable provider-agnostic prompt package for one shot."""

        if continuity.shot_id != shot.shot_id:
            raise PromptCompilationError(
                "continuity shot_id must match cinematic shot_id"
            )
        if shot.duration_seconds <= 0:
            raise PromptCompilationError("shot duration_seconds must be positive")

        values: tuple[tuple[str, str | None], ...] = (
            ("shot", shot.text),
            ("characters", _format_characters(continuity.characters)),
            ("location", continuity.location),
            ("objects", _format_collection(continuity.objects)),
            ("technology", _format_collection(continuity.technology)),
            ("timeline", continuity.timeline),
            ("lighting", continuity.lighting),
            ("visual_style", continuity.visual_style),
            ("camera_state", continuity.camera_state),
            ("scene_state", continuity.scene_state),
            ("continuity_note", shot.continuity_note),
        )

        sections: list[PromptSection] = []
        if self._policy.include_identifiers:
            sections.extend(
                (
                    PromptSection("shot_id", shot.shot_id),
                    PromptSection("source_beat_id", shot.source_beat_id),
                    PromptSection("sequence", str(shot.sequence)),
                    PromptSection(
                        "duration_seconds",
                        _format_duration(shot.duration_seconds),
                    ),
                )
            )

        for name, value in values:
            if value is None:
                if self._policy.include_empty_sections:
                    sections.append(PromptSection(name, "none"))
                continue
            sections.append(PromptSection(name, value))

        prompt_text = self._policy.section_separator.join(
            f"{section.name}: {section.value}" for section in sections
        )
        return ShotPromptPackage(
            shot_id=shot.shot_id,
            source_beat_id=shot.source_beat_id,
            duration_seconds=shot.duration_seconds,
            sections=tuple(sections),
            prompt_text=prompt_text,
        )


def _format_characters(characters: tuple[CharacterContinuity, ...]) -> str | None:
    if not characters:
        return None
    return " | ".join(
        ", ".join(
            (
                f"id={character.character_id}",
                f"identity={character.identity}",
                f"appearance={character.appearance}",
                f"costume={character.costume}",
            )
        )
        for character in characters
    )


def _format_collection(values: tuple[str, ...]) -> str | None:
    if not values:
        return None
    return " | ".join(values)


def _format_duration(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _require_non_blank(name: str, value: str) -> None:
    if not value.strip():
        raise PromptCompilationError(f"{name} must not be blank")
