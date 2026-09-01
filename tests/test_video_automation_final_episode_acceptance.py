from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from src.video_automation.assembled_output_technical_validation import (
    AssembledOutputTechnicalIssue,
    AssembledOutputTechnicalValidation,
    AssembledOutputTechnicalValidationStatus,
)
from src.video_automation.episode_assembly_execution import EpisodeAssemblyArtifact
from src.video_automation.final_episode_acceptance import (
    FinalEpisodeAcceptanceCoordinator,
    FinalEpisodeAcceptanceError,
    FinalEpisodeAcceptancePolicy,
    FinalEpisodeAcceptanceStatus,
    FinalEpisodeQualityCheck,
)
from src.video_automation.media_technical_validation import MediaProbeObservation


def _artifact(path: Path, body: bytes = b"final-episode") -> EpisodeAssemblyArtifact:
    path.write_bytes(body)
    return EpisodeAssemblyArtifact(
        artifact_id="episode-assembly-artifact-001",
        request_id="episode-assembly-request-001",
        episode_id="episode-001",
        executor_id="fake-executor-v1",
        output_path=str(path),
        sha256_hex=sha256(body).hexdigest(),
        byte_length=len(body),
        container_format="mp4",
        video_codec="h264",
        audio_codec="aac",
        width=1080,
        height=1920,
        frame_rate=24,
        source_asset_ids=("asset-1", "asset-2"),
        metadata={},
    )


def _technical_validation(
    artifact: EpisodeAssemblyArtifact,
    *,
    status: AssembledOutputTechnicalValidationStatus = (
        AssembledOutputTechnicalValidationStatus.PASSED
    ),
    duration_seconds: float = 40.0,
    audio_stream_count: int = 1,
) -> AssembledOutputTechnicalValidation:
    issues = (
        ()
        if status is AssembledOutputTechnicalValidationStatus.PASSED
        else (
            AssembledOutputTechnicalIssue(
                "technical_issue",
                "technical validation failed",
            ),
        )
    )
    return AssembledOutputTechnicalValidation(
        validation_id="assembled-output-validation-001",
        artifact_id=artifact.artifact_id,
        request_id=artifact.request_id,
        episode_id=artifact.episode_id,
        output_path=artifact.output_path,
        sha256_hex=artifact.sha256_hex,
        byte_length=artifact.byte_length,
        status=status,
        observation=MediaProbeObservation(
            container="mp4",
            duration_seconds=duration_seconds,
            width=1080,
            height=1920,
            frames_per_second=24.0,
            video_codec="h264",
            audio_codec="aac" if audio_stream_count else None,
            video_stream_count=1,
            audio_stream_count=audio_stream_count,
        ),
        issues=issues,
        probe_id="fake-probe-v1",
        metadata={},
    )


def _policy() -> FinalEpisodeAcceptancePolicy:
    return FinalEpisodeAcceptancePolicy(
        required_quality_checks=(
            "visual_continuity",
            "audio_quality",
            "content_safety",
        ),
        min_duration_seconds=38.0,
        max_duration_seconds=42.0,
        require_audio_stream=True,
        min_source_asset_count=2,
    )


def _checks() -> tuple[FinalEpisodeQualityCheck, ...]:
    return (
        FinalEpisodeQualityCheck(
            "visual_continuity", True, "evidence-visual", "visual continuity passed"
        ),
        FinalEpisodeQualityCheck(
            "audio_quality", True, "evidence-audio", "audio quality passed"
        ),
        FinalEpisodeQualityCheck(
            "content_safety", True, "evidence-safety", "content safety passed"
        ),
    )


def test_accepts_when_all_required_evidence_passes(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    decision = FinalEpisodeAcceptanceCoordinator(_policy()).evaluate(
        artifact,
        _technical_validation(artifact),
        _checks(),
    )
    assert decision.status is FinalEpisodeAcceptanceStatus.ACCEPTED
    assert decision.issues == ()


def test_decision_is_deterministic(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    coordinator = FinalEpisodeAcceptanceCoordinator(_policy())
    first = coordinator.evaluate(artifact, _technical_validation(artifact), _checks())
    second = coordinator.evaluate(artifact, _technical_validation(artifact), _checks())
    assert first.decision_id == second.decision_id
    assert first.policy_id == second.policy_id


def test_failed_technical_validation_rejects(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    decision = FinalEpisodeAcceptanceCoordinator(_policy()).evaluate(
        artifact,
        _technical_validation(
            artifact,
            status=AssembledOutputTechnicalValidationStatus.FAILED,
        ),
        _checks(),
    )
    assert decision.status is FinalEpisodeAcceptanceStatus.REJECTED
    assert "technical_validation_failed" in {
        issue.code for issue in decision.issues
    }


def test_missing_required_quality_check_rejects(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    checks = _checks()[:-1]
    decision = FinalEpisodeAcceptanceCoordinator(_policy()).evaluate(
        artifact,
        _technical_validation(artifact),
        checks,
    )
    assert "quality_check_missing:visual_continuity" not in {
        issue.code for issue in decision.issues
    }
    assert "quality_check_missing:content_safety" in {
        issue.code for issue in decision.issues
    }


def test_failed_required_quality_check_rejects(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    checks = (
        FinalEpisodeQualityCheck(
            "visual_continuity", False, "evidence-visual", "continuity failed"
        ),
        *_checks()[1:],
    )
    decision = FinalEpisodeAcceptanceCoordinator(_policy()).evaluate(
        artifact,
        _technical_validation(artifact),
        checks,
    )
    assert "quality_check_failed:visual_continuity" in {
        issue.code for issue in decision.issues
    }


def test_duration_below_minimum_rejects(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    decision = FinalEpisodeAcceptanceCoordinator(_policy()).evaluate(
        artifact,
        _technical_validation(artifact, duration_seconds=37.9),
        _checks(),
    )
    assert "duration_below_minimum" in {issue.code for issue in decision.issues}


def test_duration_above_maximum_rejects(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    decision = FinalEpisodeAcceptanceCoordinator(_policy()).evaluate(
        artifact,
        _technical_validation(artifact, duration_seconds=42.1),
        _checks(),
    )
    assert "duration_above_maximum" in {issue.code for issue in decision.issues}


def test_missing_audio_rejects_when_required(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    decision = FinalEpisodeAcceptanceCoordinator(_policy()).evaluate(
        artifact,
        _technical_validation(artifact, audio_stream_count=0),
        _checks(),
    )
    assert "audio_stream_required" in {issue.code for issue in decision.issues}


def test_source_asset_count_requirement_is_enforced(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    object.__setattr__(artifact, "source_asset_ids", ("asset-1",))
    decision = FinalEpisodeAcceptanceCoordinator(_policy()).evaluate(
        artifact,
        _technical_validation(artifact),
        _checks(),
    )
    assert "source_asset_count_below_minimum" in {
        issue.code for issue in decision.issues
    }


def test_artifact_identity_must_match(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    validation = _technical_validation(artifact)
    object.__setattr__(validation, "artifact_id", "artifact-other")
    with pytest.raises(FinalEpisodeAcceptanceError, match="artifact_id"):
        FinalEpisodeAcceptanceCoordinator(_policy()).evaluate(
            artifact, validation, _checks()
        )


def test_artifact_hash_must_match(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    validation = _technical_validation(artifact)
    object.__setattr__(validation, "sha256_hex", "a" * 64)
    with pytest.raises(FinalEpisodeAcceptanceError, match="SHA-256"):
        FinalEpisodeAcceptanceCoordinator(_policy()).evaluate(
            artifact, validation, _checks()
        )


def test_duplicate_quality_checks_are_rejected(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    duplicate = (_checks()[0], _checks()[0])
    with pytest.raises(FinalEpisodeAcceptanceError, match="unique"):
        FinalEpisodeAcceptanceCoordinator(_policy()).evaluate(
            artifact,
            _technical_validation(artifact),
            duplicate,
        )


def test_policy_rejects_duplicate_required_checks() -> None:
    with pytest.raises(FinalEpisodeAcceptanceError, match="unique"):
        FinalEpisodeAcceptancePolicy(
            required_quality_checks=("visual", "visual"),
            min_duration_seconds=38.0,
            max_duration_seconds=42.0,
        )


def test_policy_rejects_invalid_duration_range() -> None:
    with pytest.raises(FinalEpisodeAcceptanceError, match="must not exceed"):
        FinalEpisodeAcceptancePolicy(
            required_quality_checks=("visual",),
            min_duration_seconds=43.0,
            max_duration_seconds=42.0,
        )


def test_quality_check_codes_are_normalized(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    checks = (
        FinalEpisodeQualityCheck(
            "VISUAL_CONTINUITY", True, "evidence-visual", "visual passed"
        ),
        FinalEpisodeQualityCheck(
            "AUDIO_QUALITY", True, "evidence-audio", "audio passed"
        ),
        FinalEpisodeQualityCheck(
            "CONTENT_SAFETY", True, "evidence-safety", "safety passed"
        ),
    )
    decision = FinalEpisodeAcceptanceCoordinator(_policy()).evaluate(
        artifact,
        _technical_validation(artifact),
        checks,
    )
    assert decision.status is FinalEpisodeAcceptanceStatus.ACCEPTED


def test_decision_metadata_is_immutable(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    decision = FinalEpisodeAcceptanceCoordinator(_policy()).evaluate(
        artifact,
        _technical_validation(artifact),
        _checks(),
    )
    with pytest.raises(TypeError):
        decision.metadata["x"] = "y"  # type: ignore[index]


def test_quality_check_code_cannot_contain_whitespace() -> None:
    with pytest.raises(FinalEpisodeAcceptanceError, match="whitespace"):
        FinalEpisodeAcceptancePolicy(
            required_quality_checks=("visual continuity",),
            min_duration_seconds=38.0,
            max_duration_seconds=42.0,
        )
