from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

import pytest

from services.integrations.video_editing import GovernedVideoEditExecutor
from services.integrations.video_revision import (
    GovernedVideoRevisionExecutor,
    VideoRevisionError,
    derive_video_revision_spec,
)
from services.source_media import SourceMediaRecord, SourceMediaStore
from src.video_automation.media_technical_validation import MediaProbeObservation
from src.video_automation.perceptual_review import (
    PerceptualReviewSubmission,
    PerceptualReviewerKind,
)
from src.video_automation.video_editing import EditExecutionResult
from src.video_automation.video_skills import EditKind, EditOperation, QaDomain


def _source(*, digest: str = "a" * 64) -> SourceMediaRecord:
    return SourceMediaRecord(
        asset_id="src-1234567890abcdef12345678",
        principal_id="principal-1",
        tenant_id="tenant-1",
        sha256=digest,
        mime_type="video/mp4",
        original_filename="source.mp4",
        size_bytes=1024,
        duration_seconds=30.0,
        width=1920,
        height=1080,
        frames_per_second=24.0,
        video_codec="h264",
        audio_codec="aac",
        probe_id="test-probe",
        created_at=datetime.now(timezone.utc),
    )


def test_revision_parser_materializes_explicit_trim_crop_and_resize() -> None:
    source = _source()

    trim = derive_video_revision_spec(
        "Trim this video from 00:00:05 to 00:00:12.",
        source=source,
    )
    assert trim.kind is EditKind.TRIM
    assert trim.parameters == {"duration_seconds": 7.0, "start_seconds": 5.0}

    crop = derive_video_revision_spec(
        "Crop this video to 1080x1080 at x=200 y=0.",
        source=source,
    )
    assert crop.kind is EditKind.CROP
    assert crop.parameters == {"height": 1080, "width": 1080, "x": 200, "y": 0}

    scale = derive_video_revision_spec(
        "Resize this video to 1080x1920 at 30 fps.",
        source=source,
    )
    assert scale.kind is EditKind.SCALE
    assert scale.parameters == {
        "audio_codec": "aac",
        "fps": 30,
        "height": 1920,
        "video_codec": "libx264",
        "width": 1080,
    }


def test_revision_parser_fails_closed_on_ambiguous_or_out_of_range_work() -> None:
    source = _source()
    with pytest.raises(VideoRevisionError, match="multiple edit operations"):
        derive_video_revision_spec(
            "Trim this video from 5 to 10 and resize this video to 1280x720.",
            source=source,
        )
    with pytest.raises(VideoRevisionError, match="exceeds authenticated source duration"):
        derive_video_revision_spec(
            "Trim this video from 10 to 50.",
            source=source,
        )
    with pytest.raises(VideoRevisionError, match="exceeds authenticated source geometry"):
        derive_video_revision_spec(
            "Crop this video to 1900x1000 at x=100 y=100.",
            source=source,
        )
    with pytest.raises(VideoRevisionError, match="explicit supported"):
        derive_video_revision_spec(
            "Edit this video and make it more exciting.",
            source=source,
        )


class _SourceStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def require_registered_path(self, asset_id: str) -> Path:
        assert asset_id == "src-1234567890abcdef12345678"
        return self.path


class _Editor:
    def __init__(self, output: Path) -> None:
        self.output = output
        self.operations: list[EditOperation] = []

    def execute(self, operation: EditOperation) -> EditExecutionResult:
        self.operations.append(operation)
        body = b"revised-video-bytes"
        self.output.write_bytes(body)
        return EditExecutionResult(
            operation_id=operation.operation_id,
            output_asset_id=operation.output_asset_id,
            output_path=str(self.output),
            sha256_hex=hashlib.sha256(body).hexdigest(),
            byte_length=len(body),
            command=("ffmpeg", "bounded-test"),
        )


class _Probe:
    @property
    def probe_id(self) -> str:
        return "test-probe"

    def probe(self, path: Path) -> MediaProbeObservation:
        duration = 30.0 if path.name == "source.mp4" else 7.0
        return MediaProbeObservation(
            container="mov,mp4,m4a,3gp,3g2,mj2",
            duration_seconds=duration,
            width=1920,
            height=1080,
            frames_per_second=24.0,
            video_codec="h264",
            audio_codec="aac",
            video_stream_count=1,
            audio_stream_count=1,
        )


@dataclass
class _Reviewer:
    calls: int = 0

    @property
    def reviewer_id(self) -> str:
        return "independent-reviewer"

    def review(
        self,
        *,
        video_path: Path,
        objective: str,
        artifact_sha256: str,
        producer_id: str,
        review_id: str,
    ) -> PerceptualReviewSubmission:
        del video_path, objective
        self.calls += 1
        return PerceptualReviewSubmission(
            review_id=review_id,
            domain=QaDomain.VISUAL,
            artifact_sha256=artifact_sha256,
            reviewer_id=self.reviewer_id,
            producer_id=producer_id,
            reviewer_kind=PerceptualReviewerKind.INDEPENDENT_MODEL,
            criteria_id="test-criteria",
            criteria_version="1.0.0",
            criteria_sha256="b" * 64,
            score=0.95,
            threshold=0.8,
            evidence_references=(f"evidence:{review_id}",),
            provenance_reference=f"review:{review_id}",
        )


def test_revision_executor_binds_source_and_output_digests_with_before_after_qa(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.mp4"
    source_body = b"authenticated-source-video"
    source_path.write_bytes(source_body)
    output_path = tmp_path / "output.mp4"
    source = _source(digest=hashlib.sha256(source_body).hexdigest())
    editor = _Editor(output_path)
    reviewer = _Reviewer()

    executor = GovernedVideoRevisionExecutor(
        cast(SourceMediaStore, _SourceStore(source_path)),
        cast(GovernedVideoEditExecutor, editor),
        reviewer,
        probe=_Probe(),
    )
    outcome = executor.execute(
        request_id="request-1",
        objective="Trim this video from 5 to 12.",
        source=source,
    )

    assert outcome.spec.kind is EditKind.TRIM
    assert outcome.spec.source_sha256 == source.sha256
    assert outcome.edit.sha256_hex == hashlib.sha256(b"revised-video-bytes").hexdigest()
    assert outcome.output_observation.duration_seconds == 7.0
    assert reviewer.calls == 2
    assert len(editor.operations) == 1
    assert editor.operations[0].input_asset_ids == (source.asset_id,)
    assert outcome.to_runtime_outcome()["revision_provider_generation_used"] is False
