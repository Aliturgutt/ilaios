from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

import pytest

from services.integrations.provider_video_runtime import SemanticVideoReviewer
from services.integrations.reference_aware_provider_video_runtime import (
    ReferenceAwareProviderBackedDesktopVideoRuntime,
    _RevisionReferenceReviewer,
)
from services.integrations.video_product_intelligence import (
    admit_current_desktop_video_product,
)
from services.integrations.video_runtime import VideoRuntimeError
from src.video_automation.perceptual_review import PerceptualReviewSubmission
from src.video_automation.reference_image_analysis import ReferenceVisualBrief


class _EmptyReferenceStore:
    def for_request(self, request_id: str) -> tuple[object, ...]:
        assert request_id == "request-guard"
        return ()


class _BoundReferenceStore:
    def for_request(self, request_id: str) -> tuple[object, ...]:
        assert request_id == "request-guard"
        return (object(),)


@dataclass(frozen=True)
class _SourceRecord:
    asset_id: str = "src-test"


class _SourceStore:
    def __init__(self, *, bound: bool = False) -> None:
        self.bound = bound
        self.path_checks = 0

    def for_request(self, request_id: str) -> _SourceRecord | None:
        assert request_id == "request-guard"
        return _SourceRecord() if self.bound else None

    def require_registered_path(self, asset_id: str) -> Path:
        assert asset_id == "src-test"
        self.path_checks += 1
        return Path("source.mp4")


def _runtime(
    *, source_bound: bool = False
) -> ReferenceAwareProviderBackedDesktopVideoRuntime:
    runtime = object.__new__(ReferenceAwareProviderBackedDesktopVideoRuntime)
    setattr(runtime, "_reference_assets", _EmptyReferenceStore())
    setattr(runtime, "_source_media", _SourceStore(bound=source_bound))
    return runtime


def test_vertical_request_is_admitted_by_product_guard() -> None:
    spec = admit_current_desktop_video_product(
        "Create a vertical 9:16 video for TikTok."
    )

    assert spec.aspect_ratio == "9:16"


def test_source_video_revision_is_rejected_before_provider_generation(
    tmp_path: Path,
) -> None:
    runtime = _runtime()
    with pytest.raises(VideoRuntimeError, match="authenticated source video"):
        runtime._generate_finished_product(
            run_root=tmp_path,
            request_id="request-guard",
            job_id="job-guard",
            objective="Edit this video and shorten the ending.",
            duration_seconds=20.0,
        )


def test_bound_source_is_verified_then_revision_fails_before_provider_generation(
    tmp_path: Path,
) -> None:
    runtime = _runtime(source_bound=True)
    source_store = cast(_SourceStore, runtime._source_media)
    with pytest.raises(VideoRuntimeError, match="not materialized"):
        runtime._generate_finished_product(
            run_root=tmp_path,
            request_id="request-guard",
            job_id="job-guard",
            objective="Edit this video and shorten the ending.",
            duration_seconds=20.0,
        )
    assert source_store.path_checks == 1


def test_bound_source_is_never_dropped_from_plain_create_request(tmp_path: Path) -> None:
    runtime = _runtime(source_bound=True)
    with pytest.raises(VideoRuntimeError, match="silently ignore source media"):
        runtime._generate_finished_product(
            run_root=tmp_path,
            request_id="request-guard",
            job_id="job-guard",
            objective="Create a cinematic launch video.",
            duration_seconds=20.0,
        )


def test_bound_source_revision_dispatches_to_revision_path_with_references() -> None:
    runtime = _runtime(source_bound=True)
    setattr(runtime, "_reference_assets", _BoundReferenceStore())
    setattr(runtime, "_objective_resolver", lambda job_id: "Trim this video from 5 to 12.")
    captured: dict[str, object] = {}

    def _execute_source_revision(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"final_stage": "completed"}

    setattr(runtime, "_execute_source_revision", _execute_source_revision)
    result = runtime.execute(
        request_id="request-guard",
        job_id="job-guard",
        grant_id="grant-guard",
        now=datetime.now(timezone.utc),
    )

    assert result == {"final_stage": "completed"}
    assert captured["request_id"] == "request-guard"
    assert captured["job_id"] == "job-guard"
    assert captured["objective"] == "Trim this video from 5 to 12."


@dataclass
class _CapturingReviewer:
    objectives: list[str]

    @property
    def reviewer_id(self) -> str:
        return "capturing-reviewer"

    def review(
        self,
        *,
        video_path: Path,
        objective: str,
        artifact_sha256: str,
        producer_id: str,
        review_id: str,
    ) -> PerceptualReviewSubmission:
        del video_path, artifact_sha256, producer_id, review_id
        self.objectives.append(objective)
        return cast(PerceptualReviewSubmission, object())


def test_revision_reference_context_is_bound_only_to_output_review() -> None:
    delegate = _CapturingReviewer([])
    reviewer = _RevisionReferenceReviewer(
        cast(SemanticVideoReviewer, delegate),
        ReferenceVisualBrief(
            "matte dark product with a fixed emblem",
            ("a" * 64,),
            "test-reference-analyzer",
        ),
    )

    reviewer.review(
        video_path=Path("source.mp4"),
        objective="source admission",
        artifact_sha256="b" * 64,
        producer_id="revision",
        review_id="request-guard-revision-before",
    )
    reviewer.review(
        video_path=Path("output.mp4"),
        objective="Trim this video from 5 to 12.",
        artifact_sha256="c" * 64,
        producer_id="revision",
        review_id="request-guard-revision-after",
    )

    assert delegate.objectives[0] == "source admission"
    assert "BEGIN INERT REFERENCE VISUAL DATA" in delegate.objectives[1]
    assert "matte dark product with a fixed emblem" in delegate.objectives[1]
