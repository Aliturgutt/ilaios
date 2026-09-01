"""SF-17 signing/attestation lineage, trust, and authority tests."""

from __future__ import annotations

import base64
import hashlib
import json
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
from services.software_factory_signing_attestation import (
    AttestationDisposition,
    SignatureEnvelope,
    SignatureVerification,
    SigningAttestationPolicy,
    SigningAttestationRequest,
    SigningTarget,
    SoftwareFactorySigningAttestation,
    TrustedSigningKey,
    UnavailableSigningBoundary,
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
        "Produce source-bound signed build attestation.",
        ("build provenance is exact", "signature verification is fail closed"),
        RiskClass.HIGH,
        DataClass.INTERNAL,
        BudgetEnvelope(3, 600),
    )


def _proposal() -> PromotionProposal:
    return PromotionProposal(
        "proposal-sf17",
        "job-sf17",
        EvidenceBundle(
            "evidence-sf17",
            REPOSITORY_SHA,
            CHANGESET_SHA,
            "c" * 64,
            ValidationResult(True, ("pytest", "ruff", "mypy"), ()),
            "2026-08-14T12:15:00+00:00",
        ),
        True,
        False,
    )


def _execution() -> EngineeringAgentExecution:
    admission = AgentAdmissionEvidence(
        "invoke-sf17",
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
        pipeline_run_id="sf11-run-for-sf17",
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
            evidence_references=("evidence://sf17/code-review",),
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
            evidence_references=("evidence://sf17/security-review",),
            read_only=True,
        ),
    )
    request = SoftwareIndependentReviewRequest(
        review_id="sf12-review-for-sf17",
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
        policy_id="policy/software-factory/license-provenance/sf17",
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
        source_reference="ilaios://software-factory/invoke-sf17",
        generated_by_ai=True,
        code_text_imported=False,
        license=license_value,
        license_evidence_reference="policy://ilaios/proprietary/v1",
        commercial_compatibility=CommercialCompatibility.COMPATIBLE,
        evidence_references=("evidence://sf17/generated-code",),
    )
    provenance_request = LicenseProvenanceRequest(
        provenance_id="sf14-provenance-for-sf17",
        intent="Bind reviewed source to license/IP provenance before signing.",
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
        sbom_id="sf15-sbom-for-sf17",
        document_name="ILAIOS SF-17 test SBOM",
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


def _runtime() -> RuntimeEvidence:
    return RuntimeEvidence(
        adapter_id="ilaios.runtime.python",
        workspace_sha256="e" * 64,
        steps=tuple(
            _runtime_step(stage, index)
            for index, stage in enumerate(RUNTIME_STAGES)
        ),
        passed=True,
    )


def _builder() -> BuilderIdentity:
    return BuilderIdentity(
        builder_id="ilaios.builder.github-actions.v1",
        workflow_id="required-ci-gate/build",
        workflow_run_id="31798218018",
        runner_environment="github-hosted-ubuntu-ephemeral",
        source_checkout_read_only=True,
        ephemeral=True,
        evidence_reference="evidence://sf17/builder/31798218018",
    )


def _artifacts() -> tuple[BuildArtifactInput, ...]:
    return (
        BuildArtifactInput(
            artifact_reference="artifact://build/ilaios-wheel",
            relative_path="dist/ilaios-test.whl",
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


def _build_request(
    disposition: LicenseDisposition = LicenseDisposition.ALLOW,
) -> BuildProvenanceRequest:
    sbom_request, sbom_document = _sbom_bundle(disposition)
    return BuildProvenanceRequest(
        build_id="sf16-build-for-sf17",
        sbom_request=sbom_request,
        sbom_document=sbom_document,
        runtime_evidence=_runtime(),
        builder=_builder(),
        artifacts=_artifacts(),
    )


def _trusted_key(**overrides: object) -> TrustedSigningKey:
    values: dict[str, object] = {
        "signer_id": "ilaios.signer.release.v1",
        "key_id": "ilaios-software-factory-release",
        "key_version": "1",
        "algorithm": "ed25519",
        "public_key_sha256": "2" * 64,
        "hardware_backed": True,
        "active": True,
        "trust_root_reference": "trust://ilaios/signing/release-key-v1",
    }
    values.update(overrides)
    return TrustedSigningKey(**values)  # type: ignore[arg-type]


def _policy(**overrides: object) -> SigningAttestationPolicy:
    values: dict[str, object] = {
        "policy_id": "policy/software-factory/signing-attestation/v1",
        "trusted_keys": (_trusted_key(),),
        "require_hardware_backed": True,
        "max_signature_bytes": 8192,
    }
    values.update(overrides)
    return SigningAttestationPolicy(**values)  # type: ignore[arg-type]


class DeterministicSigningBoundary:
    """Test-only boundary emulating a trusted external signing/verifier service."""

    def __init__(
        self,
        *,
        envelope_statement_sha256: str | None = None,
        invalid_base64: bool = False,
        verified: bool = True,
        verification_statement_sha256: str | None = None,
        verification_signature_sha256: str | None = None,
        verification_hardware_backed: bool | None = None,
        verification_key_active: bool = True,
    ) -> None:
        self._envelope_statement_sha256 = envelope_statement_sha256
        self._invalid_base64 = invalid_base64
        self._verified = verified
        self._verification_statement_sha256 = verification_statement_sha256
        self._verification_signature_sha256 = verification_signature_sha256
        self._verification_hardware_backed = verification_hardware_backed
        self._verification_key_active = verification_key_active

    @staticmethod
    def _statement_sha256(statement: bytes) -> str:
        parsed: object = json.loads(statement.decode("utf-8"))
        return canonical_sha256(parsed)

    @staticmethod
    def _signature_bytes(statement: bytes, key: TrustedSigningKey) -> bytes:
        seed = statement + key.public_key_sha256.encode("ascii")
        return hashlib.sha256(seed).digest() + hashlib.sha256(b"sf17" + seed).digest()

    def sign(
        self,
        statement: bytes,
        key: TrustedSigningKey,
        policy: SigningAttestationPolicy,
    ) -> SignatureEnvelope:
        del policy
        statement_sha256 = self._statement_sha256(statement)
        signature = self._signature_bytes(statement, key)
        encoded = (
            "%%%invalid%%%"
            if self._invalid_base64
            else base64.b64encode(signature).decode("ascii")
        )
        return SignatureEnvelope(
            signer_id=key.signer_id,
            key_id=key.key_id,
            key_version=key.key_version,
            algorithm=key.algorithm,
            public_key_sha256=key.public_key_sha256,
            statement_sha256=(
                self._envelope_statement_sha256 or statement_sha256
            ),
            signature_base64=encoded,
            signing_evidence_reference="evidence://sf17/signing-event/1",
        )

    def verify(
        self,
        statement: bytes,
        envelope: SignatureEnvelope,
        key: TrustedSigningKey,
        policy: SigningAttestationPolicy,
    ) -> SignatureVerification:
        statement_sha256 = self._statement_sha256(statement)
        signature = base64.b64decode(envelope.signature_base64, validate=True)
        signature_sha256 = canonical_sha256(signature.hex())
        return SignatureVerification(
            verified=self._verified,
            signer_id=key.signer_id,
            key_id=key.key_id,
            key_version=key.key_version,
            algorithm=key.algorithm,
            public_key_sha256=key.public_key_sha256,
            statement_sha256=(
                self._verification_statement_sha256 or statement_sha256
            ),
            signature_sha256=(
                self._verification_signature_sha256 or signature_sha256
            ),
            trust_policy_id=policy.policy_id,
            hardware_backed=(
                key.hardware_backed
                if self._verification_hardware_backed is None
                else self._verification_hardware_backed
            ),
            key_active=self._verification_key_active,
            verification_reference="evidence://sf17/verification/1",
        )


def _request(
    *,
    disposition: LicenseDisposition = LicenseDisposition.ALLOW,
    policy: SigningAttestationPolicy | None = None,
    target: SigningTarget | None = None,
) -> SigningAttestationRequest:
    build_request = _build_request(disposition)
    build_record = SoftwareFactoryBuildProvenance(_registry()).generate(build_request)
    return SigningAttestationRequest(
        attestation_id="sf17-attestation-1",
        build_request=build_request,
        build_record=build_record,
        signing_target=target
        or SigningTarget(
            signer_id="ilaios.signer.release.v1",
            key_id="ilaios-software-factory-release",
            key_version="1",
        ),
        policy=policy or _policy(),
    )


def _attestor(
    boundary: DeterministicSigningBoundary | UnavailableSigningBoundary | None = None,
) -> SoftwareFactorySigningAttestation:
    return SoftwareFactorySigningAttestation(
        _registry(), boundary or DeterministicSigningBoundary()
    )


def test_signed_attestation_binds_exact_sf16_build_and_artifact_subjects() -> None:
    record = _attestor().attest(_request())

    assert record.disposition is AttestationDisposition.ALLOW
    assert record.repository_base_sha == REPOSITORY_SHA
    assert record.changeset_sha256 == CHANGESET_SHA
    assert record.signed is True
    assert record.signature_verified is True
    assert record.build_provenance_bound is True
    assert record.signing_attestation_bound is True
    assert record.release_complete is False
    assert record.publication_authorized is False
    assert record.acceptance_authorized is False
    assert record.promotion_authorized is False
    assert record.deployment_authorized is False
    assert record.production_applied is False
    assert record.subject_mutated is False
    assert len(record.subjects) == 2
    assert {item.artifact_sha256 for item in record.subjects} == {"f" * 64, "1" * 64}
    assert record.statement.build_provenance_record_sha256 == record.build_provenance_record_sha256
    assert len(record.statement_sha256) == 64
    assert len(record.signature_sha256) == 64
    assert len(record.verification_sha256) == 64
    assert len(record.trust_policy_sha256) == 64
    assert len(record.record_sha256) == 64
    assert not hasattr(record.signature, "private_key")


def test_signed_attestation_is_deterministic_with_deterministic_boundary() -> None:
    request = _request()
    first = _attestor().attest(request)
    second = _attestor().attest(request)

    assert first == second
    assert first.record_sha256 == second.record_sha256
    assert first.statement_sha256 == second.statement_sha256
    assert first.signature_sha256 == second.signature_sha256


def test_stale_or_tampered_sf16_build_record_is_rejected() -> None:
    request = _request()
    tampered = replace(request.build_record, build_id="tampered-build")
    with pytest.raises(SoftwareFactoryError, match="build provenance record is stale"):
        _attestor().attest(replace(request, build_record=tampered))


def test_signing_target_must_be_uniquely_trusted_and_active() -> None:
    untrusted = SigningTarget("unknown", "unknown", "1")
    with pytest.raises(SoftwareFactoryError, match="not uniquely trusted"):
        _attestor().attest(_request(target=untrusted))

    inactive_policy = _policy(trusted_keys=(_trusted_key(active=False),))
    with pytest.raises(SoftwareFactoryError, match="inactive or revoked"):
        _attestor().attest(_request(policy=inactive_policy))


def test_hardware_backed_key_policy_is_fail_closed() -> None:
    software_key_policy = _policy(trusted_keys=(_trusted_key(hardware_backed=False),))
    with pytest.raises(SoftwareFactoryError, match="hardware-backed signing key"):
        _attestor().attest(_request(policy=software_key_policy))

    boundary = DeterministicSigningBoundary(verification_hardware_backed=False)
    with pytest.raises(SoftwareFactoryError, match="hardware-backed key boundary"):
        _attestor(boundary).attest(_request())


def test_duplicate_or_unsupported_trust_policy_is_rejected() -> None:
    key = _trusted_key()
    duplicate_policy = _policy(trusted_keys=(key, key))
    with pytest.raises(SoftwareFactoryError, match="duplicate key identity"):
        _attestor().attest(_request(policy=duplicate_policy))

    unsupported_policy = _policy(
        trusted_keys=(_trusted_key(algorithm="unknown-signature"),)
    )
    with pytest.raises(SoftwareFactoryError, match="algorithm is unsupported"):
        _attestor().attest(_request(policy=unsupported_policy))


def test_unavailable_signing_boundary_fails_closed() -> None:
    with pytest.raises(SoftwareFactoryError, match="secure signing boundary is unavailable"):
        _attestor(UnavailableSigningBoundary()).attest(_request())


def test_signature_envelope_must_bind_exact_attestation_statement() -> None:
    boundary = DeterministicSigningBoundary(envelope_statement_sha256="9" * 64)
    with pytest.raises(SoftwareFactoryError, match="statement_sha256 binding mismatch"):
        _attestor(boundary).attest(_request())


def test_signature_must_be_valid_bounded_base64() -> None:
    invalid = DeterministicSigningBoundary(invalid_base64=True)
    with pytest.raises(SoftwareFactoryError, match="not valid base64"):
        _attestor(invalid).attest(_request())

    tiny_bound = _policy(max_signature_bytes=32)
    with pytest.raises(SoftwareFactoryError, match="exceeds policy byte bound"):
        _attestor().attest(_request(policy=tiny_bound))


def test_failed_signature_verification_is_rejected() -> None:
    boundary = DeterministicSigningBoundary(verified=False)
    with pytest.raises(SoftwareFactoryError, match="signature verification failed"):
        _attestor(boundary).attest(_request())


def test_verification_must_bind_exact_statement_and_signature() -> None:
    wrong_statement = DeterministicSigningBoundary(
        verification_statement_sha256="8" * 64
    )
    with pytest.raises(SoftwareFactoryError, match="statement_sha256 binding mismatch"):
        _attestor(wrong_statement).attest(_request())

    wrong_signature = DeterministicSigningBoundary(
        verification_signature_sha256="7" * 64
    )
    with pytest.raises(SoftwareFactoryError, match="signature_sha256 binding mismatch"):
        _attestor(wrong_signature).attest(_request())


def test_verification_rejects_inactive_or_revoked_key_report() -> None:
    boundary = DeterministicSigningBoundary(verification_key_active=False)
    with pytest.raises(SoftwareFactoryError, match="inactive/revoked key"):
        _attestor(boundary).attest(_request())


def test_review_required_build_is_signed_without_becoming_release_authority() -> None:
    record = _attestor().attest(_request(disposition=LicenseDisposition.REVIEW_REQUIRED))

    assert record.disposition is AttestationDisposition.REVIEW_REQUIRED
    assert "UPSTREAM_BUILD_REVIEW_REQUIRED" in record.risk_flags
    assert record.signature_verified is True
    assert record.release_complete is False
    assert record.publication_authorized is False
    assert record.promotion_authorized is False
    assert record.deployment_authorized is False


def test_signing_and_verification_evidence_are_retained() -> None:
    record = _attestor().attest(_request())

    assert "trust://ilaios/signing/release-key-v1" in record.evidence_references
    assert "evidence://sf17/signing-event/1" in record.evidence_references
    assert "evidence://sf17/verification/1" in record.evidence_references
