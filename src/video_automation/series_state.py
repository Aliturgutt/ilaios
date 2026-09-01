"""Durable series truth for autonomous Video Factory continuations.

This module adds episode-to-episode state above the existing shot-level
``continuity.py`` tracker.  Accepted final artifacts are the only source of
canonical continuity references; rejected or intermediate media is never
promoted into series truth.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path


class SeriesStateError(ValueError):
    """Raised when durable series truth would become inconsistent."""


class EpisodeProgressState(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    INCOMPLETE = "INCOMPLETE"
    ACCEPTED = "ACCEPTED"


class EpisodePublicationState(str, Enum):
    PENDING_EXTERNAL_AUTHORIZATION = "PENDING_EXTERNAL_AUTHORIZATION"
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class CharacterBibleEntry:
    character_id: str
    name: str
    appearance: str
    wardrobe_constraints: tuple[str, ...]
    personality: str
    relationships: tuple[str, ...] = ()
    voice_identity: str | None = None
    reference_assets: tuple[str, ...] = ()
    character_arc: str | None = None

    def __post_init__(self) -> None:
        _text("character_id", self.character_id)
        _text("name", self.name)
        _text("appearance", self.appearance)
        _text("personality", self.personality)
        _texts("wardrobe_constraints", self.wardrobe_constraints)
        _texts("relationships", self.relationships)
        _texts("reference_assets", self.reference_assets)
        _optional_text("voice_identity", self.voice_identity)
        _optional_text("character_arc", self.character_arc)


@dataclass(frozen=True, slots=True)
class SeriesBible:
    series_id: str
    revision: int
    premise: str
    world_rules: tuple[str, ...]
    characters: tuple[CharacterBibleEntry, ...]
    cinematography: str
    visual_style: str
    color_language: str
    lighting: str
    locations: tuple[str, ...]
    camera_rules: tuple[str, ...]
    aspect_ratio: str
    format_constraints: tuple[str, ...]
    music_language: str
    ambience: str
    sfx_language: str
    mixing_constraints: tuple[str, ...]
    story_arc: str
    season_constraints: tuple[str, ...]

    def __post_init__(self) -> None:
        _text("series_id", self.series_id)
        if self.revision < 1:
            raise SeriesStateError("series bible revision must be >= 1")
        for name, value in (
            ("premise", self.premise),
            ("cinematography", self.cinematography),
            ("visual_style", self.visual_style),
            ("color_language", self.color_language),
            ("lighting", self.lighting),
            ("aspect_ratio", self.aspect_ratio),
            ("music_language", self.music_language),
            ("ambience", self.ambience),
            ("sfx_language", self.sfx_language),
            ("story_arc", self.story_arc),
        ):
            _text(name, value)
        for name, values in (
            ("world_rules", self.world_rules),
            ("locations", self.locations),
            ("camera_rules", self.camera_rules),
            ("format_constraints", self.format_constraints),
            ("mixing_constraints", self.mixing_constraints),
            ("season_constraints", self.season_constraints),
        ):
            _texts(name, values)
        character_ids = [character.character_id for character in self.characters]
        if len(character_ids) != len(set(character_ids)):
            raise SeriesStateError("series bible character_id values must be unique")


@dataclass(frozen=True, slots=True)
class SeriesState:
    series_id: str
    tenant_id: str
    user_id: str
    title: str
    objective: str
    premise: str
    schedule_spec: str
    bible_revision: int
    next_episode_number: int = 1
    latest_accepted_episode_id: str | None = None
    latest_artifact_sha256: str | None = None
    open_story_threads: tuple[str, ...] = ()
    resolved_story_threads: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (
            ("series_id", self.series_id),
            ("tenant_id", self.tenant_id),
            ("user_id", self.user_id),
            ("title", self.title),
            ("objective", self.objective),
            ("premise", self.premise),
            ("schedule_spec", self.schedule_spec),
        ):
            _text(name, value)
        if self.bible_revision < 1:
            raise SeriesStateError("bible_revision must be >= 1")
        if self.next_episode_number < 1:
            raise SeriesStateError("next_episode_number must be >= 1")
        _optional_text("latest_accepted_episode_id", self.latest_accepted_episode_id)
        if self.latest_artifact_sha256 is not None:
            _sha256("latest_artifact_sha256", self.latest_artifact_sha256)
        _texts("open_story_threads", self.open_story_threads)
        _texts("resolved_story_threads", self.resolved_story_threads)
        overlap = set(self.open_story_threads) & set(self.resolved_story_threads)
        if overlap:
            raise SeriesStateError("story thread cannot be both open and resolved")


@dataclass(frozen=True, slots=True)
class AcceptedEpisodeManifest:
    series_id: str
    episode_id: str
    episode_number: int
    episode_objective: str
    final_acceptance_id: str
    final_artifact_reference: str
    final_artifact_sha256: str
    duration_seconds: int
    resolution: str
    script_reference: str
    shot_plan_reference: str
    generated_clip_references: tuple[str, ...]
    source_reference_assets: tuple[str, ...]
    provider_model_evidence_refs: tuple[str, ...]
    voice_references: tuple[str, ...]
    music_references: tuple[str, ...]
    sfx_references: tuple[str, ...]
    caption_artifact_reference: str | None
    edit_timeline_evidence_ref: str
    technical_validation_ref: str
    visual_quality_evidence_ref: str
    audio_quality_evidence_ref: str
    brand_evidence_ref: str | None
    continuity_evidence_ref: str
    final_frame_reference: str
    character_reference_frames: tuple[str, ...]
    location_reference_frames: tuple[str, ...]
    visual_style_fingerprint: str
    color_language: str
    episode_summary: str
    open_narrative_threads: tuple[str, ...]
    resolved_narrative_threads: tuple[str, ...]
    accepted_at: str
    bible_revision: int

    def __post_init__(self) -> None:
        for name, value in (
            ("series_id", self.series_id),
            ("episode_id", self.episode_id),
            ("episode_objective", self.episode_objective),
            ("final_acceptance_id", self.final_acceptance_id),
            ("final_artifact_reference", self.final_artifact_reference),
            ("resolution", self.resolution),
            ("script_reference", self.script_reference),
            ("shot_plan_reference", self.shot_plan_reference),
            ("edit_timeline_evidence_ref", self.edit_timeline_evidence_ref),
            ("technical_validation_ref", self.technical_validation_ref),
            ("visual_quality_evidence_ref", self.visual_quality_evidence_ref),
            ("audio_quality_evidence_ref", self.audio_quality_evidence_ref),
            ("continuity_evidence_ref", self.continuity_evidence_ref),
            ("final_frame_reference", self.final_frame_reference),
            ("visual_style_fingerprint", self.visual_style_fingerprint),
            ("color_language", self.color_language),
            ("episode_summary", self.episode_summary),
            ("accepted_at", self.accepted_at),
        ):
            _text(name, value)
        if self.episode_number < 1:
            raise SeriesStateError("episode_number must be >= 1")
        if self.duration_seconds <= 0:
            raise SeriesStateError("duration_seconds must be positive")
        if self.bible_revision < 1:
            raise SeriesStateError("bible_revision must be >= 1")
        _sha256("final_artifact_sha256", self.final_artifact_sha256)
        _optional_text("caption_artifact_reference", self.caption_artifact_reference)
        _optional_text("brand_evidence_ref", self.brand_evidence_ref)
        for name, values in (
            ("generated_clip_references", self.generated_clip_references),
            ("source_reference_assets", self.source_reference_assets),
            ("provider_model_evidence_refs", self.provider_model_evidence_refs),
            ("voice_references", self.voice_references),
            ("music_references", self.music_references),
            ("sfx_references", self.sfx_references),
            ("character_reference_frames", self.character_reference_frames),
            ("location_reference_frames", self.location_reference_frames),
            ("open_narrative_threads", self.open_narrative_threads),
            ("resolved_narrative_threads", self.resolved_narrative_threads),
        ):
            _texts(name, values)


@dataclass(frozen=True, slots=True)
class EpisodeContinuityPackage:
    series_id: str
    episode_id: str
    previous_artifact_sha256: str
    previous_final_frame: str
    character_references: tuple[str, ...]
    location_references: tuple[str, ...]
    visual_style_fingerprint: str
    color_language: str
    voice_references: tuple[str, ...]
    audio_references: tuple[str, ...]
    previous_episode_summary: str
    open_narrative_threads: tuple[str, ...]
    last_scene_reference: str
    next_scene_constraints: tuple[str, ...]
    series_bible_revision: int
    privacy_classification: str
    provenance: str

    def __post_init__(self) -> None:
        for name, value in (
            ("series_id", self.series_id),
            ("episode_id", self.episode_id),
            ("previous_final_frame", self.previous_final_frame),
            ("visual_style_fingerprint", self.visual_style_fingerprint),
            ("color_language", self.color_language),
            ("previous_episode_summary", self.previous_episode_summary),
            ("last_scene_reference", self.last_scene_reference),
            ("privacy_classification", self.privacy_classification),
            ("provenance", self.provenance),
        ):
            _text(name, value)
        _sha256("previous_artifact_sha256", self.previous_artifact_sha256)
        if self.series_bible_revision < 1:
            raise SeriesStateError("series_bible_revision must be >= 1")
        for name, values in (
            ("character_references", self.character_references),
            ("location_references", self.location_references),
            ("voice_references", self.voice_references),
            ("audio_references", self.audio_references),
            ("open_narrative_threads", self.open_narrative_threads),
            ("next_scene_constraints", self.next_scene_constraints),
        ):
            _texts(name, values)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS media_series (
 series_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, user_id TEXT NOT NULL,
 state_json TEXT NOT NULL, bible_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS media_episode_progress (
 series_id TEXT NOT NULL, episode_id TEXT NOT NULL, episode_number INTEGER NOT NULL,
 state TEXT NOT NULL, checkpoint TEXT NOT NULL,
 PRIMARY KEY (series_id, episode_id),
 UNIQUE (series_id, episode_number),
 FOREIGN KEY (series_id) REFERENCES media_series (series_id));
CREATE TABLE IF NOT EXISTS accepted_episode_manifests (
 series_id TEXT NOT NULL, episode_id TEXT PRIMARY KEY, episode_number INTEGER NOT NULL,
 artifact_sha256 TEXT NOT NULL, manifest_sha256 TEXT NOT NULL, manifest_json TEXT NOT NULL,
 UNIQUE (series_id, episode_number),
 FOREIGN KEY (series_id) REFERENCES media_series (series_id));
CREATE TABLE IF NOT EXISTS episode_publication_state (
 episode_id TEXT PRIMARY KEY, state TEXT NOT NULL,
 FOREIGN KEY (episode_id) REFERENCES accepted_episode_manifests (episode_id));
CREATE TABLE IF NOT EXISTS episode_continuity_packages (
 episode_id TEXT PRIMARY KEY, parent_artifact_sha256 TEXT NOT NULL,
 package_json TEXT NOT NULL,
 FOREIGN KEY (episode_id) REFERENCES accepted_episode_manifests (episode_id));
"""


class SeriesStateStore:
    """SQLite-backed series, accepted-manifest, and continuity truth store."""

    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._database = root / "media_series_state.sqlite3"
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_series(self, state: SeriesState, bible: SeriesBible) -> None:
        if state.series_id != bible.series_id:
            raise SeriesStateError("series state and bible must share series_id")
        if state.bible_revision != bible.revision:
            raise SeriesStateError("series state must reference exact bible revision")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute(
                "SELECT 1 FROM media_series WHERE series_id = ?", (state.series_id,)
            ).fetchone() is not None:
                raise SeriesStateError("series_id already exists")
            connection.execute(
                "INSERT INTO media_series VALUES (?, ?, ?, ?, ?)",
                (
                    state.series_id,
                    state.tenant_id,
                    state.user_id,
                    _state_json(state),
                    _bible_json(bible),
                ),
            )

    def load_series(self, series_id: str) -> SeriesState:
        with self._connect() as connection:
            value = connection.execute(
                "SELECT state_json FROM media_series WHERE series_id = ?", (series_id,)
            ).fetchone()
        if value is None:
            raise SeriesStateError("series does not exist")
        return _state_from_json(str(_row(value)["state_json"]))

    def load_bible(self, series_id: str) -> SeriesBible:
        with self._connect() as connection:
            value = connection.execute(
                "SELECT bible_json FROM media_series WHERE series_id = ?", (series_id,)
            ).fetchone()
        if value is None:
            raise SeriesStateError("series does not exist")
        return _bible_from_json(str(_row(value)["bible_json"]))

    def begin_episode(
        self,
        *,
        series_id: str,
        episode_id: str,
        episode_number: int,
        checkpoint: str = "SERIES_LOAD",
    ) -> None:
        _text("episode_id", episode_id)
        _text("checkpoint", checkpoint)
        state = self.load_series(series_id)
        if episode_number != state.next_episode_number:
            raise SeriesStateError("episode_number is not the next accepted sequence number")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            active = connection.execute(
                "SELECT episode_id,state FROM media_episode_progress "
                "WHERE series_id=? AND state != ?",
                (series_id, EpisodeProgressState.ACCEPTED.value),
            ).fetchall()
            if active:
                existing = _row(active[0])
                if str(existing["episode_id"]) != episode_id:
                    raise SeriesStateError("previous episode is incomplete; resume it first")
                return
            connection.execute(
                "INSERT INTO media_episode_progress VALUES (?, ?, ?, ?, ?)",
                (
                    series_id,
                    episode_id,
                    episode_number,
                    EpisodeProgressState.IN_PROGRESS.value,
                    checkpoint,
                ),
            )

    def checkpoint_episode(
        self,
        *,
        series_id: str,
        episode_id: str,
        checkpoint: str,
        incomplete: bool = False,
    ) -> None:
        _text("checkpoint", checkpoint)
        new_state = (
            EpisodeProgressState.INCOMPLETE
            if incomplete
            else EpisodeProgressState.IN_PROGRESS
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT state FROM media_episode_progress "
                "WHERE series_id=? AND episode_id=?",
                (series_id, episode_id),
            ).fetchone()
            if row is None:
                raise SeriesStateError("episode progress does not exist")
            if str(_row(row)["state"]) == EpisodeProgressState.ACCEPTED.value:
                raise SeriesStateError("accepted episode progress is immutable")
            connection.execute(
                "UPDATE media_episode_progress SET state=?,checkpoint=? "
                "WHERE series_id=? AND episode_id=?",
                (new_state.value, checkpoint, series_id, episode_id),
            )

    def episode_progress(
        self, *, series_id: str, episode_id: str
    ) -> tuple[EpisodeProgressState, str]:
        with self._connect() as connection:
            value = connection.execute(
                "SELECT state,checkpoint FROM media_episode_progress "
                "WHERE series_id=? AND episode_id=?",
                (series_id, episode_id),
            ).fetchone()
        if value is None:
            raise SeriesStateError("episode progress does not exist")
        row = _row(value)
        return EpisodeProgressState(str(row["state"])), str(row["checkpoint"])

    def persist_accepted_manifest(
        self,
        manifest: AcceptedEpisodeManifest,
        *,
        publication_state: EpisodePublicationState,
    ) -> str:
        """Persist immutable accepted truth before advancing SeriesState."""

        state = self.load_series(manifest.series_id)
        if manifest.episode_number != state.next_episode_number:
            raise SeriesStateError("accepted manifest is not the next episode")
        if manifest.bible_revision != state.bible_revision:
            raise SeriesStateError("accepted manifest bible revision is stale")
        progress, _ = self.episode_progress(
            series_id=manifest.series_id, episode_id=manifest.episode_id
        )
        if progress not in {
            EpisodeProgressState.IN_PROGRESS,
            EpisodeProgressState.INCOMPLETE,
        }:
            raise SeriesStateError("episode is not eligible for final acceptance persistence")
        material = _manifest_json(manifest)
        manifest_sha = hashlib.sha256(material.encode("utf-8")).hexdigest()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT manifest_sha256 FROM accepted_episode_manifests "
                "WHERE episode_id=?",
                (manifest.episode_id,),
            ).fetchone()
            if existing is not None:
                if str(_row(existing)["manifest_sha256"]) != manifest_sha:
                    raise SeriesStateError("accepted episode manifest is immutable")
                return manifest_sha
            connection.execute(
                "INSERT INTO accepted_episode_manifests VALUES (?, ?, ?, ?, ?, ?)",
                (
                    manifest.series_id,
                    manifest.episode_id,
                    manifest.episode_number,
                    manifest.final_artifact_sha256,
                    manifest_sha,
                    material,
                ),
            )
            connection.execute(
                "INSERT INTO episode_publication_state VALUES (?, ?)",
                (manifest.episode_id, publication_state.value),
            )
        return manifest_sha

    def advance_series_from_manifest(self, *, series_id: str, episode_id: str) -> SeriesState:
        """Advance durable series state only from an immutable accepted manifest."""

        manifest = self.load_manifest(episode_id)
        state = self.load_series(series_id)
        if manifest.series_id != series_id:
            raise SeriesStateError("accepted manifest belongs to another series")
        if manifest.episode_number < state.next_episode_number:
            if state.latest_accepted_episode_id == episode_id:
                return state
            raise SeriesStateError("series already advanced beyond this manifest")
        if manifest.episode_number != state.next_episode_number:
            raise SeriesStateError("accepted manifest sequence has a gap")
        next_state = replace(
            state,
            next_episode_number=state.next_episode_number + 1,
            latest_accepted_episode_id=manifest.episode_id,
            latest_artifact_sha256=manifest.final_artifact_sha256,
            open_story_threads=manifest.open_narrative_threads,
            resolved_story_threads=manifest.resolved_narrative_threads,
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            stored = connection.execute(
                "SELECT state_json FROM media_series WHERE series_id=?", (series_id,)
            ).fetchone()
            if stored is None:
                raise SeriesStateError("series disappeared during advancement")
            current = _state_from_json(str(_row(stored)["state_json"]))
            if current != state:
                raise SeriesStateError("series changed concurrently; recover from manifest")
            connection.execute(
                "UPDATE media_series SET state_json=? WHERE series_id=?",
                (_state_json(next_state), series_id),
            )
            connection.execute(
                "UPDATE media_episode_progress SET state=?,checkpoint=? "
                "WHERE series_id=? AND episode_id=?",
                (
                    EpisodeProgressState.ACCEPTED.value,
                    "ACCEPTED_EPISODE_MANIFEST",
                    series_id,
                    episode_id,
                ),
            )
        return next_state

    def accept_episode(
        self,
        manifest: AcceptedEpisodeManifest,
        *,
        publication_state: EpisodePublicationState,
    ) -> SeriesState:
        self.persist_accepted_manifest(manifest, publication_state=publication_state)
        return self.advance_series_from_manifest(
            series_id=manifest.series_id, episode_id=manifest.episode_id
        )

    def recover_series_from_manifests(self, series_id: str) -> SeriesState:
        """Recover after a crash between manifest durability and state advancement."""

        state = self.load_series(series_id)
        while True:
            with self._connect() as connection:
                value = connection.execute(
                    "SELECT episode_id FROM accepted_episode_manifests "
                    "WHERE series_id=? AND episode_number=?",
                    (series_id, state.next_episode_number),
                ).fetchone()
            if value is None:
                return state
            state = self.advance_series_from_manifest(
                series_id=series_id,
                episode_id=str(_row(value)["episode_id"]),
            )

    def load_manifest(self, episode_id: str) -> AcceptedEpisodeManifest:
        with self._connect() as connection:
            value = connection.execute(
                "SELECT manifest_json FROM accepted_episode_manifests WHERE episode_id=?",
                (episode_id,),
            ).fetchone()
        if value is None:
            raise SeriesStateError("accepted episode manifest does not exist")
        return _manifest_from_json(str(_row(value)["manifest_json"]))

    def publication_state(self, episode_id: str) -> EpisodePublicationState:
        with self._connect() as connection:
            value = connection.execute(
                "SELECT state FROM episode_publication_state WHERE episode_id=?",
                (episode_id,),
            ).fetchone()
        if value is None:
            raise SeriesStateError("episode publication state does not exist")
        return EpisodePublicationState(str(_row(value)["state"]))

    def update_publication_state(
        self, episode_id: str, state: EpisodePublicationState
    ) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                "UPDATE episode_publication_state SET state=? WHERE episode_id=?",
                (state.value, episode_id),
            )
            if updated.rowcount != 1:
                raise SeriesStateError("episode publication state does not exist")

    def create_continuity_package(
        self,
        *,
        episode_id: str,
        privacy_classification: str,
        provenance: str,
        last_scene_reference: str,
        next_scene_constraints: tuple[str, ...],
    ) -> EpisodeContinuityPackage:
        """Derive references only from the exact accepted final artifact lineage."""

        manifest = self.load_manifest(episode_id)
        package = EpisodeContinuityPackage(
            series_id=manifest.series_id,
            episode_id=manifest.episode_id,
            previous_artifact_sha256=manifest.final_artifact_sha256,
            previous_final_frame=manifest.final_frame_reference,
            character_references=manifest.character_reference_frames,
            location_references=manifest.location_reference_frames,
            visual_style_fingerprint=manifest.visual_style_fingerprint,
            color_language=manifest.color_language,
            voice_references=manifest.voice_references,
            audio_references=manifest.music_references + manifest.sfx_references,
            previous_episode_summary=manifest.episode_summary,
            open_narrative_threads=manifest.open_narrative_threads,
            last_scene_reference=last_scene_reference,
            next_scene_constraints=next_scene_constraints,
            series_bible_revision=manifest.bible_revision,
            privacy_classification=privacy_classification,
            provenance=provenance,
        )
        material = _package_json(package)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT parent_artifact_sha256,package_json "
                "FROM episode_continuity_packages WHERE episode_id=?",
                (episode_id,),
            ).fetchone()
            if existing is not None:
                row = _row(existing)
                if (
                    str(row["parent_artifact_sha256"]) != manifest.final_artifact_sha256
                    or str(row["package_json"]) != material
                ):
                    raise SeriesStateError("episode continuity package is immutable")
                return package
            connection.execute(
                "INSERT INTO episode_continuity_packages VALUES (?, ?, ?)",
                (episode_id, manifest.final_artifact_sha256, material),
            )
        return package


def _state_json(state: SeriesState) -> str:
    return _dumps(
        {
            "series_id": state.series_id,
            "tenant_id": state.tenant_id,
            "user_id": state.user_id,
            "title": state.title,
            "objective": state.objective,
            "premise": state.premise,
            "schedule_spec": state.schedule_spec,
            "bible_revision": state.bible_revision,
            "next_episode_number": state.next_episode_number,
            "latest_accepted_episode_id": state.latest_accepted_episode_id,
            "latest_artifact_sha256": state.latest_artifact_sha256,
            "open_story_threads": list(state.open_story_threads),
            "resolved_story_threads": list(state.resolved_story_threads),
        }
    )


def _state_from_json(raw: str) -> SeriesState:
    data = _json_object(raw)
    return SeriesState(
        series_id=_string(data, "series_id"),
        tenant_id=_string(data, "tenant_id"),
        user_id=_string(data, "user_id"),
        title=_string(data, "title"),
        objective=_string(data, "objective"),
        premise=_string(data, "premise"),
        schedule_spec=_string(data, "schedule_spec"),
        bible_revision=_integer(data, "bible_revision"),
        next_episode_number=_integer(data, "next_episode_number"),
        latest_accepted_episode_id=_nullable_string(data, "latest_accepted_episode_id"),
        latest_artifact_sha256=_nullable_string(data, "latest_artifact_sha256"),
        open_story_threads=_string_tuple(data, "open_story_threads"),
        resolved_story_threads=_string_tuple(data, "resolved_story_threads"),
    )


def _character_material(character: CharacterBibleEntry) -> dict[str, object]:
    return {
        "character_id": character.character_id,
        "name": character.name,
        "appearance": character.appearance,
        "wardrobe_constraints": list(character.wardrobe_constraints),
        "personality": character.personality,
        "relationships": list(character.relationships),
        "voice_identity": character.voice_identity,
        "reference_assets": list(character.reference_assets),
        "character_arc": character.character_arc,
    }


def _bible_json(bible: SeriesBible) -> str:
    return _dumps(
        {
            "series_id": bible.series_id,
            "revision": bible.revision,
            "premise": bible.premise,
            "world_rules": list(bible.world_rules),
            "characters": [_character_material(item) for item in bible.characters],
            "cinematography": bible.cinematography,
            "visual_style": bible.visual_style,
            "color_language": bible.color_language,
            "lighting": bible.lighting,
            "locations": list(bible.locations),
            "camera_rules": list(bible.camera_rules),
            "aspect_ratio": bible.aspect_ratio,
            "format_constraints": list(bible.format_constraints),
            "music_language": bible.music_language,
            "ambience": bible.ambience,
            "sfx_language": bible.sfx_language,
            "mixing_constraints": list(bible.mixing_constraints),
            "story_arc": bible.story_arc,
            "season_constraints": list(bible.season_constraints),
        }
    )


def _bible_from_json(raw: str) -> SeriesBible:
    data = _json_object(raw)
    characters_raw = data.get("characters")
    if not isinstance(characters_raw, list):
        raise SeriesStateError("series bible characters must be a list")
    characters: list[CharacterBibleEntry] = []
    for value in characters_raw:
        if not isinstance(value, dict):
            raise SeriesStateError("series bible character must be an object")
        characters.append(
            CharacterBibleEntry(
                character_id=_string(value, "character_id"),
                name=_string(value, "name"),
                appearance=_string(value, "appearance"),
                wardrobe_constraints=_string_tuple(value, "wardrobe_constraints"),
                personality=_string(value, "personality"),
                relationships=_string_tuple(value, "relationships"),
                voice_identity=_nullable_string(value, "voice_identity"),
                reference_assets=_string_tuple(value, "reference_assets"),
                character_arc=_nullable_string(value, "character_arc"),
            )
        )
    return SeriesBible(
        series_id=_string(data, "series_id"),
        revision=_integer(data, "revision"),
        premise=_string(data, "premise"),
        world_rules=_string_tuple(data, "world_rules"),
        characters=tuple(characters),
        cinematography=_string(data, "cinematography"),
        visual_style=_string(data, "visual_style"),
        color_language=_string(data, "color_language"),
        lighting=_string(data, "lighting"),
        locations=_string_tuple(data, "locations"),
        camera_rules=_string_tuple(data, "camera_rules"),
        aspect_ratio=_string(data, "aspect_ratio"),
        format_constraints=_string_tuple(data, "format_constraints"),
        music_language=_string(data, "music_language"),
        ambience=_string(data, "ambience"),
        sfx_language=_string(data, "sfx_language"),
        mixing_constraints=_string_tuple(data, "mixing_constraints"),
        story_arc=_string(data, "story_arc"),
        season_constraints=_string_tuple(data, "season_constraints"),
    )


def _manifest_json(manifest: AcceptedEpisodeManifest) -> str:
    material: dict[str, object] = {}
    for name in manifest.__dataclass_fields__:
        value = getattr(manifest, name)
        material[name] = list(value) if isinstance(value, tuple) else value
    return _dumps(material)


def _manifest_from_json(raw: str) -> AcceptedEpisodeManifest:
    data = _json_object(raw)
    return AcceptedEpisodeManifest(
        series_id=_string(data, "series_id"),
        episode_id=_string(data, "episode_id"),
        episode_number=_integer(data, "episode_number"),
        episode_objective=_string(data, "episode_objective"),
        final_acceptance_id=_string(data, "final_acceptance_id"),
        final_artifact_reference=_string(data, "final_artifact_reference"),
        final_artifact_sha256=_string(data, "final_artifact_sha256"),
        duration_seconds=_integer(data, "duration_seconds"),
        resolution=_string(data, "resolution"),
        script_reference=_string(data, "script_reference"),
        shot_plan_reference=_string(data, "shot_plan_reference"),
        generated_clip_references=_string_tuple(data, "generated_clip_references"),
        source_reference_assets=_string_tuple(data, "source_reference_assets"),
        provider_model_evidence_refs=_string_tuple(data, "provider_model_evidence_refs"),
        voice_references=_string_tuple(data, "voice_references"),
        music_references=_string_tuple(data, "music_references"),
        sfx_references=_string_tuple(data, "sfx_references"),
        caption_artifact_reference=_nullable_string(data, "caption_artifact_reference"),
        edit_timeline_evidence_ref=_string(data, "edit_timeline_evidence_ref"),
        technical_validation_ref=_string(data, "technical_validation_ref"),
        visual_quality_evidence_ref=_string(data, "visual_quality_evidence_ref"),
        audio_quality_evidence_ref=_string(data, "audio_quality_evidence_ref"),
        brand_evidence_ref=_nullable_string(data, "brand_evidence_ref"),
        continuity_evidence_ref=_string(data, "continuity_evidence_ref"),
        final_frame_reference=_string(data, "final_frame_reference"),
        character_reference_frames=_string_tuple(data, "character_reference_frames"),
        location_reference_frames=_string_tuple(data, "location_reference_frames"),
        visual_style_fingerprint=_string(data, "visual_style_fingerprint"),
        color_language=_string(data, "color_language"),
        episode_summary=_string(data, "episode_summary"),
        open_narrative_threads=_string_tuple(data, "open_narrative_threads"),
        resolved_narrative_threads=_string_tuple(data, "resolved_narrative_threads"),
        accepted_at=_string(data, "accepted_at"),
        bible_revision=_integer(data, "bible_revision"),
    )


def _package_json(package: EpisodeContinuityPackage) -> str:
    material: dict[str, object] = {}
    for name in package.__dataclass_fields__:
        value = getattr(package, name)
        material[name] = list(value) if isinstance(value, tuple) else value
    return _dumps(material)


def _dumps(value: dict[str, object]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _json_object(raw: str) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SeriesStateError("stored series JSON is invalid") from exc
    if not isinstance(value, dict):
        raise SeriesStateError("stored series JSON must be an object")
    return value


def _row(value: object) -> sqlite3.Row:
    if not isinstance(value, sqlite3.Row):
        raise SeriesStateError("SQLite series store returned invalid row type")
    return value


def _string(data: dict[str, object], name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str):
        raise SeriesStateError(f"stored {name} must be a string")
    return value


def _nullable_string(data: dict[str, object], name: str) -> str | None:
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise SeriesStateError(f"stored {name} must be string or null")
    return value


def _integer(data: dict[str, object], name: str) -> int:
    value = data.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise SeriesStateError(f"stored {name} must be an integer")
    return value


def _string_tuple(data: dict[str, object], name: str) -> tuple[str, ...]:
    value = data.get(name)
    if not isinstance(value, list):
        raise SeriesStateError(f"stored {name} must be a list")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise SeriesStateError(f"stored {name} entries must be strings")
        output.append(item)
    return tuple(output)


def _text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise SeriesStateError(f"{name} must not be blank")
    if value != value.strip():
        raise SeriesStateError(f"{name} must not contain surrounding whitespace")


def _optional_text(name: str, value: str | None) -> None:
    if value is not None:
        _text(name, value)


def _texts(name: str, values: tuple[str, ...]) -> None:
    for value in values:
        _text(name, value)
    if len(values) != len(set(values)):
        raise SeriesStateError(f"{name} values must be unique")


def _sha256(name: str, value: str) -> None:
    if len(value) != 64:
        raise SeriesStateError(f"{name} must be SHA-256 hex")
    try:
        int(value, 16)
    except ValueError as exc:
        raise SeriesStateError(f"{name} must be SHA-256 hex") from exc
