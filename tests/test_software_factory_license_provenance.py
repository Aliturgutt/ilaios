"""SF-14 license/IP provenance lineage, policy, and authority tests."""

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
    ModelProviderMetadata,
    ProvenanceKind,
    ProvenanceUsage,
    SoftwareFactoryLicenseProvenance,
)
from services.software_factory_review import (
    IndependentReviewRecord,
    IndependentReviewSubmission,
    ReviewDecision,
    ReviewFinding,
    SoftwareFactoryIndependentReview,
    SoftwareIndependentReviewRequest,
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
    "assets/reference.svg",
    "pyproject.toml",
    "services/example.py",
    "uv.lock",
)


def _registry() -> SkillRegistry:
    return SkillRegistry(default_skills_root(REPO_ROOT))


def _goal() -> GoalSpec:
    return GoalSpec(
        "Establish exact license and IP provenance.",
        (
            "all reviewed artifacts have provenance",
            "license disposition is fail closed",
        ),
        RiskClass.HIGH,
        DataClass.INTERNAL,
        BudgetEnvelope(3, 600),
    )


def _proposal() -> PromotionProposal:
    evidence = EvidenceBundle(
        "evidence-sf14",
        REPOSITORY_SHA,
        "b" * 64,
        "c" * 64,
        ValidationResult(True, ("pytest", "ruff", "mypy"), ()),
        "2026-08-14T10:00:00+00:00",
    )
    return PromotionProposal("proposal-sf14", "job-sf14", evidence, True, False)


def _execution() -> EngineeringAgentExecution:
    admission = AgentAdmissionEvidence(
        "invoke-sf14",
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
        pipeline_run_id="sf11-run-for-sf14",
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
    *,
    decision: ReviewDecision = ReviewDecision.APPROVE,
    findings: tuple[ReviewFinding, ...] = (),
) -> IndependentReviewSubmission:
    reviewer_id = CODE_REVIEWER if skill_id == "sf-code-review" else SECURITY_REVIEWER
    return IndependentReviewSubmission(
        skill_id=skill_id,
        skill_version="1.0.0",
        reviewer_id=reviewer_id,
        reviewed_subject_sha256=subject_sha256,
        validation_report_sha256=report_sha256,
        reviewed_paths=CHANGED_PATHS,
        findings=findings,
        decision=decision,
        evidence_references=(f"evidence://sf14/{skill_id}",),
        read_only=True,
    )


def _review_bundle(
    *,
    nonapproved: bool = False,
) -> tuple[SoftwareIndependentReviewRequest, IndependentReviewRecord]:
    validation_request = _validation_request()
    report = SoftwareFactoryValidationPipeline().validate(validation_request)
    code_decision = ReviewDecision.APPROVE
    code_findings: tuple[ReviewFinding, ...] = ()
    if nonapproved:
        code_decision = ReviewDecision.CHANGES_REQUIRED
        code_findings = (
            ReviewFinding(
                "license-review-1",
                "HIGH",
                "services/example.py:1",
                "evidence://sf14/review-finding",
                "Provenance requires remediation.",
                "Repair provenance and repeat independent review.",
                "OPEN",
            ),
        )
    request = SoftwareIndependentReviewRequest(
        review_id="sf12-review-for-sf14",
        tenant_id=validation_request.tenant_id,
        task_id=validation_request.task_id,
        correlation_id=validation_request.correlation_id,
        policy_reference=validation_request.policy_reference,
        environment_id=validation_request.environment_id,
        changed_paths=CHANGED_PATHS,
        validation_request=validation_request,
        validation_report=report,
        submissions=(
            _submission(
                "sf-code-review",
                report.report_sha256,
                report.subject_sha256,
                decision=code_decision,
                findings=code_findings,
            ),
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
        allowed_sources=frozenset({"pypi", "npm"}),
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
    change: DependencyChange | None = None,
) -> tuple[DependencyGovernanceRequest, DependencyGovernanceRecord]:
    request = DependencyGovernanceRequest(
        governance_id="sf13-governance-for-sf14",
        review_request=review_request,
        review_record=review_record,
        dependency_changes=(_dependency_change() if change is None else change,),
        policy=_dependency_policy(),
    )
    record = SoftwareFactoryDependencyGovernance(_registry()).evaluate(request)
    return request, record


def _license_policy(**overrides: object) -> LicenseProvenancePolicy:
    values: dict[str, object] = {
        "policy_id": "policy/software-factory/license-provenance/v1",
        "allowed_licenses": frozenset({"ILAIOS-Proprietary", "License-Allowed"}),
        "review_licenses": frozenset({"License-Review"}),
        "blocked_licenses": frozenset({"License-Blocked"}),
        "model_provider_metadata_permitted": True,
    }
    values.update(overrides)
    return LicenseProvenancePolicy(**values)  # type: ignore[arg-type]


def _model_metadata(**overrides: object) -> ModelProviderMetadata:
    values: dict[str, object] = {
        "disclosure_permitted": True,
        "provider_id": "provider-test",
        "model_id": "model-test",
        "invocation_id": "invoke-sf14",
        "evidence_reference": "evidence://sf14/model-provider",
    }
    values.update(overrides)
    return ModelProviderMetadata(**values)  # type: ignore[arg-type]


def _generated_artifact(**overrides: object) -> ArtifactProvenanceInput:
    values: dict[str, object] = {
        "artifact_reference": "artifact://generated/services-example",
        "kind": ProvenanceKind.GENERATED_CODE,
        "usage": ProvenanceUsage.FIRST_PARTY_GENERATION,
        "artifact_sha256": "e" * 64,
        "repository_paths": ("services/example.py",),
        "source_reference": "ilaios://software-factory/invoke-sf14",
        "generated_by_ai": True,
        "code_text_imported": False,
        "license": "ILAIOS-Proprietary",
        "license_evidence_reference": "policy://ilaios/proprietary/v1",
        "commercial_compatibility": CommercialCompatibility.COMPATIBLE,
        "evidence_references": ("evidence://sf14/generated-code",),
    }
    values.update(overrides)
    return ArtifactProvenanceInput(**values)  # type: ignore[arg-type]


def _asset_artifact(**overrides: object) -> ArtifactProvenanceInput:
    values: dict[str, object] = {
        "artifact_reference": "artifact://asset/reference-svg",
        "kind": ProvenanceKind.THIRD_PARTY_ASSET,
        "usage": ProvenanceUsage.ASSET_IMPORT,
        "artifact_sha256": "f" * 64,
        "repository_paths": ("assets/reference.svg",),
        "source_reference": "source://asset/reference-svg",
        "generated_by_ai": False,
        "code_text_imported": False,
        "license": "License-Allowed",
        "license_evidence_reference": "evidence://licenses/reference-svg",
        "commercial_compatibility": CommercialCompatibility.COMPATIBLE,
        "evidence_references": ("evidence://sf14/asset",),
    }
    values.update(overrides)
    return ArtifactProvenanceInput(**values)  # type: ignore[arg-type]


def _dependency_artifact(
    dependency_record: DependencyGovernanceRecord,
    **overrides: object,
) -> ArtifactProvenanceInput:
    evidence = dependency_record.dependency_evidence[0]
    values: dict[str, object] = {
        "artifact_reference": "artifact://dependency/example-dependency",
        "kind": ProvenanceKind.THIRD_PARTY_DEPENDENCY,
        "usage": ProvenanceUsage.DEPENDENCY_INCLUSION,
        "artifact_sha256": "1" * 64,
        "repository_paths": tuple(
            sorted(
                path
                for path in (evidence.manifest_path, evidence.lockfile_path)
                if path is not None
            )
        ),
        "source_reference": "pypi://example-dependency/1.2.3",
        "generated_by_ai": False,
        "code_text_imported": False,
        "license": evidence.license,
        "license_evidence_reference": "evidence://licenses/example-dependency",
        "commercial_compatibility": evidence.commercial_compatibility,
        "evidence_references": ("evidence://sf14/dependency",),
        "dependency_package": evidence.package,
        "dependency_version": evidence.version,
        "dependency_source": evidence.source,
        "upstream_dependency_evidence_sha256": evidence.evidence_sha256,
    }
    values.update(overrides)
    return ArtifactProvenanceInput(**values)  # type: ignore[arg-type]


def _concept_reference(**overrides: object) -> ArtifactProvenanceInput:
    values: dict[str, object] = {
        "artifact_reference": "reference://concept/external-standard",
        "kind": ProvenanceKind.EXTERNAL_REFERENCE,
        "usage": ProvenanceUsage.CONCEPT_REFERENCE,
        "artifact_sha256": "2" * 64,
        "repository_paths": (),
        "source_reference": "reference://external-standard",
        "generated_by_ai": False,
        "code_text_imported": False,
        "license": None,
        "license_evidence_reference": None,
        "commercial_compatibility": CommercialCompatibility.UNKNOWN,
        "evidence_references": ("evidence://sf14/concept-reference",),
    }
    values.update(overrides)
    return ArtifactProvenanceInput(**values)  # type: ignore[arg-type]


def _imported_code(**overrides: object) -> ArtifactProvenanceInput:
    values: dict[str, object] = {
        "artifact_reference": "reference://imported/code-text",
        "kind": ProvenanceKind.EXTERNAL_REFERENCE,
        "usage": ProvenanceUsage.CODE_TEXT_IMPORT,
        "artifact_sha256": "3" * 64,
        "repository_paths": ("services/example.py",),
        "source_reference": "reference://licensed-source/snippet",
        "generated_by_ai": False,
        "code_text_imported": True,
        "license": "License-Allowed",
        "license_evidence_reference": "evidence://licenses/imported-code",
        "commercial_compatibility": CommercialCompatibility.COMPATIBLE,
        "evidence_references": ("evidence://sf14/imported-code",),
    }
    values.update(overrides)
    return ArtifactProvenanceInput(**values)  # type: ignore[arg-type]


def _request(
    *,
    artifacts: tuple[ArtifactProvenanceInput, ...] | None = None,
    artifact_references: tuple[str, ...] | None = None,
    license_policy: LicenseProvenancePolicy | None = None,
    model_metadata: ModelProviderMetadata | None = None,
    dependency_change: DependencyChange | None = None,
    include_dependency_governance: bool = True,
    nonapproved_review: bool = False,
) -> LicenseProvenanceRequest:
    review_request, review_record = _review_bundle(nonapproved=nonapproved_review)
    dependency_request: DependencyGovernanceRequest | None = None
    dependency_record: DependencyGovernanceRecord | None = None
    if include_dependency_governance and not nonapproved_review:
        dependency_request, dependency_record = _dependency_bundle(
            review_request,
            review_record,
            change=dependency_change,
        )
    selected_artifacts: tuple[ArtifactProvenanceInput, ...]
    if artifacts is None:
        if dependency_record is None:
            selected_artifacts = (_generated_artifact(), _asset_artifact())
        else:
            selected_artifacts = (
                _generated_artifact(),
                _asset_artifact(),
                _dependency_artifact(dependency_record),
            )
    else:
        selected_artifacts = artifacts
    references = (
        tuple(item.artifact_reference for item in selected_artifacts)
        if artifact_references is None
        else artifact_references
    )
    return LicenseProvenanceRequest(
        provenance_id="sf14-provenance-1",
        intent="Establish exact license/IP provenance for reviewed artifacts.",
        artifact_references=references,
        review_request=review_request,
        review_record=review_record,
        artifacts=selected_artifacts,
        policy=license_policy or _license_policy(),
        model_provider_metadata=model_metadata or _model_metadata(),
        dependency_governance_request=dependency_request,
        dependency_governance_record=dependency_record,
    )


def _provenance() -> SoftwareFactoryLicenseProvenance:
    return SoftwareFactoryLicenseProvenance(_registry())


def test_complete_provenance_chain_is_allowed_without_ip_clearance_or_authority() -> None:
    record = _provenance().evaluate(_request())

    assert record.skill_id == "sf-license-provenance"
    assert record.skill_version == "1.0.0"
    assert record.license_disposition is LicenseDisposition.ALLOW
    assert record.factory_job_id == "job-sf14"
    assert record.repository_base_sha == REPOSITORY_SHA
    assert record.changeset_sha256 == "b" * 64
    assert record.engineering_agent_id == AGENT_ID
    assert record.engineering_invocation_id == "invoke-sf14"
    assert record.reviewer_ids == tuple(sorted((CODE_REVIEWER, SECURITY_REVIEWER)))
    assert record.model_provider_metadata.provider_id == "provider-test"
    assert "AI_GENERATED_CODE_IP_RISK_NOT_CLEARED" in record.risk_flags
    assert record.ip_risk_clearance_claimed is False
    assert all(item.ip_risk_clearance_claimed is False for item in record.provenance_records)
    assert record.independent_review_required is True
    assert record.acceptance_authorized is False
    assert record.promotion_authorized is False
    assert record.deployment_authorized is False
    assert record.production_applied is False
    assert record.subject_mutated is False
    assert len(record.policy_sha256) == 64
    assert len(record.record_sha256) == 64


def test_generated_ai_code_never_claims_ip_risk_clearance() -> None:
    record = _provenance().evaluate(_request())
    generated = next(
        item for item in record.provenance_records
        if item.kind is ProvenanceKind.GENERATED_CODE
    )

    assert generated.generated_by_ai is True
    assert "AI_GENERATED_CODE_IP_RISK_NOT_CLEARED" in generated.risk_flags
    assert generated.ip_risk_clearance_claimed is False
    assert record.ip_risk_clearance_claimed is False


def test_artifact_reference_inventory_must_match_exactly() -> None:
    request = _request()
    with pytest.raises(SoftwareFactoryError, match="does not match provenance records"):
        _provenance().evaluate(
            replace(
                request,
                artifact_references=request.artifact_references + ("artifact://missing",),
            )
        )


def test_every_reviewed_path_requires_provenance_coverage() -> None:
    request = _request()
    artifacts = tuple(
        item for item in request.artifacts
        if item.kind is not ProvenanceKind.THIRD_PARTY_ASSET
    )
    with pytest.raises(SoftwareFactoryError, match="path coverage mismatch"):
        _provenance().evaluate(
            replace(
                request,
                artifacts=artifacts,
                artifact_references=tuple(item.artifact_reference for item in artifacts),
            )
        )


def test_artifact_provenance_cannot_escape_reviewed_path_scope() -> None:
    request = _request()
    generated = next(
        item for item in request.artifacts
        if item.kind is ProvenanceKind.GENERATED_CODE
    )
    tampered = replace(generated, repository_paths=("services/unreviewed.py",))
    artifacts = tuple(
        tampered if item is generated else item for item in request.artifacts
    )
    with pytest.raises(SoftwareFactoryError, match="exceeds exact SF-12 reviewed-path scope"):
        _provenance().evaluate(replace(request, artifacts=artifacts))


def test_dependency_paths_require_exact_sf13_evidence() -> None:
    request = _request(include_dependency_governance=False)
    with pytest.raises(SoftwareFactoryError, match="requires exact SF-13 evidence"):
        _provenance().evaluate(request)


def test_dependency_artifact_must_bind_exact_sf13_evidence() -> None:
    request = _request()
    dependency = next(
        item for item in request.artifacts
        if item.kind is ProvenanceKind.THIRD_PARTY_DEPENDENCY
    )
    tampered = replace(
        dependency,
        upstream_dependency_evidence_sha256="9" * 64,
    )
    artifacts = tuple(
        tampered if item is dependency else item for item in request.artifacts
    )
    with pytest.raises(SoftwareFactoryError, match="not bound to exact SF-13 evidence"):
        _provenance().evaluate(replace(request, artifacts=artifacts))


def test_dependency_license_cannot_conflict_with_sf13() -> None:
    request = _request()
    dependency = next(
        item for item in request.artifacts
        if item.kind is ProvenanceKind.THIRD_PARTY_DEPENDENCY
    )
    tampered = replace(dependency, license="License-Review")
    artifacts = tuple(
        tampered if item is dependency else item for item in request.artifacts
    )
    with pytest.raises(SoftwareFactoryError, match="conflicts with SF-13"):
        _provenance().evaluate(replace(request, artifacts=artifacts))


def test_stale_or_tampered_sf13_record_is_rejected() -> None:
    request = _request()
    assert request.dependency_governance_record is not None
    tampered = replace(
        request.dependency_governance_record,
        record_sha256="8" * 64,
    )
    with pytest.raises(SoftwareFactoryError, match="dependency-governance record is stale or tampered"):
        _provenance().evaluate(
            replace(request, dependency_governance_record=tampered)
        )


def test_sf13_review_required_or_block_cannot_be_upgraded() -> None:
    review_request = _request(
        dependency_change=_dependency_change(license="License-Review")
    )
    review_record = _provenance().evaluate(review_request)
    assert review_record.license_disposition is LicenseDisposition.REVIEW_REQUIRED

    blocked_request = _request(
        dependency_change=_dependency_change(license="License-Blocked")
    )
    blocked_record = _provenance().evaluate(blocked_request)
    assert blocked_record.license_disposition is LicenseDisposition.BLOCK


def test_third_party_asset_license_and_commercial_policy_are_fail_closed() -> None:
    request = _request()
    asset = next(
        item for item in request.artifacts
        if item.kind is ProvenanceKind.THIRD_PARTY_ASSET
    )
    blocked_asset = replace(
        asset,
        license="License-Blocked",
        commercial_compatibility=CommercialCompatibility.INCOMPATIBLE,
    )
    blocked_artifacts = tuple(
        blocked_asset if item is asset else item for item in request.artifacts
    )
    blocked = _provenance().evaluate(
        replace(request, artifacts=blocked_artifacts)
    )
    assert blocked.license_disposition is LicenseDisposition.BLOCK

    unknown_asset = replace(
        asset,
        license="License-Unclassified",
        commercial_compatibility=CommercialCompatibility.UNKNOWN,
    )
    unknown_artifacts = tuple(
        unknown_asset if item is asset else item for item in request.artifacts
    )
    unknown = _provenance().evaluate(
        replace(request, artifacts=unknown_artifacts)
    )
    assert unknown.license_disposition is LicenseDisposition.REVIEW_REQUIRED
    assert "LICENSE_CLASSIFICATION_UNRESOLVED" in unknown.risk_flags
    assert "COMMERCIAL_COMPATIBILITY_UNRESOLVED" in unknown.risk_flags


def test_concept_reference_is_distinct_from_code_text_import() -> None:
    request = _request()
    concept = _concept_reference()
    concept_request = replace(
        request,
        artifacts=request.artifacts + (concept,),
        artifact_references=request.artifact_references + (concept.artifact_reference,),
    )
    concept_record = _provenance().evaluate(concept_request)
    concept_evidence = next(
        item for item in concept_record.provenance_records
        if item.artifact_reference == concept.artifact_reference
    )
    assert concept_evidence.disposition is LicenseDisposition.ALLOW
    assert "REFERENCE_USED_FOR_CONCEPT_ONLY" in concept_evidence.risk_flags
    assert concept_evidence.code_text_imported is False

    generated = next(
        item for item in request.artifacts
        if item.kind is ProvenanceKind.GENERATED_CODE
    )
    imported = _imported_code()
    imported_artifacts = tuple(
        imported if item is generated else item for item in request.artifacts
    )
    imported_request = replace(
        request,
        artifacts=imported_artifacts,
        artifact_references=tuple(
            item.artifact_reference for item in imported_artifacts
        ),
    )
    imported_record = _provenance().evaluate(imported_request)
    assert imported_record.license_disposition is LicenseDisposition.REVIEW_REQUIRED
    imported_evidence = next(
        item for item in imported_record.provenance_records
        if item.kind is ProvenanceKind.EXTERNAL_REFERENCE
    )
    assert "CODE_TEXT_IMPORTED_FROM_EXTERNAL_REFERENCE" in imported_evidence.risk_flags


def test_imported_code_and_unknown_evidence_cannot_default_to_allow() -> None:
    with pytest.raises(SoftwareFactoryError, match="imported code/text cannot silently default"):
        _provenance().evaluate(
            _request(
                license_policy=_license_policy(
                    imported_code_disposition=LicenseDisposition.ALLOW
                )
            )
        )

    with pytest.raises(SoftwareFactoryError, match="cannot default to ALLOW"):
        _provenance().evaluate(
            _request(
                license_policy=_license_policy(
                    unknown_license_disposition=LicenseDisposition.ALLOW
                )
            )
        )

    with pytest.raises(SoftwareFactoryError, match="must not overlap"):
        _provenance().evaluate(
            _request(
                license_policy=_license_policy(
                    blocked_licenses=frozenset({"License-Allowed"})
                )
            )
        )


def test_model_provider_metadata_is_policy_gated_and_invocation_bound() -> None:
    with pytest.raises(SoftwareFactoryError, match="invocation does not match"):
        _provenance().evaluate(
            _request(model_metadata=_model_metadata(invocation_id="wrong-invocation"))
        )

    hidden_policy = _license_policy(model_provider_metadata_permitted=False)
    hidden_metadata = ModelProviderMetadata(disclosure_permitted=False)
    hidden = _provenance().evaluate(
        _request(
            license_policy=hidden_policy,
            model_metadata=hidden_metadata,
        )
    )
    assert hidden.model_provider_metadata.provider_id is None
    assert "MODEL_PROVIDER_METADATA_NOT_DISCLOSED_BY_POLICY" in hidden.risk_flags

    with pytest.raises(SoftwareFactoryError, match="must remain undisclosed"):
        _provenance().evaluate(
            _request(
                license_policy=hidden_policy,
                model_metadata=_model_metadata(),
            )
        )


def test_stale_or_tampered_sf12_review_is_rejected() -> None:
    request = _request()
    tampered = replace(request.review_record, record_sha256="7" * 64)
    with pytest.raises(SoftwareFactoryError, match="independent-review record is stale or tampered"):
        _provenance().evaluate(replace(request, review_record=tampered))


def test_nonapproved_sf12_review_cannot_enter_sf14() -> None:
    request = _request(
        include_dependency_governance=False,
        nonapproved_review=True,
    )
    with pytest.raises(SoftwareFactoryError, match="completed, approved SF-12"):
        _provenance().evaluate(request)


def test_generated_code_cannot_masquerade_as_imported_text() -> None:
    request = _request()
    generated = next(
        item for item in request.artifacts
        if item.kind is ProvenanceKind.GENERATED_CODE
    )
    tampered = replace(generated, code_text_imported=True)
    artifacts = tuple(
        tampered if item is generated else item for item in request.artifacts
    )
    with pytest.raises(SoftwareFactoryError, match="cannot be labeled as imported"):
        _provenance().evaluate(replace(request, artifacts=artifacts))


def test_provenance_record_is_deterministic_for_identical_evidence() -> None:
    request = _request()
    first = _provenance().evaluate(request)
    second = _provenance().evaluate(request)

    assert first == second
    assert first.record_sha256 == second.record_sha256
    assert tuple(item.evidence_sha256 for item in first.provenance_records) == tuple(
        item.evidence_sha256 for item in second.provenance_records
    )
