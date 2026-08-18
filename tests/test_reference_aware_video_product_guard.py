from __future__ import annotations

from pathlib import Path

import pytest

from services.integrations.reference_aware_provider_video_runtime import (
    ReferenceAwareProviderBackedDesktopVideoRuntime,
)
from services.integrations.video_runtime import VideoRuntimeError


class _EmptyReferenceStore:
    def for_request(self, request_id: str) -> tuple[object, ...]:
        assert request_id == "request-guard"
        return ()


def _runtime() -> ReferenceAwareProviderBackedDesktopVideoRuntime:
    runtime = object.__new__(ReferenceAwareProviderBackedDesktopVideoRuntime)
    setattr(runtime, "_reference_assets", _EmptyReferenceStore())
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
