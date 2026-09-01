from __future__ import annotations

import pytest

from src.media_quality import (
    MediaAcceptanceGate,
    MediaKind,
    MediaQualityDomain,
    MediaQualityError,
    MediaQualityObservation,
    MediaRepairBudget,
    image_required_domains,
    video_required_domains,
)

ARTIFACT = "a" * 64


def _observation(
    domain: MediaQualityDomain,
    *,
    score: float = 0.95,
    threshold: float = 0.8,
    target: str | None = None,
) -> MediaQualityObservation:
    return MediaQualityObservation(
        observation_id=f"obs-{domain.value.lower()}",
        domain=domain,
        artifact_sha256=ARTIFACT,
        producer_id="media-producer",
        observer_id=f"observer-{domain.value.lower()}",
        score=score,
        threshold=threshold,
        evidence_ref=f"evidence://quality/{domain.value.lower()}",
        repair_target=target,
    )


def test_video_acceptance_requires_continuity_with_existing_quality_domains() -> None:
    observations = tuple(_observation(domain) for domain in video_required_domains())

    result = MediaAcceptanceGate().evaluate(
        media_kind=MediaKind.VIDEO,
        artifact_sha256=ARTIFACT,
        observations=observations,
        required_domains=video_required_domains(),
        repair_budget=MediaRepairBudget(max_total_attempts=2, max_attempts_per_target=1),
    )

    assert result.accepted
    assert result.repair_plan == ()
    assert MediaQualityDomain.CONTINUITY in result.required_domains
    assert result.aggregate_score == pytest.approx(0.95)
    assert result.acceptance_id.startswith("media-acceptance-")


def test_failed_domains_produce_only_bounded_selective_repairs() -> None:
    observations = (
        _observation(MediaQualityDomain.VISUAL, score=0.4, target="shot-7"),
        _observation(MediaQualityDomain.AUDIO, score=0.5, target="audio-mix"),
        _observation(MediaQualityDomain.BRAND),
        _observation(MediaQualityDomain.CONTINUITY, score=0.3, target="character-face"),
        _observation(MediaQualityDomain.TECHNICAL),
    )

    result = MediaAcceptanceGate().evaluate(
        media_kind=MediaKind.VIDEO,
        artifact_sha256=ARTIFACT,
        observations=observations,
        required_domains=video_required_domains(),
        repair_budget=MediaRepairBudget(max_total_attempts=2, max_attempts_per_target=1),
    )

    assert not result.accepted
    assert len(result.repair_plan) == 2
    assert {item.target for item in result.repair_plan}.issubset(
        {"shot-7", "audio-mix", "character-face"}
    )


def test_exhausted_target_budget_does_not_schedule_hidden_retry() -> None:
    observations = (
        _observation(MediaQualityDomain.VISUAL, score=0.4, target="shot-7"),
        _observation(MediaQualityDomain.BRAND),
        _observation(MediaQualityDomain.TECHNICAL),
    )

    result = MediaAcceptanceGate().evaluate(
        media_kind=MediaKind.IMAGE,
        artifact_sha256=ARTIFACT,
        observations=observations,
        required_domains=image_required_domains(continuity_required=False),
        repair_budget=MediaRepairBudget(max_total_attempts=1, max_attempts_per_target=1),
        prior_attempts={"shot-7": 1},
    )

    assert not result.accepted
    assert result.repair_plan == ()


def test_series_image_can_require_continuity() -> None:
    domains = image_required_domains(continuity_required=True)
    observations = tuple(_observation(domain) for domain in domains)

    result = MediaAcceptanceGate().evaluate(
        media_kind=MediaKind.IMAGE,
        artifact_sha256=ARTIFACT,
        observations=observations,
        required_domains=domains,
        repair_budget=MediaRepairBudget(max_total_attempts=1, max_attempts_per_target=1),
    )

    assert result.accepted
    assert MediaQualityDomain.CONTINUITY in result.required_domains
    assert MediaQualityDomain.AUDIO not in result.required_domains


def test_artifact_mismatch_is_rejected() -> None:
    observation = MediaQualityObservation(
        observation_id="obs-visual",
        domain=MediaQualityDomain.VISUAL,
        artifact_sha256="b" * 64,
        producer_id="producer",
        observer_id="observer",
        score=1.0,
        threshold=0.8,
        evidence_ref="evidence://visual",
    )

    with pytest.raises(MediaQualityError, match="artifact identity mismatch"):
        MediaAcceptanceGate().evaluate(
            media_kind=MediaKind.IMAGE,
            artifact_sha256=ARTIFACT,
            observations=(
                observation,
                _observation(MediaQualityDomain.BRAND),
                _observation(MediaQualityDomain.TECHNICAL),
            ),
            required_domains=image_required_domains(continuity_required=False),
            repair_budget=MediaRepairBudget(max_total_attempts=1, max_attempts_per_target=1),
        )
