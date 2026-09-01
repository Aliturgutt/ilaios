"""Deterministic scene and shot planning for Video Automation.

M08 converts structured :class:`VideoScript` objects into canonical logical
:class:`Scene` objects. M09 converts scene/beat intent into executable visual
units. Neither layer calls providers or performs rendering.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import ceil, floor
from types import MappingProxyType

from .models import Scene, Shot, VideoScript


class ScenePlanningError(ValueError):
    """Raised when a structured script cannot form canonical logical scenes."""


class ScenePlanner:
    """M08 planner: transform a structured script into ordered logical scenes."""

    def plan(self, script: VideoScript) -> tuple[Scene, ...]:
        """Create one deterministic logical scene for each script section."""

        scenes: list[Scene] = []
        for sequence, section in enumerate(script.sections, start=1):
            if section.estimated_duration_seconds <= 0:
                raise ScenePlanningError(
                    "script section estimated_duration_seconds must be greater than zero"
                )

            visual_description = section.on_screen_text or section.title
            scenes.append(
                Scene(
                    scene_id=f"{script.job_id}-scene-{sequence:03d}",
                    script_reference=section.section_id,
                    purpose=section.title,
                    duration_seconds=float(section.estimated_duration_seconds),
                    visual_description=visual_description,
                    narration_reference=section.section_id,
                    transition_intent=(
                        "cut" if sequence == len(script.sections) else "continue"
                    ),
                    required_asset_ids=(),
                )
            )

        return tuple(scenes)


class ShotPlanningError(ValueError):
    """Raised when scene/beat intent cannot be converted into a shot plan."""


@dataclass(frozen=True, slots=True)
class ShotDurationProfile:
    """Preferred cinematic timing envelope for one semantic shot class."""

    minimum_seconds: float
    target_seconds: float
    maximum_seconds: float

    def __post_init__(self) -> None:
        if self.minimum_seconds <= 0:
            raise ShotPlanningError("profile minimum_seconds must be greater than zero")
        if self.maximum_seconds < self.minimum_seconds:
            raise ShotPlanningError(
                "profile maximum_seconds must be >= profile minimum_seconds"
            )
        if not self.minimum_seconds <= self.target_seconds <= self.maximum_seconds:
            raise ShotPlanningError(
                "profile target_seconds must be inside the profile bounds"
            )


_DEFAULT_DURATION_PROFILES: Mapping[str, ShotDurationProfile] = MappingProxyType(
    {
        "establishing": ShotDurationProfile(5.0, 6.0, 8.0),
        "action": ShotDurationProfile(3.0, 4.0, 5.0),
        "dialogue": ShotDurationProfile(5.0, 7.0, 10.0),
        "reaction": ShotDurationProfile(2.0, 3.0, 4.0),
        "insert": ShotDurationProfile(2.0, 3.0, 4.0),
        "hero": ShotDurationProfile(4.0, 6.0, 8.0),
        "cinematic hero": ShotDurationProfile(4.0, 6.0, 8.0),
        "transition": ShotDurationProfile(2.0, 3.0, 4.0),
    }
)


@dataclass(frozen=True, slots=True)
class ShotPlannerConfig:
    """Timing constraints for generated cinematic clips.

    The 4-6 second envelope remains the provider-neutral default. Semantic shot
    classes may use different preferred envelopes, while absolute bounds prevent
    the planner from turning a user-requested final duration into one oversized
    provider request. Live provider capabilities are resolved later by the
    provider capability gate; this planner does not select providers.
    """

    min_shot_seconds: float = 4.0
    target_shot_seconds: float = 5.0
    max_shot_seconds: float = 6.0
    absolute_min_shot_seconds: float = 2.0
    absolute_max_shot_seconds: float = 12.0

    def __post_init__(self) -> None:
        if self.min_shot_seconds <= 0:
            raise ShotPlanningError("min_shot_seconds must be greater than zero")
        if self.max_shot_seconds < self.min_shot_seconds:
            raise ShotPlanningError(
                "max_shot_seconds must be greater than or equal to min_shot_seconds"
            )
        if not self.min_shot_seconds <= self.target_shot_seconds <= self.max_shot_seconds:
            raise ShotPlanningError(
                "target_shot_seconds must be inside configured shot bounds"
            )
        if self.absolute_min_shot_seconds <= 0:
            raise ShotPlanningError(
                "absolute_min_shot_seconds must be greater than zero"
            )
        if self.absolute_max_shot_seconds < self.absolute_min_shot_seconds:
            raise ShotPlanningError(
                "absolute_max_shot_seconds must be >= absolute_min_shot_seconds"
            )
        if self.min_shot_seconds < self.absolute_min_shot_seconds:
            raise ShotPlanningError(
                "min_shot_seconds must be >= absolute_min_shot_seconds"
            )
        if self.max_shot_seconds > self.absolute_max_shot_seconds:
            raise ShotPlanningError(
                "max_shot_seconds must be <= absolute_max_shot_seconds"
            )


@dataclass(frozen=True, slots=True)
class EpisodeBeat:
    """Legacy-compatible explicit M09 shot-planning intent."""

    beat_id: str
    text: str
    duration_seconds: float
    continuity_note: str | None = None
    shot_type: str = "cinematic"
    subject: str = "narrative subject"
    action: str = "depict the narrative beat"
    environment: str = "story environment"
    framing: str = "medium shot"
    movement: str = "static"
    generation_prompt: str | None = None
    required_provider_capability: str = "video.generate"

    def __post_init__(self) -> None:
        _require_non_blank("beat_id", self.beat_id)
        _require_non_blank("text", self.text)
        if self.duration_seconds <= 0:
            raise ShotPlanningError("duration_seconds must be greater than zero")
        if self.continuity_note is not None:
            _require_non_blank("continuity_note", self.continuity_note)
        for name, value in (
            ("shot_type", self.shot_type),
            ("subject", self.subject),
            ("action", self.action),
            ("environment", self.environment),
            ("framing", self.framing),
            ("movement", self.movement),
            ("required_provider_capability", self.required_provider_capability),
        ):
            _require_non_blank(name, value)
        if self.generation_prompt is not None:
            _require_non_blank("generation_prompt", self.generation_prompt)


@dataclass(frozen=True, slots=True)
class CinematicShot:
    """One executable provider-neutral visual unit."""

    shot_id: str
    sequence: int
    source_beat_id: str
    text: str
    duration_seconds: float
    continuity_note: str | None
    previous_shot_id: str | None
    next_shot_id: str | None
    scene_id: str | None = None
    shot_type: str = "cinematic"
    subject: str = "narrative subject"
    action: str = "depict the narrative beat"
    environment: str = "story environment"
    framing: str = "medium shot"
    movement: str = "static"
    generation_prompt: str | None = None
    required_provider_capability: str = "video.generate"

    def __post_init__(self) -> None:
        for name, value in (
            ("shot_id", self.shot_id),
            ("source_beat_id", self.source_beat_id),
            ("text", self.text),
            ("shot_type", self.shot_type),
            ("subject", self.subject),
            ("action", self.action),
            ("environment", self.environment),
            ("framing", self.framing),
            ("movement", self.movement),
            ("required_provider_capability", self.required_provider_capability),
        ):
            _require_non_blank(name, value)
        if self.sequence <= 0:
            raise ShotPlanningError("sequence must be greater than zero")
        if self.duration_seconds <= 0:
            raise ShotPlanningError("duration_seconds must be greater than zero")
        if self.continuity_note is not None:
            _require_non_blank("continuity_note", self.continuity_note)
        if self.previous_shot_id is not None:
            _require_non_blank("previous_shot_id", self.previous_shot_id)
        if self.next_shot_id is not None:
            _require_non_blank("next_shot_id", self.next_shot_id)

        resolved_scene_id = self.source_beat_id if self.scene_id is None else self.scene_id
        resolved_prompt = self.text if self.generation_prompt is None else self.generation_prompt
        _require_non_blank("scene_id", resolved_scene_id)
        _require_non_blank("generation_prompt", resolved_prompt)
        object.__setattr__(self, "scene_id", resolved_scene_id)
        object.__setattr__(self, "generation_prompt", resolved_prompt)


@dataclass(frozen=True, slots=True)
class EpisodeShotPlan:
    """Complete ordered shot plan for one episode."""

    episode_id: str
    shots: tuple[CinematicShot, ...]

    @property
    def total_duration_seconds(self) -> float:
        return sum(shot.duration_seconds for shot in self.shots)


class ShotPlanner:
    """M09 planner: transform scenes or explicit beat intent into visual units."""

    def __init__(self, config: ShotPlannerConfig | None = None) -> None:
        self._config = config or ShotPlannerConfig()

    def plan_scenes(self, scenes: Sequence[Scene]) -> tuple[Shot, ...]:
        """Create deterministic canonical Shot objects from logical scenes."""

        if not scenes:
            raise ShotPlanningError("at least one scene is required")
        scene_ids = [scene.scene_id for scene in scenes]
        if len(scene_ids) != len(set(scene_ids)):
            raise ShotPlanningError("scene_id values must be unique")

        return tuple(
            Shot(
                shot_id=f"{scene.scene_id}-shot-001",
                scene_id=scene.scene_id,
                shot_type="cinematic",
                camera_description=scene.visual_description,
                subject=scene.purpose,
                action=f"depict {scene.purpose}",
                environment=scene.visual_description,
                framing="medium shot",
                movement="static",
                estimated_duration_seconds=scene.duration_seconds,
                generation_prompt=scene.visual_description,
                required_provider_capability="video.generate",
            )
            for scene in scenes
        )

    def plan(
        self,
        beats: Sequence[EpisodeBeat],
        *,
        episode_id: str,
    ) -> EpisodeShotPlan:
        """Plan adaptive short shots while preserving the exact final beat duration."""

        if not episode_id.strip():
            raise ShotPlanningError("episode_id must not be blank")
        if not beats:
            raise ShotPlanningError("at least one episode beat is required")
        beat_ids = [beat.beat_id for beat in beats]
        if len(beat_ids) != len(set(beat_ids)):
            raise ShotPlanningError("beat_id values must be unique")

        drafts: list[tuple[EpisodeBeat, str, float]] = []
        for beat in beats:
            durations = self._partition_duration(
                beat.duration_seconds,
                shot_type=beat.shot_type,
            )
            chunks = _split_text(beat.text, len(durations))
            drafts.extend(
                (beat, chunks[index], duration)
                for index, duration in enumerate(durations)
            )

        total_shots = len(drafts)
        shots: list[CinematicShot] = []
        for sequence, (beat, text, duration) in enumerate(drafts, start=1):
            shots.append(
                CinematicShot(
                    shot_id=_shot_id(episode_id, sequence),
                    sequence=sequence,
                    source_beat_id=beat.beat_id,
                    text=text,
                    duration_seconds=duration,
                    continuity_note=beat.continuity_note,
                    previous_shot_id=(
                        None if sequence == 1 else _shot_id(episode_id, sequence - 1)
                    ),
                    next_shot_id=(
                        None if sequence == total_shots else _shot_id(episode_id, sequence + 1)
                    ),
                    scene_id=beat.beat_id,
                    shot_type=beat.shot_type,
                    subject=beat.subject,
                    action=beat.action,
                    environment=beat.environment,
                    framing=beat.framing,
                    movement=beat.movement,
                    generation_prompt=(text if beat.generation_prompt is None else beat.generation_prompt),
                    required_provider_capability=beat.required_provider_capability,
                )
            )

        return EpisodeShotPlan(episode_id=episode_id, shots=tuple(shots))

    def preferred_profile(self, shot_type: str) -> ShotDurationProfile:
        """Return semantic timing intent without introducing provider selection."""

        normalized = " ".join(shot_type.strip().lower().replace("_", " ").split())
        profile = _DEFAULT_DURATION_PROFILES.get(normalized)
        if profile is not None:
            return profile
        return ShotDurationProfile(
            self._config.min_shot_seconds,
            self._config.target_shot_seconds,
            self._config.max_shot_seconds,
        )

    def _partition_duration(
        self,
        total_seconds: float,
        *,
        shot_type: str = "cinematic",
    ) -> tuple[float, ...]:
        profile = self.preferred_profile(shot_type)
        try:
            return _partition_inside_bounds(
                total_seconds,
                minimum=profile.minimum_seconds,
                target=profile.target_seconds,
                maximum=profile.maximum_seconds,
            )
        except ShotPlanningError:
            # Semantic ranges are directorial preferences, not a reason to reject
            # a valid user duration. Fall back to the global 2-12 second safety
            # envelope. Live provider capability resolution may narrow this later.
            target = min(
                max(profile.target_seconds, self._config.absolute_min_shot_seconds),
                self._config.absolute_max_shot_seconds,
            )
            return _partition_inside_bounds(
                total_seconds,
                minimum=self._config.absolute_min_shot_seconds,
                target=target,
                maximum=self._config.absolute_max_shot_seconds,
            )


def _partition_inside_bounds(
    total_seconds: float,
    *,
    minimum: float,
    target: float,
    maximum: float,
) -> tuple[float, ...]:
    if total_seconds <= 0:
        raise ShotPlanningError("total_seconds must be greater than zero")
    minimum_count = ceil(total_seconds / maximum)
    maximum_count = floor(total_seconds / minimum)
    if minimum_count > maximum_count:
        raise ShotPlanningError(
            "beat duration cannot be partitioned inside configured shot bounds"
        )
    ideal_count = max(1, round(total_seconds / target))
    count = min(max(ideal_count, minimum_count), maximum_count)
    base_duration = total_seconds / count
    durations = [base_duration for _ in range(count)]
    durations[-1] = total_seconds - sum(durations[:-1])
    if any(duration < minimum or duration > maximum for duration in durations):
        raise ShotPlanningError("shot partition violated configured duration bounds")
    return tuple(durations)


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ShotPlanningError(f"{name} must not be blank")
    if value != value.strip():
        raise ShotPlanningError(f"{name} must not contain surrounding whitespace")


def _shot_id(episode_id: str, sequence: int) -> str:
    return f"{episode_id}-shot-{sequence:03d}"


def _split_text(text: str, count: int) -> tuple[str, ...]:
    words = " ".join(text.split()).split()
    if len(words) < count:
        raise ShotPlanningError("beat text has fewer words than required shots")
    chunks: list[str] = []
    offset = 0
    for index in range(count):
        remaining_words = len(words) - offset
        remaining_chunks = count - index
        take = ceil(remaining_words / remaining_chunks)
        chunks.append(" ".join(words[offset : offset + take]))
        offset += take
    return tuple(chunks)
