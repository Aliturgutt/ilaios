"""Canonical M19 Remotion Composition Adapter.

M19 converts validated timeline evidence and explicit visual-composition
instructions into deterministic Remotion-facing artifacts.

It supports composition instructions for:

- titles
- animated text
- lower thirds
- overlays
- branded layouts
- transitions
- charts
- progress indicators
- reusable visual templates
- dynamic captions

M19 does not perform the final render. Rendering into RenderArtifact belongs
to canonical M20.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType

from .models import MediaAsset, Timeline

_ALLOWED_KINDS = frozenset(
    {
        "title",
        "animated_text",
        "lower_third",
        "overlay",
        "branded_layout",
        "transition",
        "chart",
        "progress_indicator",
        "visual_template",
        "dynamic_caption",
    }
)


class RemotionCompositionError(ValueError):
    """Raised when M19 composition planning cannot proceed safely."""


@dataclass(frozen=True, slots=True)
class RemotionCompositionElement:
    """One explicit programmatic composition instruction."""

    element_id: str
    kind: str
    start_seconds: float
    duration_seconds: float
    layer: int
    payload: Mapping[str, str]

    def __post_init__(self) -> None:
        _require_non_blank("element_id", self.element_id)
        _require_non_blank("kind", self.kind)

        if self.kind not in _ALLOWED_KINDS:
            raise RemotionCompositionError(
                f"unsupported Remotion composition kind: {self.kind}"
            )

        if self.start_seconds < 0:
            raise RemotionCompositionError(
                "start_seconds must be greater than or equal to zero"
            )

        if self.duration_seconds <= 0:
            raise RemotionCompositionError(
                "duration_seconds must be greater than zero"
            )

        if self.layer < 0:
            raise RemotionCompositionError(
                "layer must be greater than or equal to zero"
            )

        normalized = dict(self.payload)

        for key, value in normalized.items():
            _require_non_blank("payload key", key)
            _require_non_blank(
                f"payload value for {key}",
                value,
            )

        object.__setattr__(
            self,
            "payload",
            MappingProxyType(dict(sorted(normalized.items()))),
        )


@dataclass(frozen=True, slots=True)
class RemotionCompositionArtifact:
    """Deterministic M19 adapter output consumed later by M20."""

    composition_id: str
    job_id: str
    manifest_path: str
    manifest_sha256: str
    entry_source_path: str
    entry_source_sha256: str
    duration_seconds: float
    fps: int
    width: int
    height: int

    def __post_init__(self) -> None:
        for name in (
            "composition_id",
            "job_id",
            "manifest_path",
            "entry_source_path",
        ):
            _require_non_blank(
                name,
                getattr(self, name),
            )

        _validate_sha256(self.manifest_sha256)
        _validate_sha256(self.entry_source_sha256)

        if self.duration_seconds <= 0:
            raise RemotionCompositionError(
                "duration_seconds must be greater than zero"
            )

        if self.fps <= 0:
            raise RemotionCompositionError(
                "fps must be greater than zero"
            )

        if self.width <= 0 or self.height <= 0:
            raise RemotionCompositionError(
                "width and height must be greater than zero"
            )


class RemotionCompositionAdapter:
    """Create deterministic Remotion-facing composition artifacts."""

    def prepare(
        self,
        *,
        job_id: str,
        timeline: Timeline,
        assets: tuple[MediaAsset, ...],
        elements: tuple[RemotionCompositionElement, ...],
        output_directory: str | Path,
        duration_seconds: float,
        fps: int,
        width: int,
        height: int,
    ) -> RemotionCompositionArtifact:
        """Prepare manifest and TSX entry source without rendering."""

        _require_non_blank("job_id", job_id)

        if timeline.job_id != job_id:
            raise RemotionCompositionError(
                "timeline job_id does not match requested job_id"
            )

        if duration_seconds <= 0:
            raise RemotionCompositionError(
                "duration_seconds must be greater than zero"
            )

        if fps <= 0:
            raise RemotionCompositionError(
                "fps must be greater than zero"
            )

        if width <= 0 or height <= 0:
            raise RemotionCompositionError(
                "width and height must be greater than zero"
            )

        if not timeline.items:
            raise RemotionCompositionError(
                "timeline must contain at least one item"
            )

        if not assets:
            raise RemotionCompositionError(
                "assets must contain at least one MediaAsset"
            )

        asset_by_id = {
            asset.asset_id: asset
            for asset in assets
        }

        if len(asset_by_id) != len(assets):
            raise RemotionCompositionError(
                "asset identifiers must be unique"
            )

        timeline_asset_ids = {
            item.asset_id
            for item in timeline.items
        }

        if set(asset_by_id) != timeline_asset_ids:
            raise RemotionCompositionError(
                "assets must exactly match timeline asset identifiers"
            )

        for asset in assets:
            if asset.job_id != job_id:
                raise RemotionCompositionError(
                    "asset job_id does not match requested job_id"
                )

            if not asset.validated:
                raise RemotionCompositionError(
                    f"Remotion input asset must be validated: {asset.asset_id}"
                )

        element_ids = tuple(
            element.element_id
            for element in elements
        )

        if len(element_ids) != len(set(element_ids)):
            raise RemotionCompositionError(
                "composition element identifiers must be unique"
            )

        for element in elements:
            if (
                element.start_seconds
                + element.duration_seconds
                > duration_seconds + 1e-9
            ):
                raise RemotionCompositionError(
                    f"composition element exceeds duration: "
                    f"{element.element_id}"
                )

        ordered_elements = tuple(
            sorted(
                elements,
                key=lambda element: (
                    element.start_seconds,
                    element.layer,
                    element.element_id,
                ),
            )
        )

        ordered_timeline_items = tuple(
            sorted(
                timeline.items,
                key=lambda item: (
                    item.start_seconds,
                    item.layer,
                    item.asset_id,
                    item.item_id,
                ),
            )
        )

        manifest_payload = {
            "schema_version": 1,
            "engine": "remotion",
            "job_id": job_id,
            "composition": {
                "duration_seconds": duration_seconds,
                "duration_frames": round(duration_seconds * fps),
                "fps": fps,
                "width": width,
                "height": height,
            },
            "timeline": [
                {
                    "item_id": item.item_id,
                    "asset_id": item.asset_id,
                    "file_path": asset_by_id[
                        item.asset_id
                    ].file_path,
                    "checksum_sha256": asset_by_id[
                        item.asset_id
                    ].checksum_sha256,
                    "media_type": asset_by_id[
                        item.asset_id
                    ].media_type.value,
                    "start_seconds": item.start_seconds,
                    "duration_seconds": item.duration_seconds,
                    "start_frame": round(item.start_seconds * fps),
                    "duration_frames": round(item.duration_seconds * fps),
                    "layer": item.layer,
                }
                for item in ordered_timeline_items
            ],
            "elements": [
                {
                    "element_id": element.element_id,
                    "kind": element.kind,
                    "start_seconds": element.start_seconds,
                    "duration_seconds": element.duration_seconds,
                    "start_frame": round(element.start_seconds * fps),
                    "duration_frames": round(element.duration_seconds * fps),
                    "layer": element.layer,
                    "payload": dict(element.payload),
                }
                for element in ordered_elements
            ],
        }

        canonical_json = json.dumps(
            manifest_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        composition_id = (
            "remotion-composition-"
            + sha256(
                canonical_json.encode("utf-8")
            ).hexdigest()[:24]
        )

        output_root = Path(output_directory)
        output_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        manifest_path = (
            output_root
            / f"{composition_id}.json"
        )

        entry_path = (
            output_root
            / f"{composition_id}.tsx"
        )

        manifest_text = (
            json.dumps(
                manifest_payload,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        )

        entry_source = _build_entry_source(
            composition_id=composition_id,
            manifest_filename=manifest_path.name,
        )

        _write_text(
            manifest_path,
            manifest_text,
        )
        _write_text(
            entry_path,
            entry_source,
        )

        manifest_digest = sha256(
            manifest_path.read_bytes()
        ).hexdigest()

        entry_digest = sha256(
            entry_path.read_bytes()
        ).hexdigest()

        return RemotionCompositionArtifact(
            composition_id=composition_id,
            job_id=job_id,
            manifest_path=str(
                manifest_path.resolve()
            ),
            manifest_sha256=manifest_digest,
            entry_source_path=str(
                entry_path.resolve()
            ),
            entry_source_sha256=entry_digest,
            duration_seconds=duration_seconds,
            fps=fps,
            width=width,
            height=height,
        )


def _build_entry_source(
    *,
    composition_id: str,
    manifest_filename: str,
) -> str:
    """Return deterministic Remotion adapter entry source.

    This deliberately remains adapter source only. M20 owns actual render
    execution and may supply the concrete project/runtime implementation.
    """

    return (
        'import manifest from "./'
        + manifest_filename
        + '";\n\n'
        + "export const ilaiosComposition = {\n"
        + f'  id: "{composition_id}",\n'
        + "  manifest,\n"
        + "} as const;\n"
    )


def _write_text(
    path: Path,
    content: str,
) -> None:
    try:
        path.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )
    except OSError as exc:
        raise RemotionCompositionError(
            f"failed to write Remotion composition artifact: {path}"
        ) from exc


def _validate_sha256(value: str) -> None:
    if len(value) != 64:
        raise RemotionCompositionError(
            "SHA-256 digest must contain 64 hexadecimal characters"
        )

    try:
        int(value, 16)
    except ValueError as exc:
        raise RemotionCompositionError(
            "SHA-256 digest must contain 64 hexadecimal characters"
        ) from exc


def _require_non_blank(
    name: str,
    value: str,
) -> None:
    if not value or not value.strip():
        raise RemotionCompositionError(
            f"{name} must not be blank"
        )

    if value != value.strip():
        raise RemotionCompositionError(
            f"{name} must not contain surrounding whitespace"
        )
