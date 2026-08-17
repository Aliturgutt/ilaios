"""Capability-aware first/last-frame references for managed video dispatch."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .openrouter_video_catalog import OpenRouterVideoModel


class FrameReferenceRoutingError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class FrameReferenceRequest:
    first_frame_url: str | None = None
    last_frame_url: str | None = None
    require_first_frame: bool = False
    require_last_frame: bool = False

    def __post_init__(self) -> None:
        for name in ("first_frame_url", "last_frame_url"):
            value = getattr(self, name)
            if value is not None:
                _require_https(name, value)
        if self.require_first_frame and self.first_frame_url is None:
            raise FrameReferenceRoutingError(
                "required first_frame reference has no authorized URL"
            )
        if self.require_last_frame and self.last_frame_url is None:
            raise FrameReferenceRoutingError(
                "required last_frame reference has no authorized URL"
            )


def capability_bound_frame_fields(
    *,
    model: OpenRouterVideoModel,
    references: FrameReferenceRequest,
) -> Mapping[str, str]:
    """Return only reference roles the live model proves it supports.

    Required unsupported roles fail closed. Optional unsupported roles are
    omitted, allowing provider-agnostic routing to fall back to text-to-video.
    URLs are assumed to have passed tenant/privacy/reference policy upstream.
    """

    fields: dict[str, str] = {}
    for role, url, required in (
        ("first_frame", references.first_frame_url, references.require_first_frame),
        ("last_frame", references.last_frame_url, references.require_last_frame),
    ):
        if url is None:
            continue
        if model.supports_frame_role(role):
            fields[f"{role}_url"] = url
        elif required:
            raise FrameReferenceRoutingError(
                f"live model does not support required {role} reference"
            )
    return fields


def validate_bound_frame_fields(
    *, item: Mapping[str, object], model: OpenRouterVideoModel
) -> None:
    """Fail closed if caller supplied a role not proven by live catalog."""

    for role in ("first_frame", "last_frame"):
        key = f"{role}_url"
        raw = item.get(key)
        if raw is None:
            continue
        if not isinstance(raw, str):
            raise FrameReferenceRoutingError(f"{key} must be a string")
        _require_https(key, raw)
        if not model.supports_frame_role(role):
            raise FrameReferenceRoutingError(
                f"live model does not support supplied {role} reference"
            )


def build_openrouter_frame_images(item: Mapping[str, object]) -> list[dict[str, object]]:
    """Translate already capability-validated fields to OpenRouter API shape."""

    result: list[dict[str, object]] = []
    for role in ("first_frame", "last_frame"):
        raw = item.get(f"{role}_url")
        if raw is None:
            continue
        if not isinstance(raw, str):
            raise FrameReferenceRoutingError(f"{role}_url must be a string")
        _require_https(f"{role}_url", raw)
        result.append(
            {
                "type": "image_url",
                "image_url": {"url": raw},
                "frame_type": role,
            }
        )
    return result


def _require_https(name: str, value: str) -> None:
    if not value or value != value.strip() or not value.startswith("https://"):
        raise FrameReferenceRoutingError(f"{name} must be a trimmed HTTPS URL")
