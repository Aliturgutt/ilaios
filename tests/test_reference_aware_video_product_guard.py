from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from services.integrations.reference_aware_provider_video_runtime import (
    ReferenceAwareProviderBackedDesktopVideoRuntime,
)
from services.integrations.video_runtime import VideoRuntimeError


class _EmptyReferenceStore:
    def for_request(self, request_id: str) -> tuple[object, ...]:
        assert request_id == "request-guard"
        return ()


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


def test_vertical_request_is_rejected_before_reference_analysis_or_provider_generation(
    tmp_path: Path,
) -> None:
    runtime = _runtime()
    with pytest.raises(VideoRuntimeError, match="9:16"):
        runtime._generate_finished_product(
            run_root=tmp_path,
            request_id="request-guard",
            job_id="job-guard",
            objective="Create a vertical video for TikTok.",
            duration_seconds=20.0,
        )


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
