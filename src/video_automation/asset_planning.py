"""Deterministic asset planning for canonical ILAIOS Video Automation M10.

M10 converts approved Shot objects into provider-neutral AssetRequest objects.
It does not select providers, invoke providers, generate media, download media,
poll jobs, perform retries, or mutate upstream planning data.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256

from .models import AssetRequest, MediaType, Shot


class AssetPlanningError(ValueError):
    """Raised when shots cannot be converted into valid asset requests."""


class AssetPlanner:
    """Convert approved shots into deterministic AssetRequest objects."""

    def plan(
        self,
        *,
        job_id: str,
        shots: Sequence[Shot],
        media_type_by_capability: Mapping[str, MediaType],
    ) -> tuple[AssetRequest, ...]:
        """Return one provider-neutral AssetRequest for every approved shot.

        The Shot already declares the provider capability it requires.
        M10 does not guess the media type from arbitrary capability text.
        The caller supplies an explicit deterministic capability-to-media-type
        mapping established by the composition/configuration layer.
        """

        _require_non_blank("job_id", job_id)

        planned_shots = tuple(shots)
        if not planned_shots:
            raise AssetPlanningError("shots must not be empty")

        _validate_media_type_mapping(media_type_by_capability)

        shot_ids = tuple(shot.shot_id for shot in planned_shots)
        if len(shot_ids) != len(set(shot_ids)):
            raise AssetPlanningError("shot_id values must be unique")

        requests: list[AssetRequest] = []

        for shot in planned_shots:
            capability = shot.required_provider_capability

            try:
                media_type = media_type_by_capability[capability]
            except KeyError as exc:
                raise AssetPlanningError(
                    "no media type mapping exists for required provider "
                    f"capability: {capability}"
                ) from exc

            canonical_material = "\n".join(
                (
                    f"job_id={job_id}",
                    f"shot_id={shot.shot_id}",
                    f"scene_id={shot.scene_id}",
                    f"media_type={media_type.value}",
                    f"required_capability={capability}",
                    (
                        "estimated_duration_seconds="
                        f"{_format_duration(shot.estimated_duration_seconds)}"
                    ),
                    (
                        "generation_prompt_sha256="
                        f"{sha256(shot.generation_prompt.encode('utf-8')).hexdigest()}"
                    ),
                )
            )

            digest = sha256(canonical_material.encode("utf-8")).hexdigest()

            requests.append(
                AssetRequest(
                    asset_request_id=f"asset-request-{digest[:16]}",
                    job_id=job_id,
                    shot_id=shot.shot_id,
                    media_type=media_type,
                    description=shot.generation_prompt,
                    required_capability=capability,
                    metadata={
                        "scene_id": shot.scene_id,
                        "shot_type": shot.shot_type,
                        "estimated_duration_seconds": (
                            shot.estimated_duration_seconds
                        ),
                        "planning_sha256": digest,
                    },
                )
            )

        return tuple(requests)


def _validate_media_type_mapping(
    media_type_by_capability: Mapping[str, MediaType],
) -> None:
    if not media_type_by_capability:
        raise AssetPlanningError("media_type_by_capability must not be empty")

    for capability, media_type in media_type_by_capability.items():
        _require_non_blank("capability mapping key", capability)
        if not isinstance(media_type, MediaType):
            raise AssetPlanningError(
                "media_type_by_capability values must be MediaType instances"
            )


def _format_duration(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise AssetPlanningError(f"{name} must not be blank")

    if value != value.strip():
        raise AssetPlanningError(
            f"{name} must not contain surrounding whitespace"
        )
