"""OpenRouter-specific reference-to-video capability and payload gates."""

from __future__ import annotations

from collections.abc import Mapping

from .openrouter_video_catalog import OpenRouterVideoModel
from .reference_images import (
    DEFAULT_PROVIDER_REFERENCE_IMAGES,
    ReferenceImageError,
    ReferenceSelection,
    build_openrouter_input_references,
    parse_reference_images,
)

# This is deliberately narrower than the provider's general model allowlist.
# OpenRouter's current reference-to-video cookbook explicitly demonstrates
# Seedance 2.0 Fast. Additional models are promoted only when current provider
# evidence and an adapter regression prove reference semantics for that model.
OPENROUTER_REFERENCE_IMAGE_LIMITS: Mapping[str, int] = {
    "bytedance/seedance-2.0-fast": DEFAULT_PROVIDER_REFERENCE_IMAGES,
}


class OpenRouterReferenceImageError(ValueError):
    """Raised before provider POST when reference semantics are unproven."""


def model_reference_image_limit(model: OpenRouterVideoModel) -> int | None:
    return OPENROUTER_REFERENCE_IMAGE_LIMITS.get(model.model_id)


def validate_reference_image_capability(
    *,
    item: Mapping[str, object],
    model: OpenRouterVideoModel,
) -> ReferenceSelection | None:
    """Validate reference-to-video intent against explicit model evidence."""

    try:
        references = parse_reference_images(item.get("reference_images"))
    except ReferenceImageError as exc:
        raise OpenRouterReferenceImageError(str(exc)) from exc
    if not references:
        return None
    if item.get("first_frame_url") is not None or item.get("last_frame_url") is not None:
        raise OpenRouterReferenceImageError(
            "generic reference images cannot be combined with first/last-frame anchors; "
            "choose reference-to-video or exact frame control explicitly"
        )
    limit = model_reference_image_limit(model)
    if limit is None:
        raise OpenRouterReferenceImageError(
            "current model has no verified reference-to-video capability evidence"
        )
    try:
        _, selection = build_openrouter_input_references(
            references,
            provider_limit=limit,
        )
    except ReferenceImageError as exc:
        raise OpenRouterReferenceImageError(str(exc)) from exc
    return selection


def build_reference_to_video_fields(
    *,
    item: Mapping[str, object],
    model_id: str,
) -> tuple[dict[str, object], ReferenceSelection | None]:
    """Build provider fields after the gateway has already capability-gated them."""

    try:
        references = parse_reference_images(item.get("reference_images"))
    except ReferenceImageError as exc:
        raise OpenRouterReferenceImageError(str(exc)) from exc
    if not references:
        return {}, None
    if item.get("first_frame_url") is not None or item.get("last_frame_url") is not None:
        raise OpenRouterReferenceImageError(
            "reference images and frame anchors are mutually exclusive"
        )
    limit = OPENROUTER_REFERENCE_IMAGE_LIMITS.get(model_id)
    if limit is None:
        raise OpenRouterReferenceImageError(
            "model is not approved for OpenRouter reference-to-video dispatch"
        )
    try:
        payload, selection = build_openrouter_input_references(
            references,
            provider_limit=limit,
        )
    except ReferenceImageError as exc:
        raise OpenRouterReferenceImageError(str(exc)) from exc
    return {"input_references": payload}, selection
