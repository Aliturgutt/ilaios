"""SF-10 governed specialized-factory integration proofs."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.agent_governance import AgentAdmissionEvidence
from services.commerce_growth_factory import CommerceGrowthError, CommerceGrowthFactory
from services.control_plane.proposals import (
    BudgetEnvelope,
    DataClass,
    GoalSpec,
    RiskClass,
)
from services.creative_document_factory import CreativeDocumentError, CreativeDocumentFactory
from services.integrations.software_specialized_handoff import (
    COMMERCE_GROWTH_CAPABILITY,
    CREATIVE_DOCUMENT_CAPABILITY,
    PERSONAL_OPERATIONS_CAPABILITY,
    RESEARCH_DATA_CAPABILITY,
    SECURITY_CAPABILITY,
    SPECIALIZED_TARGETS,
    CommerceGrowthPayload,
    CreativeDocumentPayload,
    FactorySourceInput,
    PersonalOperationsPayload,
    ResearchDataPayload,
    SecurityPayload,
    SoftwareToSpecializedFactoryHandoff,
    SpecializedFactoryHandoffError,
    SpecializedFactoryHandoffRequest,
)
from services.personal_operations_factory import PersonalOperationsError, PersonalOperationsFactory
from services.research_data_factory import ResearchDataError, ResearchDataFactory
from services.security_factory import SecurityFactory
from services.software_factory import EvidenceBundle, PromotionProposal, ValidationResult
from services.software_factory_agents import EngineeringAgentExecution
from services.software_factory_skills import SkillExecutionResult

NOW = datetime(2026, 8, 14, tzinfo=timezone.utc)
BACKEND_ID = "ilaios.agent.engineering.backend.v1"
VERIFIER_ID = "ilaios.agent.meta.independent-verifier.v1"
REPOSITORY_SHA = "a" * 40


def _goal() -> GoalSpec:
    return GoalSpec(
        "Prepare bounded specialized-factory work from validated software evidence.",
        (
            "Source evidence remains linked",
            "Target authority does not propagate automatically",
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
        "evidence-sf10",
        REPOSITORY_SHA,
        "b" * 64,
        "c" * 64,
        validation,
        "2026-08-14T06:50:00+00:00",
    )
    return PromotionProposal(
        "proposal-sf10",
        "job-sf10",
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
        "invoke-sf10",
        BACKEND_ID,
        VERIFIER_ID,
        NOW,
        True,
        False,
    )
    result = SkillExecutionResult(
        "sf-integration-engineering",
        "1.0.0",
        "READY",
        {"repository_sha": REPOSITORY_SHA},
        None,
        ("repository_base_sha", "validation_results", "reviewer"),
        True,
    )
    return EngineeringAgentExecution(admission, (result,), status, evidence_digest)


def _source(source_id: str = "source-1") -> FactorySourceInput:
    return FactorySourceInput(
        source_id,
        f"evidence://{source_id}",
        f"validated material for {source_id}".encode(),
        True,
    )


def _factories() -> tuple[
    SoftwareToSpecializedFactoryHandoff,
    ResearchDataFactory,
    SecurityFactory,
    CreativeDocumentFactory,
    CommerceGrowthFactory,
    PersonalOperationsFactory,
]:
    research = ResearchDataFactory()
    security = SecurityFactory()
    creative = CreativeDocumentFactory()
    commerce = CommerceGrowthFactory()
    personal = PersonalOperationsFactory()
    return (
        SoftwareToSpecializedFactoryHandoff(
            research,
            security,
            creative,
            commerce,
            personal,
        ),
        research,
        security,
        creative,
        commerce,
        personal,
    )


def _request(
    target_capability: str,
    payload: (
        ResearchDataPayload
        | SecurityPayload
        | CreativeDocumentPayload
        | CommerceGrowthPayload
        | PersonalOperationsPayload
    ),
    *,
    handoff_id: str = "specialized-1",
    proposal: PromotionProposal | None = None,
    execution: EngineeringAgentExecution | None = None,
) -> SpecializedFactoryHandoffRequest:
    return SpecializedFactoryHandoffRequest(
        handoff_id=handoff_id,
        goal=_goal(),
        software_proposal=proposal or _proposal(),
        engineering_execution=execution or _execution(),
        target_capability=target_capability,
        payload=payload,
    )


def test_sf10_target_set_is_exact_canonical_specialized_family() -> None:
    assert SPECIALIZED_TARGETS == frozenset(
        {
            "ilaios.capability.research-data",
            "ilaios.capability.security-factory",
            "ilaios.capability.creative-document",
            "ilaios.capability.commerce-growth",
            "ilaios.capability.personal-operations",
        }
    )


def test_research_handoff_preserves_unverified_claim_boundary() -> None:
    handoff, research, _, _, _, _ = _factories()
    payload = ResearchDataPayload(
        "claim-1",
        "Validated software evidence requires specialized research review.",
        (_source(),),
    )

    artifact = handoff.create(_request(RESEARCH_DATA_CAPABILITY, payload))

    assert artifact.target_object_id == "claim-1"
    assert artifact.target_status == "REVIEW_REQUIRED"
    assert artifact.target_approved is False
    assert artifact.independent_verification_completed is False
    assert artifact.authority_propagated is False
    assert artifact.external_applied is False
    assert len(artifact.target_output_sha256) == 64
    assert len(artifact.artifact_sha256) == 64
    with pytest.raises(ResearchDataError, match="only verified claims"):
        research.knowledge_projection("claim-1")


def test_security_handoff_scans_bounded_scope_without_self_verification(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "service.py").write_text("value = 1\n", encoding="utf-8")
    handoff, _, _, _, _, _ = _factories()

    artifact = handoff.create(
        _request(
            SECURITY_CAPABILITY,
            SecurityPayload("scope-1", repository),
        )
    )

    assert artifact.target_object_id == "scope-1"
    assert artifact.target_status == "REVIEW_REQUIRED"
    assert artifact.independent_verification_completed is False
    assert artifact.authority_propagated is False


def test_security_handoff_blocks_on_high_severity_finding(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "unsafe.py").write_text("result = eval(user_input)\n", encoding="utf-8")
    handoff, _, _, _, _, _ = _factories()

    artifact = handoff.create(
        _request(
            SECURITY_CAPABILITY,
            SecurityPayload("scope-blocked", repository),
        )
    )

    assert artifact.target_status == "BLOCKED"
    assert artifact.target_approved is False
    assert artifact.independent_verification_completed is False


def test_creative_handoff_composes_but_does_not_approve() -> None:
    handoff, _, _, creative, _, _ = _factories()
    payload = CreativeDocumentPayload(
        "document-1",
        "Bounded change brief",
        ("Evidence-linked summary.", "No production authority is transferred."),
        (_source(),),
    )

    artifact = handoff.create(_request(CREATIVE_DOCUMENT_CAPABILITY, payload))

    assert artifact.target_object_id == "document-1"
    assert artifact.target_status == "REVIEW_REQUIRED"
    assert artifact.target_approved is False
    with pytest.raises(CreativeDocumentError, match="only approved artifacts"):
        creative.export_projection("document-1")


def test_commerce_handoff_creates_zero_spend_unapproved_plan() -> None:
    handoff, _, _, _, commerce, _ = _factories()
    payload = CommerceGrowthPayload(
        "growth-1",
        "Existing users",
        ("content_draft", "social_draft"),
        (_source(),),
    )

    artifact = handoff.create(_request(COMMERCE_GROWTH_CAPABILITY, payload))

    assert artifact.target_object_id == "growth-1"
    assert artifact.target_status == "REVIEW_REQUIRED"
    assert artifact.target_approved is False
    assert artifact.external_applied is False
    with pytest.raises(CommerceGrowthError, match="only approved growth plans"):
        commerce.review_projection("growth-1")


def test_personal_operations_handoff_creates_draft_only_plan() -> None:
    handoff, _, _, _, _, personal = _factories()
    payload = PersonalOperationsPayload(
        "operations-1",
        (
            (
                "step-1",
                "checklist_draft",
                "local-review",
                "Review the validated software handoff.",
            ),
        ),
    )

    artifact = handoff.create(_request(PERSONAL_OPERATIONS_CAPABILITY, payload))

    assert artifact.target_object_id == "operations-1"
    assert artifact.target_status == "REVIEW_REQUIRED"
    assert artifact.target_approved is False
    assert artifact.external_applied is False
    with pytest.raises(PersonalOperationsError, match="only approved operation plans"):
        personal.review_projection("operations-1")


def test_identical_research_handoffs_are_content_deterministic() -> None:
    payload = ResearchDataPayload("claim-1", "Stable claim.", (_source(),))
    first, _, _, _, _, _ = _factories()
    second, _, _, _, _, _ = _factories()

    first_artifact = first.create(_request(RESEARCH_DATA_CAPABILITY, payload))
    second_artifact = second.create(_request(RESEARCH_DATA_CAPABILITY, payload))

    assert first_artifact.goal_sha256 == second_artifact.goal_sha256
    assert first_artifact.target_output_sha256 == second_artifact.target_output_sha256
    assert first_artifact.artifact_sha256 == second_artifact.artifact_sha256


def test_sf10_rejects_source_evidence_bypass_and_authority_escalation() -> None:
    payload = PersonalOperationsPayload(
        "operations-1",
        (("step-1", "note_draft", "local", "draft"),),
    )
    cases = (
        (_proposal(passed=False), _execution(), "validation must pass"),
        (_proposal(requires_human_approval=False), _execution(), "human approval requirement"),
        (_proposal(production_applied=True), _execution(), "production-applied"),
        (_proposal(), _execution(status="FAILED"), "not handoff-eligible"),
        (_proposal(), _execution(evidence_digest="bad"), "digest is invalid"),
    )
    for index, (proposal, execution, message) in enumerate(cases):
        handoff, _, _, _, _, _ = _factories()
        with pytest.raises(SpecializedFactoryHandoffError, match=message):
            handoff.create(
                _request(
                    PERSONAL_OPERATIONS_CAPABILITY,
                    payload,
                    handoff_id=f"failure-{index}",
                    proposal=proposal,
                    execution=execution,
                )
            )


def test_sf10_rejects_non_engineering_self_verified_and_non_ready_steps() -> None:
    payload = PersonalOperationsPayload(
        "operations-1",
        (("step-1", "note_draft", "local", "draft"),),
    )
    base = _execution()
    non_engineering = replace(
        base,
        admission=replace(base.admission, agent_id="ilaios.agent.security.codesec.v1"),
    )
    self_verified = replace(
        base,
        admission=replace(base.admission, verifier_id=BACKEND_ID),
    )
    blocked_step = replace(base.skill_results[0], status="BLOCKED")
    blocked = replace(base, skill_results=(blocked_step,))
    cases = (
        (non_engineering, "engineering-agent"),
        (self_verified, "cannot independently verify"),
        (blocked, "skill steps must be READY"),
    )
    for index, (execution, message) in enumerate(cases):
        handoff, _, _, _, _, _ = _factories()
        with pytest.raises(SpecializedFactoryHandoffError, match=message):
            handoff.create(
                _request(
                    PERSONAL_OPERATIONS_CAPABILITY,
                    payload,
                    handoff_id=f"agent-failure-{index}",
                    execution=execution,
                )
            )


def test_sf10_rejects_duplicate_unknown_target_and_payload_mismatch() -> None:
    payload = ResearchDataPayload("claim-1", "Stable claim.", (_source(),))
    handoff, _, _, _, _, _ = _factories()
    handoff.create(_request(RESEARCH_DATA_CAPABILITY, payload))
    with pytest.raises(SpecializedFactoryHandoffError, match="handoff_id already exists"):
        handoff.create(_request(RESEARCH_DATA_CAPABILITY, payload))

    unknown, _, _, _, _, _ = _factories()
    with pytest.raises(SpecializedFactoryHandoffError, match="not an SF-10 specialized factory"):
        unknown.create(
            _request(
                "ilaios.capability.app-factory",
                PersonalOperationsPayload(
                    "operations-1",
                    (("step-1", "note_draft", "local", "draft"),),
                ),
                handoff_id="unknown-target",
            )
        )

    mismatch, _, _, _, _, _ = _factories()
    with pytest.raises(SpecializedFactoryHandoffError, match="payload type mismatch"):
        mismatch.create(
            _request(
                RESEARCH_DATA_CAPABILITY,
                PersonalOperationsPayload(
                    "operations-2",
                    (("step-1", "note_draft", "local", "draft"),),
                ),
                handoff_id="payload-mismatch",
            )
        )
