"""SF-16 build provenance lineage, runtime, and authority tests."""

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
from services.software_factory_build_provenance import (
    BuildArtifactInput,
    BuildDisposition,
    BuilderIdentity,
    BuildProvenanceRequest,
    SoftwareFactoryBuildProvenance,
)
from services.software_factory_dependencies import CommercialCompatibility
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
    IndependentReviewSubmission,
    ReviewDecision,
    SoftwareFactoryIndependentReview,
    SoftwareIndependentReviewRequest,
)
from services.software_factory_runtime import RuntimeEvidence, RuntimeStepResult
from services.software_factory_sbom import (
    SoftwareFactorySBOM,
    SoftwareSBOMDocument,
    SoftwareSBOMRequest,
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
CHANGESET_SHA = "b" * 64
AGENT_ID = "ilaios.agent.engineering.backend.v1"
VERIFIER_ID = "ilaios.agent.meta.independent-verifier.v1"
VALIDATOR_ID = "ilaios.validator.software-factory.v1"
CODE_REVIEWER = "ilaios.reviewer.code.independent.v1"
SECURITY_REVIEWER = "ilaios.reviewer.security.independent.v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
CHANGED_PATHS = ("services/example.py",)
RUNTIME_STAGES = (
    "prepare",
    "resolve_dependencies",
    "lint",
    "typecheck",
    "test",
    "build",
    "package",
    "smoke_test",
)


def _registry() -> SkillRegistry:
    return SkillRegistry(default_skills_root(REPO_ROOT))


def _goal() -> GoalSpec:
    return GoalSpec(
        "Produce source-bound build provenance.",
        ("build evidence is deterministic", "artifacts are content addressed"),
        RiskClass.HIGH,
        DataClass.INTERNAL,
        BudgetEnvelope(3, 600),
    )


def _proposal() -> PromotionProposal:
    return PromotionProposal(
        "proposal-sf16",
        "job-sf16",
        EvidenceBundle(
            "evidence-sf16",
            REPOSITORY_SHA,
            CHANGESET_SHA,
            "c" * 64,
            ValidationResult(True, ("pytest", "ruff", "mypy"), ()),
            "2026-08-14T11:40:00+00:00",
        ),
        True,
        False,
    )


def _execution() -> EngineeringAgentExecution:
    admission = AgentAdmissionEvidence(
        "invoke-sf16",
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
        pipeline_run_id="sf11-run-for-sf16",
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


def _review_bundle() -> tuple[SoftwareIndependentReviewRequest, object]:
    validation_request = _validation_request()
    report = SoftwareFactoryValidationPipeline().validate(validation_request)
    submissions = (
        IndependentReviewSubmission(
            skill_id="sf-code-review",
            skill_version="1.0.0",
            reviewer_id=CODE_REVIEWER,
            reviewed_subject_sha256=report.subject_sha256,
            validation_report_sha256=report.report_sha256,
            reviewed_paths=CHANGED_PATHS,
            findings=(),
            decision=ReviewDecision.APPROVE,
            evidence_references=("evidence://sf16/code-review",),
            read_only=True,
        ),
        IndependentReviewSubmission(
            skill_id="sf-security-review",
            skill_version="1.0.0",
            reviewer_id=SECURITY_REVIEWER,
            reviewed_subject_sha256=report.subject_sha256,
            validation_report_sha256=report.report_sha256,
            reviewed_paths=CHANGED_PATHS,
            findings=(),
            decision=ReviewDecision.APPROVE,
            evidence_references=("evidence://sf16/security-review",),
            read_only=True,
        ),
    )
    request = SoftwareIndependentReviewRequest(
        review_id="sf12-review-for-sf16",
        tenant_id=validation_request.tenant_id,
        task_id=validation_request.task_id,
        correlation_id=validation_request.correlation_id,
        policy_reference=validation_request.policy_reference,
        environment_id=validation_request.environment_id,
        changed_paths=CHANGED_PATHS,
        validation_request=validation_request,
        validation_report=report,
        submissions=submissions,
    )
    return request, SoftwareFactoryIndependentReview(_registry()).review(request)


def _provenance_policy(
    *,
    license_value: str,
    disposition: LicenseDisposition,
) -> LicenseProvenancePolicy:
    allowed: frozenset[str] = frozenset()
    review: frozenset[str] = frozenset()
    blocked: frozenset[str] = frozenset()
    if disposition is LicenseDisposition.ALLOW:
        allowed = frozenset({license_value})
    elif disposition is LicenseDisposition.REVIEW_REQUIRED:
        review = frozenset({license_value})
    else:
        blocked = frozenset({license_value})
    return LicenseProvenancePolicy(
        policy_id="policy/software-factory/license-provenance/sf16",
        allowed_licenses=allowed,
        review_licenses=review,
        blocked_licenses=blocked,
        model_provider_metadata_permitted=False,
    )


def _sbom_bundle(
    disposition: LicenseDisposition = LicenseDisposition.ALLOW,
) -> tuple[SoftwareSBOMRequest, SoftwareSBOMDocument]:
    review_request, review_record = _review_bundle()
    license_value = "ILAIOS-Proprietary"
    artifact = ArtifactProvenanceInput(
        artifact_reference="artifact://generated/services-example",
        kind=ProvenanceKind.GENERATED_CODE,
        usage=ProvenanceUsage.FIRST_PARTY_GENERATION,
        artifact_sha256="d" * 64,
        repository_paths=CHANGED_PATHS,
        source_reference="ilaios://software-factory/invoke-sf16",
        generated_by_ai=True,
        code_text_imported=False,
        license=license_value,
        license_evidence_reference="policy://ilaios/proprietary/v1",
        commercial_compatibility=CommercialCompatibility.COMPATIBLE,
        evidence_references=("evidence://sf16/generated-code",),
    )
    provenance_request = LicenseProvenanceRequest(
        provenance_id="sf14-provenance-for-sf16",
        intent="Bind reviewed source to license/IP provenance before build.",
        artifact_references=(artifact.artifact_reference,),
        review_request=review_request,
        review_record=review_record,  # type: ignore[arg-type]
        artifacts=(artifact,),
        policy=_provenance_policy(
            license_value=license_value,
            disposition=disposition,
        ),
        model_provider_metadata=ModelProviderMetadata(disclosure_permitted=False),
    )
    provenance_record = SoftwareFactoryLicenseProvenance(_registry()).evaluate(
        provenance_request
    )
    sbom_request = SoftwareSBOMRequest(
        sbom_id="sf15-sbom-for-sf16",
        document_name="ILAIOS SF-16 test SBOM",
        provenance_request=provenance_request,
        provenance_record=provenance_record,
    )
    return sbom_request, SoftwareFactorySBOM(_registry()).generate(sbom_request)


def _runtime_step(stage: str, index: int) -> RuntimeStepResult:
    return RuntimeStepResult(
        stage=stage,
        command=("test-runtime", stage),
        exit_code=0,
        stdout_sha256=f"{index + 1:064x}",
        stderr_sha256=f"{index + 101:064x}",
        passed=True,
    )


def _runtime(**overrides: object) -> RuntimeEvidence:
    values: dict[str, object] = {
        "adapter_id": "ilaios.runtime.python",
        "workspace_sha256": "e" * 64,
        "steps": tuple(
            _runtime_step(stage, index)
            for index, stage in enumerate(RUNTIME_STAGES)
        ),
        "passed": True,
    }
    values.update(overrides)
    return RuntimeEvidence(**values)  # type: ignore[arg-type]


def _builder(**overrides: object) -> BuilderIdentity:
    values: dict[str, object] = {
        "builder_id": "ilaios.builder.github-actions.v1",
        "workflow_id": "required-ci-gate/build",
        "workflow_run_id": "31796000000",
        "runner_environment": "github-hosted-ubuntu-ephemeral",
        "source_checkout_read_only": True,
        "ephemeral": True,
        "evidence_reference": "evidence://sf16/builder/31796000000",
    }
    values.update(overrides)
    return BuilderIdentity(**values)  # type: ignore[arg-type]


def _artifacts() -> tuple[BuildArtifactInput, ...]:
    return (
        BuildArtifactInput(
            artifact_reference="artifact://build/ilaios-wheel",
            relative_path="dist/ilaios_test.whl",
            artifact_sha256="f" * 64,
            size_bytes=4096,
            media_type="application/zip",
            producing_stage="build",
        ),
        BuildArtifactInput(
            artifact_reference="artifact://package/ilaios-sdist",
            relative_path="dist/ilaios-test.tar.gz",
            artifact_sha256="1" * 64,
            size_bytes=8192,
            media_type="application/gzip",
            producing_stage="package",
        ),
    )


def _request(
    *,
    disposition: LicenseDisposition = LicenseDisposition.ALLOW,
    runtime: RuntimeEvidence | None = None,
    builder: BuilderIdentity | None = None,
    artifacts: tuple[BuildArtifactInput, ...] | None = None,
) -> BuildProvenanceRequest:
    sbom_request, sbom_document = _sbom_bundle(disposition)
    return BuildProvenanceRequest(
        build_id="sf16-build-1",
        sbom_request=sbom_request,
        sbom_document=sbom_document,
        runtime_evidence=runtime or _runtime(),
        builder=builder or _builder(),
        artifacts=artifacts or _artifacts(),
    )


def _build() -> SoftwareFactoryBuildProvenance:
    return SoftwareFactoryBuildProvenance(_registry())


def test_build_provenance_binds_sbom_runtime_builder_and_artifacts() -> None:
    record = _build().generate(_request())

    assert record.skill_id == "sf-build"
    assert record.skill_version == "1.0.0"
    assert record.repository_base_sha == REPOSITORY_SHA
    assert record.changeset_sha256 == CHANGESET_SHA
    assert record.runtime_adapter_id == "ilaios.runtime.python"
    assert record.disposition is BuildDisposition.ALLOW
    assert record.build_succeeded is True
    assert record.build_provenance_bound is True
    assert record.signing_attestation_bound is False
    assert record.release_complete is False
    assert record.acceptance_authorized is False
    assert record.promotion_authorized is False
    assert record.deployment_authorized is False
    assert record.production_applied is False
    assert record.subject_mutated is False
    assert len(record.runtime_evidence_sha256) == 64
    assert len(record.builder_sha256) == 64
    assert len(record.record_sha256) == 64
    assert len(record.artifacts) == 2
    assert all(item.repository_base_sha == REPOSITORY_SHA for item in record.artifacts)
    assert all(item.sbom_document_sha256 == record.sbom_document_sha256 for item in record.artifacts)


def test_build_provenance_is_deterministic() -> None:
    request = _request()
    first = _build().generate(request)
    second = _build().generate(request)

    assert first == second
    assert first.record_sha256 == second.record_sha256


def test_stale_or_tampered_sbom_is_rejected() -> None:
    request = _request()
    tampered = replace(request.sbom_document, document_name="tampered")
    with pytest.raises(SoftwareFactoryError, match="SBOM document is stale"):
        _build().generate(replace(request, sbom_document=tampered))


def test_runtime_lifecycle_order_is_exact_and_fail_closed() -> None:
    request = _request()
    steps = request.runtime_evidence.steps
    reordered = steps[:5] + (steps[6], steps[5]) + steps[7:]
    with pytest.raises(SoftwareFactoryError, match="exact canonical SF-6 lifecycle"):
        _build().generate(
            replace(
                request,
                runtime_evidence=replace(request.runtime_evidence, steps=reordered),
            )
        )


def test_failed_runtime_step_is_rejected() -> None:
    request = _request()
    steps = list(request.runtime_evidence.steps)
    steps[5] = replace(steps[5], exit_code=1, passed=False)
    runtime = replace(request.runtime_evidence, steps=tuple(steps), passed=False)
    with pytest.raises(SoftwareFactoryError, match="passing canonical runtime evidence"):
        _build().generate(replace(request, runtime_evidence=runtime))


def test_runtime_adapter_must_be_allowed_by_canonical_sf_build_skill() -> None:
    request = _request()
    runtime = replace(request.runtime_evidence, adapter_id="ilaios.runtime.unknown")
    with pytest.raises(SoftwareFactoryError, match="outside sf-build allowlist"):
        _build().generate(replace(request, runtime_evidence=runtime))


def test_builder_must_be_ephemeral_and_source_checkout_read_only() -> None:
    request = _request()
    with pytest.raises(SoftwareFactoryError, match="read-only source checkout"):
        _build().generate(
            replace(
                request,
                builder=replace(request.builder, source_checkout_read_only=False),
            )
        )
    with pytest.raises(SoftwareFactoryError, match="ephemeral builder"):
        _build().generate(
            replace(request, builder=replace(request.builder, ephemeral=False))
        )


def test_build_artifacts_must_be_content_addressed_and_from_build_or_package() -> None:
    request = _request()
    bad_hash = replace(request.artifacts[0], artifact_sha256="not-a-sha")
    with pytest.raises(SoftwareFactoryError, match="artifact SHA-256"):
        _build().generate(replace(request, artifacts=(bad_hash, request.artifacts[1])))

    bad_stage = replace(request.artifacts[0], producing_stage="test")
    with pytest.raises(SoftwareFactoryError, match="build or package stage"):
        _build().generate(replace(request, artifacts=(bad_stage, request.artifacts[1])))


def test_build_artifact_cannot_overwrite_reviewed_source_path() -> None:
    request = _request()
    artifact = replace(request.artifacts[0], relative_path="services/example.py")
    with pytest.raises(SoftwareFactoryError, match="cannot overwrite reviewed source"):
        _build().generate(replace(request, artifacts=(artifact, request.artifacts[1])))


def test_review_required_upstream_is_preserved_without_downstream_authority() -> None:
    record = _build().generate(_request(disposition=LicenseDisposition.REVIEW_REQUIRED))

    assert record.disposition is BuildDisposition.REVIEW_REQUIRED
    assert "UPSTREAM_SUPPLY_CHAIN_REVIEW_REQUIRED" in record.risk_flags
    assert record.promotion_authorized is False
    assert record.deployment_authorized is False


def test_upstream_block_cannot_be_built_through_sf16() -> None:
    with pytest.raises(SoftwareFactoryError, match="upstream BLOCK"):
        _build().generate(_request(disposition=LicenseDisposition.BLOCK))


def test_sf16_explicitly_does_not_claim_sf17_signing_or_attestation() -> None:
    record = _build().generate(_request())

    assert record.signing_attestation_bound is False
    assert record.release_complete is False
