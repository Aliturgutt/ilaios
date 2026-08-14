from __future__ import annotations

from dataclasses import replace
from hashlib import sha256

import pytest

from services.integrations.video_creative_direction import GovernedCinematographyExecutor
from services.integrations.video_quality import (
    GovernedVideoQaExecutor,
    acceptance_quality_checks,
)
from services.integrations.video_skill_governance import approve_video_skills
from services.runtime.routing import AgentProfile, RuntimeError, SkillRegistry
from src.video_automation.models import Shot
from src.video_automation.video_quality import (
    QaObservationSource,
    VideoQaObservation,
    VideoQaStatus,
    VideoQualityError,
    VideoQualityFoundation,
)
from src.video_automation.video_skills import CreativeDirection, QaDomain, VideoSkillError

ARTIFACT = sha256(b"finished-video").hexdigest()


def _observations(
    failing: QaDomain | None = None,
    *,
    producer_id: str = "video-producer",
) -> tuple[VideoQaObservation, ...]:
    return tuple(
        VideoQaObservation(
            observation_id=f"obs-{domain.value}",
            domain=domain,
            artifact_sha256=ARTIFACT,
            observer_id=f"observer-{domain.value}",
            producer_id=producer_id,
            source=(
                QaObservationSource.DETERMINISTIC_PROBE
                if domain is QaDomain.TECHNICAL
                else QaObservationSource.INDEPENDENT_MODEL
            ),
            score=0.4 if domain is failing else 0.95,
            threshold=0.8,
            evidence_reference=f"evidence:{domain.value}",
            provenance_reference=f"provenance:{domain.value}",
            repair_target=f"scene:{domain.value}" if domain is failing else None,
        )
        for domain in QaDomain
    )


def _registry() -> SkillRegistry:
    registry = SkillRegistry()
    approve_video_skills(registry)
    return registry


def _agent(*, repair: bool = True) -> AgentProfile:
    authorities = {"manifest.read", "media.read"}
    if repair:
        authorities.add("media.write")
    return AgentProfile("video-qa-worker", frozenset(authorities))


def _shot() -> Shot:
    return Shot(
        shot_id="scene-001-shot-001",
        scene_id="scene-001",
        shot_type="cinematic",
        camera_description="subject crosses a graphite corridor",
        subject="subject",
        action="crosses corridor",
        environment="graphite corridor",
        framing="medium shot",
        movement="static",
        estimated_duration_seconds=4.0,
        generation_prompt="subject crosses a graphite corridor",
        required_provider_capability="video.generate",
    )


def _direction() -> CreativeDirection:
    return CreativeDirection(
        direction_id="direction-qa-001",
        visual_intent="controlled cinematic realism",
        shot_scale="wide shot",
        camera_angle="eye-level",
        camera_movement="slow dolly-in",
        lighting="soft directional light",
        palette=("graphite", "cyan"),
        pacing="measured",
        continuity_keys=("subject", "corridor"),
    )


def test_four_layer_chain_uses_one_registry_and_independent_final_evaluator() -> None:
    registry = _registry()
    directed = GovernedCinematographyExecutor(
        registry,
        AgentProfile("video-director", frozenset({"manifest.read"})),
    ).execute((_shot(),), _direction())
    assert directed.direction_id == "direction-qa-001"

    run = GovernedVideoQaExecutor(registry, _agent()).evaluate(
        ARTIFACT,
        _observations(),
        evaluator_id="final-evaluator",
    )
    assert run.status is VideoQaStatus.ACCEPTED
    assert run.evaluation.passed
    assert run.repairs == ()
    assert {item.domain for item in run.evaluation.findings} == set(QaDomain)

    checks = acceptance_quality_checks(run)
    assert {check.check_code for check in checks} == {
        "visual_quality",
        "audio_quality",
        "brand_quality",
        "technical_quality",
    }
    assert all(check.passed for check in checks)


def test_qa_requires_exactly_one_observation_for_every_domain() -> None:
    with pytest.raises(VideoQualityError, match="exactly one visual, audio, brand"):
        VideoQualityFoundation().evaluate(
            ARTIFACT,
            _observations()[:-1],
            evaluator_id="final-evaluator",
        )


def test_qa_rejects_artifact_substitution() -> None:
    observations = list(_observations())
    observations[0] = replace(observations[0], artifact_sha256="b" * 64)
    with pytest.raises(VideoQualityError, match="artifact identity"):
        VideoQualityFoundation().evaluate(
            ARTIFACT,
            observations,
            evaluator_id="final-evaluator",
        )


def test_observer_cannot_self_certify_produced_artifact() -> None:
    with pytest.raises(VideoQualityError, match="independent from artifact producer"):
        VideoQaObservation(
            observation_id="self-certification",
            domain=QaDomain.VISUAL,
            artifact_sha256=ARTIFACT,
            observer_id="same-service",
            producer_id="same-service",
            source=QaObservationSource.INDEPENDENT_MODEL,
            score=0.9,
            threshold=0.8,
            evidence_reference="evidence:visual",
            provenance_reference="provenance:visual",
        )


def test_final_evaluator_cannot_generate_the_observations_it_aggregates() -> None:
    with pytest.raises(VideoQualityError, match="externally produced observations"):
        VideoQualityFoundation().evaluate(
            ARTIFACT,
            _observations(),
            evaluator_id="observer-visual",
        )


def test_final_evaluator_cannot_certify_its_own_produced_artifact() -> None:
    with pytest.raises(VideoQualityError, match="own produced artifact"):
        VideoQualityFoundation().evaluate(
            ARTIFACT,
            _observations(producer_id="final-evaluator"),
            evaluator_id="final-evaluator",
        )


def test_failed_observation_requires_bounded_repair_target() -> None:
    with pytest.raises(VideoQualityError, match="repair target"):
        VideoQaObservation(
            observation_id="failed-visual",
            domain=QaDomain.VISUAL,
            artifact_sha256=ARTIFACT,
            observer_id="visual-observer",
            producer_id="video-producer",
            source=QaObservationSource.INDEPENDENT_MODEL,
            score=0.2,
            threshold=0.8,
            evidence_reference="evidence:visual",
            provenance_reference="provenance:visual",
        )


def test_failed_qa_requires_repair_skill_authority() -> None:
    executor = GovernedVideoQaExecutor(_registry(), _agent(repair=False))
    with pytest.raises(RuntimeError, match="expand agent authority"):
        executor.evaluate(
            ARTIFACT,
            _observations(QaDomain.AUDIO),
            evaluator_id="final-evaluator",
        )


def test_failed_qa_plans_only_failed_domain_and_enforces_attempt_limit() -> None:
    foundation = VideoQualityFoundation(max_repair_attempts=1)
    run = foundation.evaluate(
        ARTIFACT,
        _observations(QaDomain.BRAND),
        evaluator_id="final-evaluator",
    )
    assert run.status is VideoQaStatus.REPAIR_REQUIRED
    assert [(repair.target, repair.attempt) for repair in run.repairs] == [
        ("scene:brand", 1)
    ]
    finding_id = run.repairs[0].finding_id
    with pytest.raises(VideoSkillError, match="repair limit exhausted"):
        foundation.evaluate(
            ARTIFACT,
            _observations(QaDomain.BRAND),
            evaluator_id="final-evaluator",
            prior_attempts={finding_id: 1},
        )


def test_repair_history_rejects_unknown_finding_identity() -> None:
    with pytest.raises(VideoQualityError, match="unknown findings"):
        VideoQualityFoundation().evaluate(
            ARTIFACT,
            _observations(QaDomain.VISUAL),
            evaluator_id="final-evaluator",
            prior_attempts={"finding:forged": 1},
        )


def test_provenance_must_be_explicit_and_trimmed() -> None:
    with pytest.raises(VideoQualityError, match="provenance_reference"):
        VideoQaObservation(
            observation_id="bad-provenance",
            domain=QaDomain.BRAND,
            artifact_sha256=ARTIFACT,
            observer_id="brand-observer",
            producer_id="video-producer",
            source=QaObservationSource.HUMAN_REVIEW,
            score=0.9,
            threshold=0.8,
            evidence_reference="evidence:brand",
            provenance_reference=" ",
        )


def test_qa_run_identity_is_order_independent() -> None:
    foundation = VideoQualityFoundation()
    observations = _observations()
    first = foundation.evaluate(
        ARTIFACT,
        observations,
        evaluator_id="final-evaluator",
    )
    second = foundation.evaluate(
        ARTIFACT,
        tuple(reversed(observations)),
        evaluator_id="final-evaluator",
    )
    assert first.run_id == second.run_id
    assert first.observations == second.observations
