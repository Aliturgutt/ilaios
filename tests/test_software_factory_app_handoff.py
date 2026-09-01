"""SF-9 typed Software Factory to App Factory handoff proofs."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from services.agent_governance import AgentAdmissionEvidence
from services.app_factory import AppFactory, AppFactoryError
from services.control_plane.proposals import (
    BudgetEnvelope,
    DataClass,
    GoalSpec,
    RiskClass,
)
from services.integrations.software_app_handoff import (
    AppFactoryHandoffError,
    AppFactoryHandoffRequest,
    SoftwareToAppFactoryHandoff,
)
from services.software_factory import EvidenceBundle, PromotionProposal, ValidationResult
from services.software_factory_agents import EngineeringAgentExecution
from services.software_factory_skills import SkillExecutionResult

NOW = datetime(2026, 8, 14, tzinfo=timezone.utc)
BACKEND_ID = "ilaios.agent.engineering.backend.v1"
VERIFIER_ID = "ilaios.agent.meta.independent-verifier.v1"
REPOSITORY_SHA = "a" * 40


def _goal() -> GoalSpec:
    return GoalSpec(
        "Prepare a governed application change for App Factory review.",
        (
            "Software Factory evidence remains linked",
            "App Factory receives no inherited mutation authority",
        ),
        RiskClass.HIGH,
        DataClass.INTERNAL,
        BudgetEnvelope(3, 600),
    )


def _proposal(
    *,
    passed: bool = True,
    requires_human_approval: bool = True,
    production_applied: bool = False,
) -> PromotionProposal:
    validation = ValidationResult(
        passed,
        ("pytest", "ruff", "mypy"),
        () if passed else ("validation failed",),
    )
    evidence = EvidenceBundle(
        "evidence-sf9",
        REPOSITORY_SHA,
        "b" * 64,
        "c" * 64,
        validation,
        "2026-08-14T06:30:00+00:00",
    )
    return PromotionProposal(
        "proposal-sf9",
        "job-sf9",
        evidence,
        requires_human_approval,
        production_applied,
    )


def _execution(
    *,
    status: str = "REVIEW_REQUIRED",
    evidence_digest: str = "d" * 64,
) -> EngineeringAgentExecution:
    admission = AgentAdmissionEvidence(
        "invoke-sf9",
        BACKEND_ID,
        VERIFIER_ID,
        NOW,
        True,
        False,
    )
    result = SkillExecutionResult(
        "sf-backend-engineering",
        "1.0.0",
        "READY",
        {"repository_sha": REPOSITORY_SHA},
        None,
        ("repository_base_sha", "validation_results", "reviewer"),
        True,
    )
    return EngineeringAgentExecution(admission, (result,), status, evidence_digest)


def _request(
    *,
    handoff_id: str = "desktop-feature-1",
    proposal: PromotionProposal | None = None,
    execution: EngineeringAgentExecution | None = None,
    platform: str = "windows",
    action: str = "client_change_request",
) -> AppFactoryHandoffRequest:
    return AppFactoryHandoffRequest(
        handoff_id=handoff_id,
        goal=_goal(),
        software_proposal=proposal or _proposal(),
        engineering_execution=execution or _execution(),
        platform=platform,
        action=action,
    )


def test_sf9_creates_typed_review_only_handoff_without_authority_propagation() -> None:
    app_factory = AppFactory()
    handoff = SoftwareToAppFactoryHandoff(app_factory)

    artifact = handoff.create(_request())

    assert artifact.source_capability == "ilaios.capability.software-factory"
    assert artifact.target_capability == "ilaios.capability.app-factory"
    assert artifact.repository_sha == REPOSITORY_SHA
    assert artifact.engineering_agent_id == BACKEND_ID
    assert artifact.engineering_verifier_id == VERIFIER_ID
    assert artifact.source_review_required is True
    assert artifact.app_approved_for_review is False
    assert artifact.authority_propagated is False
    assert artifact.client_mutated is False
    assert len(artifact.goal_sha256) == 64
    assert len(artifact.artifact_sha256) == 64

    with pytest.raises(AppFactoryError, match="only approved app requests"):
        app_factory.review_projection(artifact.app_request_id)

    app_factory.approve_for_review(artifact.app_request_id, approver="human-owner")
    projection = app_factory.review_projection(artifact.app_request_id)
    assert projection["approved_for_review"] is True
    assert projection["client_mutated"] is False


def test_sf9_handoff_is_deterministic_for_identical_source_evidence() -> None:
    first = SoftwareToAppFactoryHandoff(AppFactory()).create(_request())
    second = SoftwareToAppFactoryHandoff(AppFactory()).create(_request())

    assert first.goal_sha256 == second.goal_sha256
    assert first.app_request_sha256 == second.app_request_sha256
    assert first.artifact_sha256 == second.artifact_sha256


def test_sf9_rejects_unvalidated_or_production_applied_software_output() -> None:
    first = SoftwareToAppFactoryHandoff(AppFactory())
    with pytest.raises(AppFactoryHandoffError, match="validation must pass"):
        first.create(_request(proposal=_proposal(passed=False)))

    second = SoftwareToAppFactoryHandoff(AppFactory())
    with pytest.raises(AppFactoryHandoffError, match="production-applied"):
        second.create(_request(proposal=_proposal(production_applied=True)))

    third = SoftwareToAppFactoryHandoff(AppFactory())
    with pytest.raises(AppFactoryHandoffError, match="human approval requirement"):
        third.create(_request(proposal=_proposal(requires_human_approval=False)))


def test_sf9_rejects_non_engineering_self_verified_or_malformed_execution() -> None:
    base = _execution()
    non_engineering = replace(
        base,
        admission=replace(
            base.admission,
            agent_id="ilaios.agent.security.codesec.v1",
        ),
    )
    with pytest.raises(AppFactoryHandoffError, match="engineering-agent"):
        SoftwareToAppFactoryHandoff(AppFactory()).create(
            _request(execution=non_engineering)
        )

    self_verified = replace(
        base,
        admission=replace(base.admission, verifier_id=BACKEND_ID),
    )
    with pytest.raises(AppFactoryHandoffError, match="cannot independently verify"):
        SoftwareToAppFactoryHandoff(AppFactory()).create(
            _request(execution=self_verified)
        )

    malformed = replace(base, evidence_digest="not-a-sha256")
    with pytest.raises(AppFactoryHandoffError, match="digest is invalid"):
        SoftwareToAppFactoryHandoff(AppFactory()).create(_request(execution=malformed))


def test_sf9_rejects_duplicate_handoff_and_unsafe_target_requests() -> None:
    handoff = SoftwareToAppFactoryHandoff(AppFactory())
    handoff.create(_request())
    with pytest.raises(AppFactoryHandoffError, match="handoff_id already exists"):
        handoff.create(_request())

    with pytest.raises(AppFactoryHandoffError, match="bounded canonical identifier"):
        SoftwareToAppFactoryHandoff(AppFactory()).create(
            _request(handoff_id="../escape")
        )

    with pytest.raises(AppFactoryError, match="unsupported app platform"):
        SoftwareToAppFactoryHandoff(AppFactory()).create(
            _request(platform="linux")
        )

    with pytest.raises(AppFactoryError, match="unsupported app factory action"):
        SoftwareToAppFactoryHandoff(AppFactory()).create(
            _request(action="deploy")
        )


def test_sf9_preserves_sf7_step_readiness_and_source_review_state() -> None:
    base = _execution(status="READY")
    not_ready_step = replace(base.skill_results[0], status="BLOCKED")
    blocked = replace(base, skill_results=(not_ready_step,))
    with pytest.raises(AppFactoryHandoffError, match="skill steps must be READY"):
        SoftwareToAppFactoryHandoff(AppFactory()).create(_request(execution=blocked))

    invalid_state = replace(base, status="FAILED")
    with pytest.raises(AppFactoryHandoffError, match="not handoff-eligible"):
        SoftwareToAppFactoryHandoff(AppFactory()).create(
            _request(execution=invalid_state)
        )
