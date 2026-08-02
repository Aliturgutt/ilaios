"""Film-agnostic cinematic scene and shot planning.

The planner converts ordered episode beats into short generation units. It does
not call any media provider and does not encode a specific film, channel, story,
character, or publishing platform.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor
from typing import Sequence


class ShotPlanningError(ValueError):
    """Raised when an episode cannot be converted into a valid shot plan."""


@dataclass(frozen=True, slots=True)
class ShotPlannerConfig:
    """Timing constraints for generated cinematic clips."""

    min_shot_seconds: float = 4.0
    target_shot_seconds: float = 5.0
    max_shot_seconds: float = 6.0

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


@dataclass(frozen=True, slots=True)
class EpisodeBeat:
    """One ordered narrative beat from the script-generation layer."""

    beat_id: str
    text: str
    duration_seconds: float
    continuity_note: str | None = None

    def __post_init__(self) -> None:
        if not self.beat_id.strip():
            raise ShotPlanningError("beat_id must not be blank")
        if not self.text.strip():
            raise ShotPlanningError("text must not be blank")
        if self.duration_seconds <= 0:
            raise ShotPlanningError("duration_seconds must be greater than zero")
        if self.continuity_note is not None and not self.continuity_note.strip():
            raise ShotPlanningError("continuity_note must be None or non-blank")


@dataclass(frozen=True, slots=True)
class CinematicShot:
    """One short ordered generation unit."""

    shot_id: str
    sequence: int
    source_beat_id: str
    text: str
    duration_seconds: float
    continuity_note: str | None
    previous_shot_id: str | None
    next_shot_id: str | None


@dataclass(frozen=True, slots=True)
class EpisodeShotPlan:
    """Complete ordered shot plan for one episode."""

    episode_id: str
    shots: tuple[CinematicShot, ...]

    @property
    def total_duration_seconds(self) -> float:
        """Return the exact planned episode duration."""

        return sum(shot.duration_seconds for shot in self.shots)


class ScenePlanner:
    """Split episode beats into deterministic short cinematic shots."""

    def __init__(self, config: ShotPlannerConfig | None = None) -> None:
        self._config = config or ShotPlannerConfig()

    def plan(
        self,
        beats: Sequence[EpisodeBeat],
        *,
        episode_id: str,
    ) -> EpisodeShotPlan:
        """Create an ordered short-shot plan without changing story order."""

        if not episode_id.strip():
            raise ShotPlanningError("episode_id must not be blank")
        if not beats:
            raise ShotPlanningError("at least one episode beat is required")

        beat_ids = [beat.beat_id for beat in beats]
        if len(set(beat_ids)) != len(beat_ids):
            raise ShotPlanningError("beat_id values must be unique")

        drafts: list[tuple[EpisodeBeat, str, float]] = []
        for beat in beats:
            durations = self._partition_duration(beat.duration_seconds)
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
                        None
                        if sequence == 1
                        else _shot_id(episode_id, sequence - 1)
                    ),
                    next_shot_id=(
                        None
                        if sequence == total_shots
                        else _shot_id(episode_id, sequence + 1)
                    ),
                )
            )

        return EpisodeShotPlan(episode_id=episode_id, shots=tuple(shots))

    def _partition_duration(self, total_seconds: float) -> tuple[float, ...]:
        minimum = self._config.min_shot_seconds
        target = self._config.target_shot_seconds
        maximum = self._config.max_shot_seconds

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
            raise ShotPlanningError(
                "shot partition violated configured duration bounds"
            )

        return tuple(durations)


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
