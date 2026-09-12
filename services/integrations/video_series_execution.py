"""Accepted-only series execution lifecycle for canonical Video continuity.

This integration layer reuses ``SeriesStateStore`` as the only durable series
truth. It does not generate media, choose providers, authorize execution, or
create a second runtime. It starts one exact episode against authenticated
series context and promotes only a final Video result whose accepted artifact
matches the immutable episode manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from src.video_automation.series_state import (
    AcceptedEpisodeManifest,
    EpisodePublicationState,
    SeriesState,
    SeriesStateError,
    SeriesStateStore,
)

from .video_series_context import AuthenticatedVideoSeriesContext, VideoSeriesContextError


@dataclass(frozen=True, slots=True)
class VideoSeriesExecution:
    """Exact episode identity bound to authenticated accepted series truth."""

    series_id: str
    episode_id: str
    episode_number: int
    bible_revision: int
    parent_artifact_sha256: str


def begin_authenticated_video_series_execution(
    store: SeriesStateStore,
    context: AuthenticatedVideoSeriesContext,
    *,
    episode_id: str,
) -> VideoSeriesExecution:
    """Begin or resume exactly the next episode for an authenticated series."""

    if not isinstance(episode_id, str) or not episode_id.strip() or episode_id != episode_id.strip():
        raise VideoSeriesContextError("episode_id must be a normalized non-empty string")
    if context.state.series_id != context.bible.series_id:
        raise VideoSeriesContextError("series context bible identity is inconsistent")
    if context.state.bible_revision != context.bible.revision:
        raise VideoSeriesContextError("series context bible revision is stale")
    if context.continuity.series_id != context.state.series_id:
        raise VideoSeriesContextError("series continuity belongs to another series")
    if context.continuity.previous_artifact_sha256 != context.state.latest_artifact_sha256:
        raise VideoSeriesContextError("series continuity parent artifact is stale")

    try:
        store.begin_episode(
            series_id=context.state.series_id,
            episode_id=episode_id,
            episode_number=context.state.next_episode_number,
            checkpoint="SERIES_CONTEXT_BOUND",
        )
    except SeriesStateError as error:
        raise VideoSeriesContextError(str(error)) from error

    return VideoSeriesExecution(
        series_id=context.state.series_id,
        episode_id=episode_id,
        episode_number=context.state.next_episode_number,
        bible_revision=context.bible.revision,
        parent_artifact_sha256=context.previous_manifest.final_artifact_sha256,
    )


def accept_authenticated_video_series_result(
    store: SeriesStateStore,
    execution: VideoSeriesExecution,
    manifest: AcceptedEpisodeManifest,
    runtime_result: Mapping[str, object],
    *,
    publication_state: EpisodePublicationState = (
        EpisodePublicationState.PENDING_EXTERNAL_AUTHORIZATION
    ),
) -> SeriesState:
    """Promote only exact accepted final Video truth into canonical SeriesState."""

    if manifest.series_id != execution.series_id:
        raise VideoSeriesContextError("accepted manifest belongs to another series")
    if manifest.episode_id != execution.episode_id:
        raise VideoSeriesContextError("accepted manifest belongs to another episode")
    if manifest.episode_number != execution.episode_number:
        raise VideoSeriesContextError("accepted manifest episode sequence changed")
    if manifest.bible_revision != execution.bible_revision:
        raise VideoSeriesContextError("accepted manifest uses a stale series bible")

    if runtime_result.get("final_stage") != "completed":
        raise VideoSeriesContextError("series truth requires a completed final Video result")
    qa = runtime_result.get("qa")
    if not isinstance(qa, Mapping) or qa.get("passed") is not True:
        raise VideoSeriesContextError("series truth requires final Video QA acceptance")
    artifact_digest = runtime_result.get("artifact_digest")
    if artifact_digest != manifest.final_artifact_sha256:
        raise VideoSeriesContextError("final Video artifact does not match accepted manifest")

    try:
        persisted_sha = store.persist_accepted_manifest(
            manifest,
            publication_state=publication_state,
        )
        if not isinstance(persisted_sha, str) or len(persisted_sha) != 64:
            raise VideoSeriesContextError("accepted manifest durability evidence is invalid")
        return store.advance_series_from_manifest(
            series_id=execution.series_id,
            episode_id=execution.episode_id,
        )
    except SeriesStateError as error:
        raise VideoSeriesContextError(str(error)) from error


__all__ = [
    "VideoSeriesExecution",
    "accept_authenticated_video_series_result",
    "begin_authenticated_video_series_execution",
]
