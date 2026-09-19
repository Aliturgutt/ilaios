"""Authenticated binding from canonical SeriesState into Video execution context.

This module is an integration adapter only. It reuses the existing durable
SeriesStateStore and the canonical provider runtime's existing objective
resolver injection point. It does not create a second series store, scheduler,
runtime, provider, reviewer, or acceptance authority.
"""

from __future__ import annotations

from collections.abc import Callable
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


SeriesProjectResolver = Callable[[str, str, str], str]


@dataclass(frozen=True, slots=True)
class AuthenticatedVideoSeriesContext:
    """Accepted-only continuity context for one authenticated series request."""

    project_id: str
    state: SeriesState
    bible: SeriesBible
    previous_manifest: AcceptedEpisodeManifest
    continuity: EpisodeContinuityPackage


def resolve_authenticated_video_series_context(
    store: SeriesStateStore,
    *,
    series_id: str,
    project_id: str,
    tenant_id: str,
    user_id: str,
    series_project_resolver: SeriesProjectResolver,
) -> AuthenticatedVideoSeriesContext:
    """Resolve accepted continuity for one explicit authenticated project/series.

    Standalone episode text is never sufficient. The caller must supply both
    project and series identity, and the incumbent project owner must prove that
    exact series belongs to that project under the authenticated tenant/user.
    """

    for name, value in (
        ("series_id", series_id),
        ("project_id", project_id),
        ("tenant_id", tenant_id),
        ("user_id", user_id),
    ):
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise VideoSeriesContextError(f"{name} must be a normalized non-empty string")

    bound_project_id = series_project_resolver(series_id, tenant_id, user_id)
    if not isinstance(bound_project_id, str) or not bound_project_id.strip():
        raise VideoSeriesContextError("series project ownership could not be proven")
    if bound_project_id != project_id:
        raise VideoSeriesContextError("series does not belong to authenticated project")

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
            provenance=f"accepted-episode-manifest:{project_id}:{series_id}",
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
        project_id=project_id,
        state=state,
        bible=bible,
        previous_manifest=manifest,
        continuity=continuity,
    )


def bind_series_context_to_objective_resolver(
    objective_resolver: Callable[[str], str],
    context_resolver: Callable[[str], AuthenticatedVideoSeriesContext | None],
) -> Callable[[str], str]:
    """Feed accepted series continuity into the canonical runtime planning input."""

    def resolve(job_id: str) -> str:
        objective = objective_resolver(job_id).strip()
        if not objective:
            return objective
        context = context_resolver(job_id)
        if context is None:
            return objective
        continuity = context.continuity
        bible = context.bible
        if continuity.series_id != context.state.series_id:
            raise VideoSeriesContextError("series continuity belongs to another series")
        if continuity.previous_artifact_sha256 != context.previous_manifest.final_artifact_sha256:
            raise VideoSeriesContextError("series continuity parent artifact is stale")
        if continuity.series_bible_revision != bible.revision:
            raise VideoSeriesContextError("series continuity uses a stale bible revision")

        constraints = " | ".join(continuity.next_scene_constraints)
        characters = " | ".join(continuity.character_references)
        locations = " | ".join(continuity.location_references)
        voices = " | ".join(continuity.voice_references)
        return (
            f"{objective}\n\n"
            "SERIES CONTINUITY — accepted prior truth only:\n"
            f"project_id={context.project_id}\n"
            f"series_id={context.state.series_id}\n"
            f"series_bible_revision={bible.revision}\n"
            f"previous_artifact_sha256={continuity.previous_artifact_sha256}\n"
            f"previous_final_frame={continuity.previous_final_frame}\n"
            f"previous_episode_summary={continuity.previous_episode_summary}\n"
            f"visual_style={bible.visual_style}\n"
            f"color_language={continuity.color_language}\n"
            f"character_references={characters}\n"
            f"location_references={locations}\n"
            f"voice_references={voices}\n"
            f"next_scene_constraints={constraints}\n"
            "Preserve these accepted continuity facts unless the authenticated "
            "series request explicitly advances them."
        )

    return resolve


__all__ = [
    "AuthenticatedVideoSeriesContext",
    "SeriesProjectResolver",
    "VideoSeriesContextError",
    "bind_series_context_to_objective_resolver",
    "resolve_authenticated_video_series_context",
]
