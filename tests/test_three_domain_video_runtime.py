from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pytest

from services.integrations.three_domain_video_runtime import _FinalDomainReviewConfig
from services.integrations.video_runtime import VideoRuntimeError
from src.video_automation.perceptual_review import (
    PerceptualReviewerKind,
    PerceptualReviewSubmission,
)
from src.video_automation.video_skills import QaDomain


@dataclass
class _Reviewer:
    domain: QaDomain
    score: float = 0.95
    artifact_override: str | None = None

    @property
    def reviewer_id(self) -> str:
        return f"independent-{self.domain.value}-reviewer"

    def review(
        self,
        *,
        video_path: Path,
        objective: str,
        artifact_sha256: str,
        producer_id: str,
        review_id: str,
    ) -> PerceptualReviewSubmission:
        assert video_path.name == "final.mp4"
        assert objective == "NASA documentary"
        return PerceptualReviewSubmission(
            review_id=review_id,
            domain=self.domain,
            artifact_sha256=self.artifact_override or artifact_sha256,
            reviewer_id=self.reviewer_id,
            producer_id=producer_id,
            reviewer_kind=PerceptualReviewerKind.INDEPENDENT_MODEL,
            criteria_id=f"criteria-{self.domain.value}",
            criteria_version="1.0.0",
            criteria_sha256=sha256(self.domain.value.encode()).hexdigest(),
            score=self.score,
            threshold=0.90,
            evidence_references=(f"evidence:{artifact_sha256}:{self.domain.value}",),
            provenance_reference=f"review:{self.domain.value}",
            repair_target=None if self.score >= 0.90 else f"repair-{self.domain.value}",
        )


def _outcome(tmp_path: Path) -> tuple[dict[str, object], str]:
    final_path = tmp_path / "final.mp4"
    final_path.write_bytes(b"exact-final-video")
    digest = sha256(final_path.read_bytes()).hexdigest()
    return {"final_path": str(final_path), "artifact_sha256": digest}, digest


def test_final_audio_brand_reviews_are_bound_to_exact_final_artifact(tmp_path: Path) -> None:
    config = _FinalDomainReviewConfig()
    config.configure_final_perceptual_reviewers(
        audio_reviewer=_Reviewer(QaDomain.AUDIO),
        brand_reviewer=_Reviewer(QaDomain.BRAND),
    )
    outcome, digest = _outcome(tmp_path)

    result = config._apply_final_domain_reviews(
        outcome=outcome,
        objective="NASA documentary",
        request_id="request-001",
    )

    assert result["final_perceptual_domains"] == ("visual", "audio", "brand")
    assert result["final_perceptual_artifact_sha256"] == digest
    assert result["audio_perceptual_score"] == pytest.approx(0.95)
    assert result["brand_perceptual_score"] == pytest.approx(0.95)


def test_final_audio_brand_reviews_fail_closed_on_failed_domain(tmp_path: Path) -> None:
    config = _FinalDomainReviewConfig()
    config.configure_final_perceptual_reviewers(
        audio_reviewer=_Reviewer(QaDomain.AUDIO, score=0.50),
        brand_reviewer=_Reviewer(QaDomain.BRAND),
    )
    outcome, _ = _outcome(tmp_path)

    with pytest.raises(VideoRuntimeError, match="AUDIO/BRAND"):
        config._apply_final_domain_reviews(
            outcome=outcome,
            objective="NASA documentary",
            request_id="request-002",
        )


def test_final_audio_brand_reviews_reject_wrong_domain(tmp_path: Path) -> None:
    config = _FinalDomainReviewConfig()
    config.configure_final_perceptual_reviewers(
        audio_reviewer=_Reviewer(QaDomain.VISUAL),
        brand_reviewer=_Reviewer(QaDomain.BRAND),
    )
    outcome, _ = _outcome(tmp_path)

    with pytest.raises(VideoRuntimeError, match="audio domain"):
        config._apply_final_domain_reviews(
            outcome=outcome,
            objective="NASA documentary",
            request_id="request-003",
        )


def test_final_audio_brand_reviews_reject_artifact_mismatch(tmp_path: Path) -> None:
    config = _FinalDomainReviewConfig()
    config.configure_final_perceptual_reviewers(
        audio_reviewer=_Reviewer(QaDomain.AUDIO, artifact_override="a" * 64),
        brand_reviewer=_Reviewer(QaDomain.BRAND),
    )
    outcome, _ = _outcome(tmp_path)

    with pytest.raises(ValueError, match="artifact identity"):
        config._apply_final_domain_reviews(
            outcome=outcome,
            objective="NASA documentary",
            request_id="request-004",
        )
