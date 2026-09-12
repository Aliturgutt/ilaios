"""Authenticated binding from canonical SeriesState into Video execution context.

This module is an integration adapter only. It reuses the existing durable
SeriesStateStore and does not create a second series store, scheduler, runtime,
or acceptance authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.video_automation.series_state import (
    AcceptedEpisodeManifest,
    EpisodeContinuityPackage,
    SeriesBible,
    SeriesState,
    SeriesStateError,
    SeriesStateStore,
)


class VideoSeriesContextError(ValueError):
    """Raised when authenticated series continuity cannot be proven safely."""


@dataclass(frozen=True, slots=True)
class AuthenticatedVideoSeriesContext:
    """Accepted-only continuity context for one authenticated series request."""

    state: SeriesState
    bible: SeriesBible
    previous_manifest: AcceptedEpisodeManifest
    continuity: EpisodeContinuityPackage


def resolve_authenticated_video_series_context(
    store: SeriesStateStore,
    *,
    series_id: str,
    tenant_id: str,
    user_id: str,
) -> AuthenticatedVideoSeriesContext:
    """Resolve exact accepted continuity for the authenticated series owner.

    Standalone episode text is never sufficient. The caller must provide the
    canonical series identity already bound to the authenticated tenant/user.
    Only the latest accepted manifest can become continuity input.
    """

    for name, value in (
        ("series_id", series_id),
        ("tenant_id", tenant_id),
        ("user_id", user_id),
    ):
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise VideoSeriesContextError(f"{name} must be a normalized non-empty string")

    try:
        state = store.load_series(series_id)
        bible = store.load_bible(series_id)
    except SeriesStateError as error:
        raise VideoSeriesContextError(str(error)) from error

    if state.tenant_id != tenant_id or state.user_id != user_id:
        raise VideoSeriesContextError("series does not belong to authenticated tenant/user")
    if state.bible_revision != bible.revision:
        raise VideoSeriesContextError("series bible revision is stale or inconsistent")
    if state.latest_accepted_episode_id is None or state.latest_artifact_sha256 is None:
        raise VideoSeriesContextError(
            "series continuation requires a previously accepted final episode"
        )

    try:
        manifest = store.load_manifest(state.latest_accepted_episode_id)
    except SeriesStateError as error:
        raise VideoSeriesContextError(str(error)) from error

    if manifest.series_id != state.series_id:
        raise VideoSeriesContextError("latest accepted manifest belongs to another series")
    if manifest.bible_revision != bible.revision:
        raise VideoSeriesContextError("latest accepted manifest uses a stale bible revision")
    if manifest.final_artifact_sha256 != state.latest_artifact_sha256:
        raise VideoSeriesContextError("series state and accepted artifact digest disagree")

    try:
        continuity = store.create_continuity_package(
            episode_id=manifest.episode_id,
            privacy_classification="TENANT_PRIVATE",
            provenance="accepted-episode-manifest",
            last_scene_reference=manifest.final_frame_reference,
            next_scene_constraints=(
                *bible.camera_rules,
                *bible.format_constraints,
                *bible.season_constraints,
            ),
        )
    except SeriesStateError as error:
        raise VideoSeriesContextError(str(error)) from error

    if continuity.previous_artifact_sha256 != manifest.final_artifact_sha256:
        raise VideoSeriesContextError("continuity package is not bound to accepted artifact")
    if continuity.series_bible_revision != bible.revision:
        raise VideoSeriesContextError("continuity package uses a stale bible revision")

    return AuthenticatedVideoSeriesContext(
        state=state,
        bible=bible,
        previous_manifest=manifest,
        continuity=continuity,
    )


__all__ = [
    "AuthenticatedVideoSeriesContext",
    "VideoSeriesContextError",
    "resolve_authenticated_video_series_context",
]
