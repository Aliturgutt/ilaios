"""SF-15 deterministic SBOM lineage, scope, and authority tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.agent_governance import AgentAdmissionEvidence
from services.control_plane.proposals import (
    BudgetEnvelope,
    DataClass,
    GoalSpec,
    RiskClass,
)
from services.software_factory import (
    EvidenceBundle,
    PromotionProposal,
    SoftwareFactoryError,
    ValidationResult,
)
from services.software_factory_agents import EngineeringAgentExecution
from services.software_factory_dependencies import (
    CommercialCompatibility,
    DependencyChange,
    DependencyGovernanceRecord,
    DependencyGovernanceRequest,
    DependencyOperation,
    DependencyPolicy,
    DependencyRole,
    DependencySecurityStatus,
    SoftwareFactoryDependencyGovernance,
)
from services.software_factory_license_provenance import (
    ArtifactProvenanceInput,
    LicenseDisposition,
    LicenseProvenancePolicy,
    LicenseProvenanceRequest,
    LicenseProvenanceRecord,
    ModelProviderMetadata,
    ProvenanceKind,
    ProvenanceUsage,
    SoftwareFactoryLicenseProvenance,
)
from services.software_factory_review import (
    IndependentReviewRecord,
    IndependentReviewSubmission,
    ReviewDecision,
    SoftwareFactoryIndependentReview,
    SoftwareIndependentReviewRequest,
)
from services.software_factory_sbom import (
    SBOMComponentType,
    SBOMCoverage,
    SBOM_DOCUMENT_FORMAT,
    SoftwareFactorySBOM,
    SoftwareSBOMRequest,
    render_sbom,
    render_sbom_json,
)
from services.software_factory_skills import (
    SkillExecutionResult,
    SkillRegistry,
    default_skills_root,
)
from services.software_factory_validation import (
    SoftwareFactoryValidationPipeline,
    SoftwareValidationRequest,
)
from src.core.validation_pipeline import canonical_sha256

NOW = datetime(2026, 8, 14, tzinfo=timezone.utc)
REPOSITORY_SHA = "a" * 40
AGENT_ID = "ilaios.agent.engineering.backend.v1"
VERIFIER_ID = "ilaios.agent.meta.independent-verifier.v1"
VALIDATOR_ID = "ilaios.validator.software-factory.v1"
CODE_REVIEWER = "ilaios.reviewer.code.independent.v1"
SECURITY_REVIEWER = "ilaios.reviewer.security.independent.v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
CHANGED_PATHS = (
    "pyproject.toml",
    "services/example.py",
    "uv.lock",
)


def _registry() -> SkillRegistry:
    return SkillRegistry(default_skills_root(REPO_ROOT))


def _goal() -> GoalSpec:
    return GoalSpec(
        "Generate deterministic governed SBOM evidence.",
        (
            "SBOM is bound to exact provenance",
            "dependency inventory is fail closed",
        ),
        RiskClass.HIGH,
        DataClass.INTERNAL,
        BudgetEnvelope(3, 600),
    )


def _proposal() -> PromotionProposal:
    evidence = EvidenceBundle(
        "evidence-sf15",
        REPOSITORY_SHA,
        "b" * 64,
        "c" * 64,
        ValidationResult(True, ("pytest", "ruff", "mypy"), ()),
        "2026-08-14T11:00:00+00:00",
    )
    return PromotionProposal("proposal-sf15", "job-sf15", evidence, True, False)


def _execution() -> EngineeringAgentExecution:
    admission = AgentAdmissionEvidence(
        "invoke-sf15",
        AGENT_ID,
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
        ("repository_base_sha", "reviewer", "validation_results"),
        True,
    )
    status = "REVIEW_REQUIRED"
    digest = canonical_sha256(
        {
            "agent_id": AGENT_ID,
            "invocation_id": admission.invocation_id,
            "verifier_id": VERIFIER_ID,
            "base_sha": REPOSITORY_SHA,
            "status": status,
            "skills": [
                {
                    "skill_id": result.skill_id,
                    "version": result.version,
                    "status": result.status,
                    "evidence": list(result.emitted_evidence),
                    "independent_review_required": True,
                }
            ],
        }
    )
    return EngineeringAgentExecution(admission, (result,), status, digest)


def _validation_request() -> SoftwareValidationRequest:
    return SoftwareValidationRequest(
        pipeline_run_id="sf11-run-for-sf15",
        tenant_id="tenant-1",
        task_id="task-1",
        correlation_id="correlation-1",
        validator_id=VALIDATOR_ID,
        environment_id="ci-ephemeral-read-only",
        policy_reference="policy/software-factory/critical-risk/v1",
        goal=_goal(),
        software_proposal=_proposal(),
        engineering_execution=_execution(),
    )


def _submission(
    skill_id: str,
    report_sha256: str,
    subject_sha256: str,
) -> IndependentReviewSubmission:
    reviewer_id = CODE_REVIEWER if skill_id == "sf-code-review" else SECURITY_REVIEWER
    return IndependentReviewSubmission(
        skill_id=skill_id,
        skill_version="1.0.0",
        reviewer_id=reviewer_id,
        reviewed_subject_sha256=subject_sha256,
        validation_report_sha256=report_sha256,
        reviewed_paths=CHANGED_PATHS,
        findings=(),
        decision=ReviewDecision.APPROVE,
        evidence_references=(f"evidence://sf15/{skill_id}",),
        read_only=True,
    )


def _review_bundle() -> tuple[SoftwareIndependentReviewRequest, IndependentReviewRecord]:
    validation_request = _validation_request()
    report = SoftwareFactoryValidationPipeline().validate(validation_request)
    request = SoftwareIndependentReviewRequest(
        review_id="sf12-review-for-sf15",
        tenant_id=validation_request.tenant_id,
        task_id=validation_request.task_id,
        correlation_id=validation_request.correlation_id,
        policy_reference=validation_request.policy_reference,
        environment_id=validation_request.environment_id,
        changed_paths=CHANGED_PATHS,
        validation_request=validation_request,
        validation_report=report,
        submissions=(
            _submission("sf-code-review", report.report_sha256, report.subject_sha256),
            _submission(
                "sf-security-review",
                report.report_sha256,
                report.subject_sha256,
            ),
        ),
    )
    record = SoftwareFactoryIndependentReview(_registry()).review(request)
    return request, record


def _dependency_policy() -> DependencyPolicy:
    return DependencyPolicy(
        policy_id="policy/software-factory/dependencies/v1",
        allowed_sources=frozenset({"pypi"}),
        allowed_licenses=frozenset({"License-Allowed"}),
        review_licenses=frozenset({"License-Review"}),
        blocked_licenses=frozenset({"License-Blocked"}),
    )


def _dependency_change(**overrides: object) -> DependencyChange:
    values: dict[str, object] = {
        "package": "example-dependency",
        "version": "1.2.3",
        "source": "pypi",
        "role": DependencyRole.DIRECT,
        "reason": "Required by the reviewed integration.",
        "integrity": "sha256:" + "d" * 64,
        "integrity_verified": True,
        "security_status": DependencySecurityStatus.CLEAR,
        "license": "License-Allowed",
        "commercial_compatibility": CommercialCompatibility.COMPATIBLE,
        "operation": DependencyOperation.ADD,
        "manifest_path": "pyproject.toml",
        "lockfile_path": "uv.lock",
    }
    values.update(overrides)
    return DependencyChange(**values)  # type: ignore[arg-type]


def _dependency_bundle(
    review_request: SoftwareIndependentReviewRequest,
    review_record: IndependentReviewRecord,
    *,
    change: DependencyChange,
) -> tuple[DependencyGovernanceRequest, DependencyGovernanceRecord]:
    request = DependencyGovernanceRequest(
        governance_id="sf13-governance-for-sf15",
        review_request=review_request,
        review_record=review_record,
        dependency_changes=(change,),
        policy=_dependency_policy(),
    )
    record = SoftwareFactoryDependencyGovernance(_registry()).evaluate(request)
    return request, record


def _license_policy() -> LicenseProvenancePolicy:
    return LicenseProvenancePolicy(
        policy_id="policy/software-factory/license-provenance/v1",
        allowed_licenses=frozenset({"ILAIOS-Proprietary", "License-Allowed"}),
        review_licenses=frozenset({"License-Review"}),
        blocked_licenses=frozenset({"License-Blocked"}),
        model_provider_metadata_permitted=True,
    )


def _model_metadata() -> ModelProviderMetadata:
    return ModelProviderMetadata(
        disclosure_permitted=True,
        provider_id="provider-test",
        model_id="model-test",
        invocation_id="invoke-sf15",
        evidence_reference="evidence://sf15/model-provider",
    )


def _generated_artifact() -> ArtifactProvenanceInput:
    return ArtifactProvenanceInput(
        artifact_reference="artifact://generated/services-example",
        kind=ProvenanceKind.GENERATED_CODE,
        usage=ProvenanceUsage.FIRST_PARTY_GENERATION,
        artifact_sha256="e" * 64,
        repository_paths=("services/example.py",),
        source_reference="ilaios://software-factory/invoke-sf15",
        generated_by_ai=True,
        code_text_imported=False,
        license="ILAIOS-Proprietary",
        license_evidence_reference="policy://ilaios/proprietary/v1",
        commercial_compatibility=CommercialCompatibility.COMPATIBLE,
        evidence_references=("evidence://sf15/generated-code",),
    )


def _dependency_artifact(
    dependency_record: DependencyGovernanceRecord,
) -> ArtifactProvenanceInput:
    evidence = dependency_record.dependency_evidence[0]
    return ArtifactProvenanceInput(
        artifact_reference="artifact://dependency/example-dependency",
        kind=ProvenanceKind.THIRD_PARTY_DEPENDENCY,
        usage=ProvenanceUsage.DEPENDENCY_INCLUSION,
        artifact_sha256="1" * 64,
        repository_paths=tuple(
            sorted(
                path
                for path in (evidence.manifest_path, evidence.lockfile_path)
                if path is not None
            )
        ),
        source_reference="pypi://example-dependency/1.2.3",
        generated_by_ai=False,
        code_text_imported=False,
        license=evidence.license,
        license_evidence_reference="evidence://licenses/example-dependency",
        commercial_compatibility=evidence.commercial_compatibility,
        evidence_references=("evidence://sf15/dependency",),
        dependency_package=evidence.package,
        dependency_version=evidence.version,
        dependency_source=evidence.source,
        upstream_dependency_evidence_sha256=evidence.evidence_sha256,
    )


def _concept_reference() -> ArtifactProvenanceInput:
    return ArtifactProvenanceInput(
        artifact_reference="reference://concept/external-standard",
        kind=ProvenanceKind.EXTERNAL_REFERENCE,
        usage=ProvenanceUsage.CONCEPT_REFERENCE,
        artifact_sha256="2" * 64,
        repository_paths=(),
        source_reference="reference://external-standard",
        generated_by_ai=False,
        code_text_imported=False,
        license=None,
        license_evidence_reference=None,
        commercial_compatibility=CommercialCompatibility.UNKNOWN,
        evidence_references=("evidence://sf15/concept-reference",),
    )


def _imported_code() -> ArtifactProvenanceInput:
    return ArtifactProvenanceInput(
        artifact_reference="artifact://imported/services-example",
        kind=ProvenanceKind.EXTERNAL_REFERENCE,
        usage=ProvenanceUsage.CODE_TEXT_IMPORT,
        artifact_sha256="3" * 64,
        repository_paths=("services/example.py",),
        source_reference="reference://licensed-source/snippet",
        generated_by_ai=False,
        code_text_imported=True,
        license="License-Allowed",
        license_evidence_reference="evidence://licenses/imported-code",
        commercial_compatibility=CommercialCompatibility.COMPATIBLE,
        evidence_references=("evidence://sf15/imported-code",),
    )


def _provenance_bundle(
    *,
    dependency_change: DependencyChange | None = None,
    generated_artifact: ArtifactProvenanceInput | None = None,
    include_concept_reference: bool = False,
) -> tuple[LicenseProvenanceRequest, LicenseProvenanceRecord]:
    review_request, review_record = _review_bundle()
    change = dependency_change or _dependency_change()
    dependency_request, dependency_record = _dependency_bundle(
        review_request,
        review_record,
        change=change,
    )
    artifacts: tuple[ArtifactProvenanceInput, ...] = (
        generated_artifact or _generated_artifact(),
        _dependency_artifact(dependency_record),
    )
    if include_concept_reference:
        artifacts += (_concept_reference(),)
    request = LicenseProvenanceRequest(
        provenance_id="sf14-provenance-for-sf15",
        intent="Establish exact upstream provenance before SBOM generation.",
        artifact_references=tuple(item.artifact_reference for item in artifacts),
        review_request=review_request,
        review_record=review_record,
        artifacts=artifacts,
        policy=_license_policy(),
        model_provider_metadata=_model_metadata(),
        dependency_governance_request=dependency_request,
        dependency_governance_record=dependency_record,
    )
    record = SoftwareFactoryLicenseProvenance(_registry()).evaluate(request)
    return request, record


def _sbom_request(
    *,
    dependency_change: DependencyChange | None = None,
    generated_artifact: ArtifactProvenanceInput | None = None,
    include_concept_reference: bool = False,
) -> SoftwareSBOMRequest:
    provenance_request, provenance_record = _provenance_bundle(
        dependency_change=dependency_change,
        generated_artifact=generated_artifact,
        include_concept_reference=include_concept_reference,
    )
    return SoftwareSBOMRequest(
        sbom_id="sf15-sbom-1",
        document_name="ILAIOS reviewed ChangeSet SBOM",
        provenance_request=provenance_request,
        provenance_record=provenance_record,
    )


def _sbom() -> SoftwareFactorySBOM:
    return SoftwareFactorySBOM(_registry())


def test_sbom_is_deterministic_and_binds_exact_sf13_sf14_lineage() -> None:
    request = _sbom_request()
    first = _sbom().generate(request)
    second = _sbom().generate(request)

    assert first == second
    assert first.document_format == SBOM_DOCUMENT_FORMAT
    assert first.coverage is SBOMCoverage.REVIEWED_CHANGESET
    assert first.repository_base_sha == REPOSITORY_SHA
    assert first.changeset_sha256 == "b" * 64
    assert first.license_provenance_record_sha256 == request.provenance_record.record_sha256
    assert (
        first.dependency_governance_record_sha256
        == request.provenance_record.dependency_governance_record_sha256
    )
    assert first.serial_number == f"urn:ilaios:sbom:{first.document_sha256}"
    assert len(first.document_sha256) == 64
    assert render_sbom(first) == render_sbom(second)
    assert render_sbom_json(first) == render_sbom_json(second)

    generated = next(
        item for item in first.components
        if item.component_type is SBOMComponentType.APPLICATION
    )
    dependency = next(
        item for item in first.components
        if item.component_type is SBOMComponentType.LIBRARY
    )
    assert generated.generated_by_ai is True
    assert generated.license == "ILAIOS-Proprietary"
    assert generated.dependency_evidence_sha256 is None
    assert dependency.name == "example-dependency"
    assert dependency.version == "1.2.3"
    assert dependency.integrity == "sha256:" + "d" * 64
    assert dependency.integrity_verified is True
    assert dependency.license == "License-Allowed"
    assert dependency.commercial_compatibility is CommercialCompatibility.COMPATIBLE
    assert dependency.dependency_role is DependencyRole.DIRECT
    assert dependency.dependency_operation is DependencyOperation.ADD
    assert dependency.present_after_change is True
    assert dependency.dependency_evidence_sha256 is not None


def test_sbom_never_claims_release_build_ip_or_downstream_authority() -> None:
    document = _sbom().generate(_sbom_request())

    assert document.release_complete is False
    assert document.build_provenance_bound is False
    assert document.ip_risk_clearance_claimed is False
    assert document.acceptance_authorized is False
    assert document.promotion_authorized is False
    assert document.deployment_authorized is False
    assert document.production_applied is False
    assert document.subject_mutated is False
    assert "REVIEWED_CHANGESET_SCOPE_ONLY" in document.limitations
    assert "RELEASE_COMPLETENESS_NOT_CLAIMED" in document.limitations
    assert "BUILD_PROVENANCE_NOT_BOUND_UNTIL_SF16" in document.limitations


def test_stale_or_tampered_sf14_record_is_rejected() -> None:
    request = _sbom_request()
    tampered = replace(request.provenance_record, record_sha256="9" * 64)

    with pytest.raises(SoftwareFactoryError, match="stale, tampered, or mismatched"):
        _sbom().generate(replace(request, provenance_record=tampered))


def test_sbom_preserves_review_required_and_block_dispositions() -> None:
    review_required = _sbom().generate(
        _sbom_request(
            dependency_change=_dependency_change(license="License-Review")
        )
    )
    assert review_required.disposition is LicenseDisposition.REVIEW_REQUIRED
    review_component = next(
        item for item in review_required.components
        if item.component_type is SBOMComponentType.LIBRARY
    )
    assert review_component.disposition is LicenseDisposition.REVIEW_REQUIRED

    blocked = _sbom().generate(
        _sbom_request(
            dependency_change=_dependency_change(license="License-Blocked")
        )
    )
    assert blocked.disposition is LicenseDisposition.BLOCK
    blocked_component = next(
        item for item in blocked.components
        if item.component_type is SBOMComponentType.LIBRARY
    )
    assert blocked_component.disposition is LicenseDisposition.BLOCK


def test_concept_reference_is_evidence_not_a_material_component() -> None:
    document = _sbom().generate(
        _sbom_request(include_concept_reference=True)
    )

    assert len(document.components) == 2
    assert len(document.non_material_references) == 1
    reference = document.non_material_references[0]
    assert reference.artifact_reference == "reference://concept/external-standard"
    assert all(
        component.artifact_reference != reference.artifact_reference
        for component in document.components
    )


def test_imported_code_is_material_and_remains_review_required() -> None:
    document = _sbom().generate(
        _sbom_request(generated_artifact=_imported_code())
    )

    imported = next(
        item for item in document.components
        if item.component_type is SBOMComponentType.IMPORTED_SOURCE
    )
    assert imported.code_text_imported is True
    assert imported.disposition is LicenseDisposition.REVIEW_REQUIRED
    assert document.disposition is LicenseDisposition.REVIEW_REQUIRED
    assert "CODE_TEXT_IMPORTED_FROM_EXTERNAL_REFERENCE" in imported.risk_flags


def test_removed_dependency_is_retained_as_transition_evidence_but_not_present() -> None:
    document = _sbom().generate(
        _sbom_request(
            dependency_change=_dependency_change(operation=DependencyOperation.REMOVE)
        )
    )
    dependency = next(
        item for item in document.components
        if item.component_type is SBOMComponentType.LIBRARY
    )

    assert dependency.dependency_operation is DependencyOperation.REMOVE
    assert dependency.present_after_change is False


def test_sbom_rejects_blank_or_unbounded_identity() -> None:
    request = _sbom_request()
    with pytest.raises(SoftwareFactoryError, match="sbom_id must be non-blank"):
        _sbom().generate(replace(request, sbom_id=" "))
    with pytest.raises(SoftwareFactoryError, match="bounded identifier length"):
        _sbom().generate(replace(request, sbom_id="x" * 161))
    with pytest.raises(SoftwareFactoryError, match="document_name must be non-blank"):
        _sbom().generate(replace(request, document_name=" "))


def test_rendered_payload_exposes_scope_and_authority_boundaries() -> None:
    document = _sbom().generate(_sbom_request())
    payload = render_sbom(document)

    metadata = payload["metadata"]
    policy = payload["policy"]
    authority = payload["authority"]
    assert isinstance(metadata, dict)
    assert isinstance(policy, dict)
    assert isinstance(authority, dict)
    assert metadata["coverage"] == "REVIEWED_CHANGESET"
    assert policy["ipRiskClearanceClaimed"] is False
    assert authority == {
        "releaseComplete": False,
        "buildProvenanceBound": False,
        "acceptanceAuthorized": False,
        "promotionAuthorized": False,
        "deploymentAuthorized": False,
        "productionApplied": False,
        "subjectMutated": False,
    }


def test_component_digest_changes_when_dependency_integrity_changes() -> None:
    first = _sbom().generate(_sbom_request())
    second = _sbom().generate(
        _sbom_request(
            dependency_change=_dependency_change(integrity="sha256:" + "4" * 64)
        )
    )
    first_dependency = next(
        item for item in first.components
        if item.component_type is SBOMComponentType.LIBRARY
    )
    second_dependency = next(
        item for item in second.components
        if item.component_type is SBOMComponentType.LIBRARY
    )

    assert first_dependency.component_sha256 != second_dependency.component_sha256
    assert first.document_sha256 != second.document_sha256
