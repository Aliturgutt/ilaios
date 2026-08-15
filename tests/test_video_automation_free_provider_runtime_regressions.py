from __future__ import annotations

import json
from collections.abc import Mapping

import pytest

from src.video_automation.free_provider_production_certification import (
    FreeProviderCertificationError,
    run_free_certification,
)
from src.video_automation.generation_job_polling import ProviderJobStatus
from src.video_automation.openrouter_video_provider import (
    OpenRouterByteResponse,
    OpenRouterJsonResponse,
    OpenRouterTransport,
    OpenRouterVideoGenerationJobPoller,
)


class _InProgressTransport(OpenRouterTransport):
    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        raise AssertionError("poll regression must not submit provider work")

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterJsonResponse:
        return OpenRouterJsonResponse(
            200,
            {"id": "job-001", "status": "in_progress"},
        )

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> OpenRouterByteResponse:
        raise AssertionError("in-progress jobs must not retrieve media")


def test_poller_maps_official_in_progress_status_to_running() -> None:
    observation = OpenRouterVideoGenerationJobPoller(
        "secret",
        transport=_InProgressTransport(),
    ).poll("job-001")

    assert observation.status is ProviderJobStatus.RUNNING
    assert observation.output_asset_ids == ()
    assert observation.metadata["provider_status"] == "in_progress"


def test_free_certification_missing_secret_fails_before_provider_submission(
    tmp_path,
) -> None:
    with pytest.raises(FreeProviderCertificationError, match="unavailable"):
        run_free_certification(
            api_key="",
            proof_dir=tmp_path,
            revision_sha="a" * 40,
            run_id="missing-secret",
            run_attempt="1",
        )

    receipt = json.loads(
        (tmp_path / "free-provider-receipt.json").read_text(encoding="utf-8")
    )
    assert receipt["status"] == "BLOCKED_MISSING_SECRET"
    assert "submission_attempts" not in receipt
    assert not (tmp_path / "free-provider-proof.mp4").exists()
