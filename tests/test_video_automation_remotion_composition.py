"""Tests for canonical M19 Remotion Composition Adapter."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.video_automation.models import (
    MediaAsset,
    MediaType,
    Timeline,
    TimelineItem,
)
from src.video_automation.remotion_composition import (
    RemotionCompositionAdapter,
    RemotionCompositionArtifact,
    RemotionCompositionElement,
    RemotionCompositionError,
)


def _asset(
    asset_id: str,
    media_type: MediaType,
    *,
    validated: bool = True,
    job_id: str = "job-1",
) -> MediaAsset:
    return MediaAsset(
        asset_id=asset_id,
        job_id=job_id,
        media_type=media_type,
        file_path=f"C:/canonical/{asset_id}.bin",
        checksum_sha256=sha256(
            asset_id.encode("utf-8")
        ).hexdigest(),
        provider_name="canonical-test",
        source_reference=f"local://{asset_id}",
        validated=validated,
    )


def _timeline() -> Timeline:
    return Timeline(
        job_id="job-1",
        items=(
            TimelineItem(
                item_id="timeline-video",
                asset_id="video-1",
                start_seconds=0.0,
                duration_seconds=5.0,
                layer=0,
            ),
            TimelineItem(
                item_id="timeline-voice",
                asset_id="voice-1",
                start_seconds=0.0,
                duration_seconds=5.0,
                layer=10,
            ),
        ),
    )


def _assets() -> tuple[MediaAsset, ...]:
    return (
        _asset(
            "video-1",
            MediaType.VIDEO,
        ),
        _asset(
            "voice-1",
            MediaType.VOICE,
        ),
    )


def test_prepare_writes_manifest_and_tsx_adapter_source() -> None:
    with TemporaryDirectory() as directory_name:
        artifact = RemotionCompositionAdapter().prepare(
            job_id="job-1",
            timeline=_timeline(),
            assets=_assets(),
            elements=(),
            output_directory=directory_name,
            duration_seconds=5.0,
            fps=30,
            width=720,
            height=1280,
        )

        assert isinstance(
            artifact,
            RemotionCompositionArtifact,
        )

        manifest = Path(
            artifact.manifest_path
        )
        source = Path(
            artifact.entry_source_path
        )

        assert manifest.is_file()
        assert source.is_file()

        assert (
            sha256(manifest.read_bytes()).hexdigest()
            == artifact.manifest_sha256
        )

        assert (
            sha256(source.read_bytes()).hexdigest()
            == artifact.entry_source_sha256
        )


def test_manifest_contains_timeline_frame_mapping() -> None:
    with TemporaryDirectory() as directory_name:
        artifact = RemotionCompositionAdapter().prepare(
            job_id="job-1",
            timeline=_timeline(),
            assets=_assets(),
            elements=(),
            output_directory=directory_name,
            duration_seconds=5.0,
            fps=30,
            width=720,
            height=1280,
        )

        payload = json.loads(
            Path(
                artifact.manifest_path
            ).read_text(encoding="utf-8")
        )

        assert payload["engine"] == "remotion"
        assert payload["composition"]["fps"] == 30
        assert (
            payload["composition"]["duration_frames"]
            == 150
        )

        assert payload["timeline"][0]["start_frame"] == 0
        assert (
            payload["timeline"][0]["duration_frames"]
            == 150
        )


def test_all_canonical_visual_element_kinds_are_supported() -> None:
    kinds = (
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
    )

    elements = tuple(
        RemotionCompositionElement(
            element_id=f"element-{index}",
            kind=kind,
            start_seconds=0.0,
            duration_seconds=1.0,
            layer=index,
            payload={
                "value": kind,
            },
        )
        for index, kind in enumerate(
            kinds,
            start=1,
        )
    )

    with TemporaryDirectory() as directory_name:
        artifact = RemotionCompositionAdapter().prepare(
            job_id="job-1",
            timeline=_timeline(),
            assets=_assets(),
            elements=elements,
            output_directory=directory_name,
            duration_seconds=5.0,
            fps=30,
            width=720,
            height=1280,
        )

        payload = json.loads(
            Path(
                artifact.manifest_path
            ).read_text(encoding="utf-8")
        )

        assert tuple(
            item["kind"]
            for item in payload["elements"]
        ) == kinds


def test_dynamic_caption_is_adapter_instruction_not_rendered_output() -> None:
    caption = RemotionCompositionElement(
        element_id="caption-1",
        kind="dynamic_caption",
        start_seconds=1.0,
        duration_seconds=2.0,
        layer=50,
        payload={
            "text": "The origin awakens.",
            "style": "short-form-dynamic",
        },
    )

    with TemporaryDirectory() as directory_name:
        artifact = RemotionCompositionAdapter().prepare(
            job_id="job-1",
            timeline=_timeline(),
            assets=_assets(),
            elements=(caption,),
            output_directory=directory_name,
            duration_seconds=5.0,
            fps=30,
            width=720,
            height=1280,
        )

        payload = json.loads(
            Path(
                artifact.manifest_path
            ).read_text(encoding="utf-8")
        )

        element = payload["elements"][0]

        assert element["kind"] == "dynamic_caption"
        assert element["start_frame"] == 30
        assert element["duration_frames"] == 60
        assert (
            element["payload"]["text"]
            == "The origin awakens."
        )


def test_composition_is_deterministic() -> None:
    element = RemotionCompositionElement(
        element_id="title-1",
        kind="title",
        start_seconds=0.0,
        duration_seconds=1.0,
        layer=20,
        payload={"text": "THE LAST ORIGIN"},
    )

    adapter = RemotionCompositionAdapter()

    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        first = adapter.prepare(
            job_id="job-1",
            timeline=_timeline(),
            assets=_assets(),
            elements=(element,),
            output_directory=root / "first",
            duration_seconds=5.0,
            fps=30,
            width=720,
            height=1280,
        )

        second = adapter.prepare(
            job_id="job-1",
            timeline=_timeline(),
            assets=_assets(),
            elements=(element,),
            output_directory=root / "second",
            duration_seconds=5.0,
            fps=30,
            width=720,
            height=1280,
        )

        assert (
            first.composition_id
            == second.composition_id
        )

        assert (
            first.manifest_sha256
            == second.manifest_sha256
        )

        assert (
            first.entry_source_sha256
            == second.entry_source_sha256
        )


def test_unvalidated_asset_fails_closed() -> None:
    assets = (
        _asset(
            "video-1",
            MediaType.VIDEO,
            validated=False,
        ),
        _asset(
            "voice-1",
            MediaType.VOICE,
        ),
    )

    with TemporaryDirectory() as directory_name, pytest.raises(
        RemotionCompositionError,
        match="must be validated",
    ):
        RemotionCompositionAdapter().prepare(
            job_id="job-1",
            timeline=_timeline(),
            assets=assets,
            elements=(),
            output_directory=directory_name,
            duration_seconds=5.0,
            fps=30,
            width=720,
            height=1280,
        )


def test_asset_set_must_exactly_match_timeline() -> None:
    assets = (
        _asset(
            "video-1",
            MediaType.VIDEO,
        ),
    )

    with TemporaryDirectory() as directory_name, pytest.raises(
        RemotionCompositionError,
        match="exactly match",
    ):
        RemotionCompositionAdapter().prepare(
            job_id="job-1",
            timeline=_timeline(),
            assets=assets,
            elements=(),
            output_directory=directory_name,
            duration_seconds=5.0,
            fps=30,
            width=720,
            height=1280,
        )


def test_element_outside_composition_duration_fails_closed() -> None:
    element = RemotionCompositionElement(
        element_id="title-1",
        kind="title",
        start_seconds=4.5,
        duration_seconds=1.0,
        layer=20,
        payload={
            "text": "Too late",
        },
    )

    with TemporaryDirectory() as directory_name, pytest.raises(
        RemotionCompositionError,
        match="exceeds duration",
    ):
        RemotionCompositionAdapter().prepare(
            job_id="job-1",
            timeline=_timeline(),
            assets=_assets(),
            elements=(element,),
            output_directory=directory_name,
            duration_seconds=5.0,
            fps=30,
            width=720,
            height=1280,
        )


def test_unknown_element_kind_fails_closed() -> None:
    with pytest.raises(
        RemotionCompositionError,
        match="unsupported",
    ):
        RemotionCompositionElement(
            element_id="unknown-1",
            kind="unknown",
            start_seconds=0.0,
            duration_seconds=1.0,
            layer=0,
            payload={
                "value": "x",
            },
        )


def test_duplicate_element_ids_fail_closed() -> None:
    first = RemotionCompositionElement(
        element_id="same",
        kind="title",
        start_seconds=0.0,
        duration_seconds=1.0,
        layer=1,
        payload={"text": "One"},
    )

    second = RemotionCompositionElement(
        element_id="same",
        kind="overlay",
        start_seconds=1.0,
        duration_seconds=1.0,
        layer=2,
        payload={"text": "Two"},
    )

    with TemporaryDirectory() as directory_name, pytest.raises(
        RemotionCompositionError,
        match="identifiers must be unique",
    ):
        RemotionCompositionAdapter().prepare(
            job_id="job-1",
            timeline=_timeline(),
            assets=_assets(),
            elements=(first, second),
            output_directory=directory_name,
            duration_seconds=5.0,
            fps=30,
            width=720,
            height=1280,
        )
