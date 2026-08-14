"""Finished-video closure over existing editing, QA, and acceptance authorities."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

from .final_episode_acceptance import (
    FinalEpisodeAcceptanceDecision,
    FinalEpisodeAcceptanceStatus,
)


class FinishedProductError(ValueError):
    """Raised when a partial/raw artifact is presented as a finished video."""


@dataclass(frozen=True, slots=True)
class FinishedVideoInputs:
    episode_id: str
    request_id: str
    final_artifact_reference: str
    final_artifact_sha256: str
    duration_seconds: float
    resolution: str
    script_reference: str
    shot_plan_reference: str
    generated_clip_references: tuple[str, ...]
    voice_dialogue_references: tuple[str, ...]
    music_references: tuple[str, ...]
    sfx_references: tuple[str, ...]
    caption_artifact_reference: str
    edit_timeline_evidence_ref: str
    technical_validation_ref: str
    visual_quality_evidence_ref: str
    audio_quality_evidence_ref: str
    brand_quality_evidence_ref: str
    continuity_evidence_ref: str
    thumbnail_reference: str

    def __post_init__(self) -> None:
        for name in (
            "episode_id",
            "request_id",
            "final_artifact_reference",
            "resolution",
            "script_reference",
            "shot_plan_reference",
            "caption_artifact_reference",
            "edit_timeline_evidence_ref",
            "technical_validation_ref",
            "visual_quality_evidence_ref",
            "audio_quality_evidence_ref",
            "brand_quality_evidence_ref",
            "continuity_evidence_ref",
            "thumbnail_reference",
        ):
            _text(name, getattr(self, name))
        _sha256("final_artifact_sha256", self.final_artifact_sha256)
        if self.duration_seconds <= 0:
            raise FinishedProductError("duration_seconds must be positive")
        for name, values in (
            ("generated_clip_references", self.generated_clip_references),
            ("voice_dialogue_references", self.voice_dialogue_references),
            ("music_references", self.music_references),
            ("sfx_references", self.sfx_references),
        ):
            if not values:
                raise FinishedProductError(f"{name} must not be empty")
            for value in values:
                _text(name, value)


@dataclass(frozen=True, slots=True)
class FinishedVideoManifest:
    manifest_id: str
    manifest_sha256: str
    episode_id: str
    request_id: str
    final_artifact_reference: str
    final_artifact_sha256: str
    duration_seconds: float
    resolution: str
    final_acceptance_id: str
    script_reference: str
    shot_plan_reference: str
    generated_clip_references: tuple[str, ...]
    voice_dialogue_references: tuple[str, ...]
    music_references: tuple[str, ...]
    sfx_references: tuple[str, ...]
    caption_artifact_reference: str
    edit_timeline_evidence_ref: str
    technical_validation_ref: str
    visual_quality_evidence_ref: str
    audio_quality_evidence_ref: str
    brand_quality_evidence_ref: str
    continuity_evidence_ref: str
    thumbnail_reference: str


class FinishedVideoFinalizer:
    """Accept only fully evidenced products after canonical final acceptance."""

    def finalize(
        self,
        inputs: FinishedVideoInputs,
        *,
        acceptance: FinalEpisodeAcceptanceDecision,
        final_artifact_bytes: bytes,
    ) -> FinishedVideoManifest:
        if acceptance.status is not FinalEpisodeAcceptanceStatus.ACCEPTED:
            raise FinishedProductError("final episode acceptance must be ACCEPTED")
        if acceptance.episode_id != inputs.episode_id:
            raise FinishedProductError("acceptance episode_id does not match finished inputs")
        if acceptance.request_id != inputs.request_id:
            raise FinishedProductError("acceptance request_id does not match finished inputs")
        if not final_artifact_bytes:
            raise FinishedProductError("final artifact bytes must not be empty")
        observed_sha = sha256(final_artifact_bytes).hexdigest()
        if observed_sha != inputs.final_artifact_sha256:
            raise FinishedProductError("final artifact SHA-256 does not match inputs")

        payload = {
            **asdict(inputs),
            "final_acceptance_id": acceptance.decision_id,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        manifest_sha = sha256(canonical.encode()).hexdigest()
        return FinishedVideoManifest(
            manifest_id=f"finished-video-{manifest_sha[:16]}",
            manifest_sha256=manifest_sha,
            episode_id=inputs.episode_id,
            request_id=inputs.request_id,
            final_artifact_reference=inputs.final_artifact_reference,
            final_artifact_sha256=inputs.final_artifact_sha256,
            duration_seconds=inputs.duration_seconds,
            resolution=inputs.resolution,
            final_acceptance_id=acceptance.decision_id,
            script_reference=inputs.script_reference,
            shot_plan_reference=inputs.shot_plan_reference,
            generated_clip_references=inputs.generated_clip_references,
            voice_dialogue_references=inputs.voice_dialogue_references,
            music_references=inputs.music_references,
            sfx_references=inputs.sfx_references,
            caption_artifact_reference=inputs.caption_artifact_reference,
            edit_timeline_evidence_ref=inputs.edit_timeline_evidence_ref,
            technical_validation_ref=inputs.technical_validation_ref,
            visual_quality_evidence_ref=inputs.visual_quality_evidence_ref,
            audio_quality_evidence_ref=inputs.audio_quality_evidence_ref,
            brand_quality_evidence_ref=inputs.brand_quality_evidence_ref,
            continuity_evidence_ref=inputs.continuity_evidence_ref,
            thumbnail_reference=inputs.thumbnail_reference,
        )


class FinishedVideoManifestStore:
    """Immutable, crash-safe file store for accepted finished-product manifests."""

    def __init__(self, root: Path) -> None:
        self._root = root / "finished_video_manifests"
        self._root.mkdir(parents=True, exist_ok=True)

    def persist(self, manifest: FinishedVideoManifest) -> Path:
        destination = self._root / f"{manifest.episode_id}.json"
        payload = json.dumps(asdict(manifest), sort_keys=True, separators=(",", ":"))
        if destination.exists():
            existing = destination.read_text(encoding="utf-8")
            if existing != payload:
                raise FinishedProductError("finished video manifest is immutable")
            return destination
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(destination)
        return destination

    def load(self, episode_id: str) -> FinishedVideoManifest:
        _text("episode_id", episode_id)
        path = self._root / f"{episode_id}.json"
        if not path.exists():
            raise FinishedProductError("finished video manifest does not exist")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise FinishedProductError("finished video manifest is invalid")
        return FinishedVideoManifest(
            manifest_id=str(data["manifest_id"]),
            manifest_sha256=str(data["manifest_sha256"]),
            episode_id=str(data["episode_id"]),
            request_id=str(data["request_id"]),
            final_artifact_reference=str(data["final_artifact_reference"]),
            final_artifact_sha256=str(data["final_artifact_sha256"]),
            duration_seconds=float(data["duration_seconds"]),
            resolution=str(data["resolution"]),
            final_acceptance_id=str(data["final_acceptance_id"]),
            script_reference=str(data["script_reference"]),
            shot_plan_reference=str(data["shot_plan_reference"]),
            generated_clip_references=_tuple(data["generated_clip_references"]),
            voice_dialogue_references=_tuple(data["voice_dialogue_references"]),
            music_references=_tuple(data["music_references"]),
            sfx_references=_tuple(data["sfx_references"]),
            caption_artifact_reference=str(data["caption_artifact_reference"]),
            edit_timeline_evidence_ref=str(data["edit_timeline_evidence_ref"]),
            technical_validation_ref=str(data["technical_validation_ref"]),
            visual_quality_evidence_ref=str(data["visual_quality_evidence_ref"]),
            audio_quality_evidence_ref=str(data["audio_quality_evidence_ref"]),
            brand_quality_evidence_ref=str(data["brand_quality_evidence_ref"]),
            continuity_evidence_ref=str(data["continuity_evidence_ref"]),
            thumbnail_reference=str(data["thumbnail_reference"]),
        )


def _tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise FinishedProductError("manifest list field is invalid")
    return tuple(value)


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise FinishedProductError(f"{name} must be non-blank and trimmed")


def _sha256(name: str, value: str) -> None:
    if len(value) != 64:
        raise FinishedProductError(f"{name} must be SHA-256 hex")
    try:
        int(value, 16)
    except ValueError as exc:
        raise FinishedProductError(f"{name} must be SHA-256 hex") from exc
