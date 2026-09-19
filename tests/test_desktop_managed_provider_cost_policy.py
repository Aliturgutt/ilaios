from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from services.integrations.managed_provider_video_runtime import ManagedDesktopVideoSession
from services.integrations.provider_video_runtime import (
    ProviderCostEvidence,
    VerifiedFreeProviderCostPolicy,
)
from services.integrations.video_runtime import VideoRuntimeError
from src.video_automation.generation_execution_tracking import (
    GenerationDispatchExecution,
    GenerationExecutionStatus,
)


def _terminal_record(
    index: int,
    *,
    actual_microusd: int,
    ceiling_microusd: int,
    proven: str = "true",
) -> GenerationDispatchExecution:
    return GenerationDispatchExecution(
        dispatch_id=f"dispatch-{index}",
        batch_id=f"batch-{index}",
        batch_number=index,
        status=GenerationExecutionStatus.SUCCEEDED,
        revision=2,
        provider_job_id=f"provider-job-{index}",
        output_asset_ids=(f"https://openrouter.ai/api/v1/videos/provider-job-{index}/content",),
        error_code=None,
        error_message=None,
        metadata={
            "managed_cost_proven": proven,
            "actual_provider_cost_microusd": str(actual_microusd),
            "provider_cost_ceiling_microusd": str(ceiling_microusd),
            "actual_margin_bps": "4000",
            "aggregate_hard_cap_microusd": "1000000",
        },
    )


def _session(tmp_path: Path) -> ManagedDesktopVideoSession:
    return ManagedDesktopVideoSession(
        root=tmp_path / "managed-provider",
        api_key="test-secret",
        model_id="bytedance/seedance-2.0-fast",
        resolution="480p",
        max_total_cost_usd=Decimal("1.00"),
    )


def test_verified_free_policy_still_rejects_paid_model() -> None:
    policy = VerifiedFreeProviderCostPolicy()

    with pytest.raises(VideoRuntimeError, match="explicit free video model"):
        policy.validate_model_id("bytedance/seedance-2.0-fast")

    policy.validate_model_id("bytedance/seedance-2.0-fast:free")


def test_managed_session_rejects_free_alias(tmp_path: Path) -> None:
    session = _session(tmp_path)

    with pytest.raises(VideoRuntimeError, match="explicit non-free model"):
        session.validate_model_id("bytedance/seedance-2.0-fast:free")

    session.validate_model_id("bytedance/seedance-2.0-fast")


def test_managed_cost_evidence_accepts_two_shots_inside_one_dollar_cap(
    tmp_path: Path,
) -> None:
    session = _session(tmp_path)
    evidence = session.verify(
        (
            _terminal_record(1, actual_microusd=215_200, ceiling_microusd=240_000),
            _terminal_record(2, actual_microusd=215_200, ceiling_microusd=240_000),
        )
    )

    assert evidence.mode == "managed-bounded"
    assert evidence.proven is True
    assert evidence.zero is False
    assert evidence.actual_microusd == 430_400
    assert evidence.ceiling_microusd == 1_000_000


def test_managed_cost_evidence_rejects_unproven_terminal_record(
    tmp_path: Path,
) -> None:
    session = _session(tmp_path)

    with pytest.raises(VideoRuntimeError, match="terminal cost is not proven"):
        session.verify(
            (
                _terminal_record(
                    1,
                    actual_microusd=215_200,
                    ceiling_microusd=240_000,
                    proven="false",
                ),
            )
        )


def test_managed_cost_evidence_rejects_dispatch_ceiling_violation(
    tmp_path: Path,
) -> None:
    session = _session(tmp_path)

    with pytest.raises(VideoRuntimeError, match="exceeded dispatch ceiling"):
        session.verify(
            (
                _terminal_record(
                    1,
                    actual_microusd=250_001,
                    ceiling_microusd=250_000,
                ),
            )
        )


def test_managed_cost_evidence_rejects_aggregate_reserved_ceiling_over_one_dollar(
    tmp_path: Path,
) -> None:
    session = _session(tmp_path)

    with pytest.raises(VideoRuntimeError, match="reserved ceilings exceeded aggregate hard cap"):
        session.verify(
            (
                _terminal_record(1, actual_microusd=100_000, ceiling_microusd=600_000),
                _terminal_record(2, actual_microusd=100_000, ceiling_microusd=600_000),
            )
        )


def test_provider_cost_evidence_rejects_inconsistent_zero_claim() -> None:
    with pytest.raises(VideoRuntimeError, match="zero-cost evidence is inconsistent"):
        ProviderCostEvidence(
            mode="managed-bounded",
            proven=True,
            zero=True,
            actual_microusd=1,
            ceiling_microusd=1_000_000,
        )


def test_managed_desktop_workflow_is_manual_and_exactly_one_dollar_capped() -> None:
    workflow = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "video-provider-production-certification.yml"
    ).read_text(encoding="utf-8")

    assert "  workflow_dispatch:" in workflow
    assert "  push:" not in workflow
    assert "  pull_request:" not in workflow
    assert "          - desktop-managed-bounded" in workflow
    assert 'ILAIOS_VIDEO_MANAGED_E2E_MAX_TOTAL_USD: "1.00"' in workflow
    assert "provider_video_managed_finished_product_e2e.py" in workflow
    assert "desktop-managed-provider-video-proof-${{ github.sha }}-${{ github.run_id }}" in workflow
