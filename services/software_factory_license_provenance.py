"""SF-14 license/IP provenance over reviewed Software Factory evidence.

This gate operationalizes the canonical first-party ``sf-license-provenance``
skill. It binds generated code, third-party dependencies/assets, and external
references to exact SF-12/SF-13 evidence while making no legal or IP-clearance
claim and granting no downstream authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from services.software_factory import SoftwareFactoryError
from services.software_factory_dependencies import (
    CommercialCompatibility,
    DependencyDisposition,
    DependencyEvidence,
    DependencyGovernanceRecord,
    DependencyGovernanceRequest,
    SoftwareFactoryDependencyGovernance,
)
from services.software_factory_review import (
    IndependentReviewRecord,
    ReviewDecision,
    SoftwareFactoryIndependentReview,
    SoftwareIndependentReviewRequest,
)
from services.software_factory_skills import SkillPackage, SkillRegistry
from src.core.validation_pipeline import canonical_sha256

LICENSE_PROVENANCE_SKILL_ID = "sf-license-provenance"
LICENSE_PROVENANCE_CONTRACT_VERSION = "1.0.0"
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DEPENDENCY_FILENAMES = frozenset(
    {
        "package.json",
        "package-lock.json",
        "npm-shrinkwrap.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "pyproject.toml",
        "poetry.lock",
        "uv.lock",
        "Pipfile",
        "Pipfile.lock",
        "pubspec.yaml",
        "pubspec.lock",
        "Cargo.toml",
        "Cargo.lock",
        "go.mod",
        "go.sum",
        "composer.json",
        "composer.lock",
        "Gemfile",
        "Gemfile.lock",
    }
)


class LicenseDisposition(str, Enum):
    ALLOW = "ALLOW"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCK = "BLOCK"


class ProvenanceKind(str, Enum):
    GENERATED_CODE = "GENERATED_CODE"
    THIRD_PARTY_DEPENDENCY = "THIRD_PARTY_DEPENDENCY"
    THIRD_PARTY_ASSET = "THIRD_PARTY_ASSET"
    EXTERNAL_REFERENCE = "EXTERNAL_REFERENCE"


class ProvenanceUsage(str, Enum):
    FIRST_PARTY_GENERATION = "FIRST_PARTY_GENERATION"
    DEPENDENCY_INCLUSION = "DEPENDENCY_INCLUSION"
    ASSET_IMPORT = "ASSET_IMPORT"
    CONCEPT_REFERENCE = "CONCEPT_REFERENCE"
    CODE_TEXT_IMPORT = "CODE_TEXT_IMPORT"


@dataclass(frozen=True, slots=True)
class ModelProviderMetadata:
    """Provider/model trace disclosed only when policy permits it."""

    disclosure_permitted: bool
    provider_id: str | None = None
    model_id: str | None = None
    invocation_id: str | None = None
    evidence_reference: str | None = None


@dataclass(frozen=True, slots=True)
class LicenseProvenancePolicy:
    """Explicit policy inputs; this gate does not invent legal classifications."""

    policy_id: str
    allowed_licenses: frozenset[str]
    review_licenses: frozenset[str]
    blocked_licenses: frozenset[str]
    unknown_license_disposition: LicenseDisposition = LicenseDisposition.REVIEW_REQUIRED
    unknown_commercial_disposition: LicenseDisposition = LicenseDisposition.REVIEW_REQUIRED
    imported_code_disposition: LicenseDisposition = LicenseDisposition.REVIEW_REQUIRED
    model_provider_metadata_permitted: bool = False


@dataclass(frozen=True, slots=True)
class ArtifactProvenanceInput:
    artifact_reference: str
    kind: ProvenanceKind
    usage: ProvenanceUsage
    artifact_sha256: str
    repository_paths: tuple[str, ...]
    source_reference: str
    generated_by_ai: bool
    code_text_imported: bool
    license: str | None
    license_evidence_reference: str | None
    commercial_compatibility: CommercialCompatibility
    evidence_references: tuple[str, ...]
    dependency_package: str | None = None
    dependency_version: str | None = None
    dependency_source: str | None = None
    upstream_dependency_evidence_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class ArtifactProvenanceEvidence:
    artifact_reference: str
    kind: ProvenanceKind
    usage: ProvenanceUsage
    artifact_sha256: str
    repository_paths: tuple[str, ...]
    source_reference: str
    generated_by_ai: bool
    code_text_imported: bool
    license: str | None
    license_evidence_reference: str | None
    commercial_compatibility: CommercialCompatibility
    dependency_package: str | None
    dependency_version: str | None
    dependency_source: str | None
    upstream_dependency_evidence_sha256: str | None
    disposition: LicenseDisposition
    policy_reasons: tuple[str, ...]
    risk_flags: tuple[str, ...]
    evidence_references: tuple[str, ...]
    ip_risk_clearance_claimed: bool
    evidence_sha256: str


@dataclass(frozen=True, slots=True)
class LicenseProvenanceRequest:
    provenance_id: str
    intent: str
    artifact_references: tuple[str, ...]
    review_request: SoftwareIndependentReviewRequest
    review_record: IndependentReviewRecord
    artifacts: tuple[ArtifactProvenanceInput, ...]
    policy: LicenseProvenancePolicy
    model_provider_metadata: ModelProviderMetadata
    dependency_governance_request: DependencyGovernanceRequest | None = None
    dependency_governance_record: DependencyGovernanceRecord | None = None


@dataclass(frozen=True, slots=True)
class LicenseProvenanceRecord:
    provenance_id: str
    contract_version: str
    skill_id: str
    skill_version: str
    policy_id: str
    policy_sha256: str
    tenant_id: str
    task_id: str
    correlation_id: str
    factory_job_id: str
    repository_base_sha: str
    changeset_sha256: str
    engineering_agent_id: str
    engineering_invocation_id: str
    reviewer_ids: tuple[str, ...]
    review_record_sha256: str
    validation_report_sha256: str
    dependency_governance_record_sha256: str | None
    model_provider_metadata: ModelProviderMetadata
    artifact_references: tuple[str, ...]
    provenance_records: tuple[ArtifactProvenanceEvidence, ...]
    license_disposition: LicenseDisposition
    risk_flags: tuple[str, ...]
    evidence_references: tuple[str, ...]
    independent_review_required: bool
    ip_risk_clearance_claimed: bool
    acceptance_authorized: bool
    promotion_authorized: bool
    deployment_authorized: bool
    production_applied: bool
    subject_mutated: bool
    record_sha256: str


class SoftwareFactoryLicenseProvenance:
    """Fail-closed SF-14 traceability gate with no legal-certification authority."""

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    def evaluate(self, request: LicenseProvenanceRequest) -> LicenseProvenanceRecord:
        package = self._validate_skill_contract()
        review = self._validate_review_binding(request)
        policy = self._validate_policy(request.policy)
        references = _normalize_references(request.artifact_references)
        dependency_record = self._validate_dependency_binding(request, review)

        validation_request = request.review_request.validation_request
        proposal = validation_request.software_proposal
        execution = validation_request.engineering_execution
        repository_sha = proposal.evidence.repository_sha
        changeset_sha256 = proposal.evidence.changeset_sha256
        if _SHA1.fullmatch(repository_sha) is None:
            raise SoftwareFactoryError("SF-14 requires a lowercase repository base SHA")
        if _SHA256.fullmatch(changeset_sha256) is None:
            raise SoftwareFactoryError("SF-14 requires a valid ChangeSet SHA-256")

        model_metadata = _validate_model_metadata(
            request.model_provider_metadata,
            policy=policy,
            expected_invocation_id=execution.admission.invocation_id,
        )
        provenance_records = self._validate_artifacts(
            request.artifacts,
            references=references,
            reviewed_paths=review.changed_paths,
            policy=policy,
            dependency_record=dependency_record,
        )
        _validate_reviewed_path_coverage(provenance_records, review.changed_paths)
        _validate_dependency_inventory_coverage(provenance_records, dependency_record)

        dispositions = tuple(record.disposition for record in provenance_records)
        if dependency_record is not None:
            dispositions += (_map_dependency_disposition(dependency_record.disposition),)
        disposition = _aggregate_disposition(dispositions)
        risk_flags = set(
            flag for record in provenance_records for flag in record.risk_flags
        )
        if not model_metadata.disclosure_permitted:
            risk_flags.add("MODEL_PROVIDER_METADATA_NOT_DISCLOSED_BY_POLICY")
        normalized_risk_flags = tuple(sorted(risk_flags))
        evidence_references = _aggregate_evidence_references(
            review,
            dependency_record,
            model_metadata,
            provenance_records,
        )
        policy_sha256 = canonical_sha256(_policy_material(policy))
        material = _record_material(
            request=request,
            package=package,
            review=review,
            repository_sha=repository_sha,
            changeset_sha256=changeset_sha256,
            dependency_record=dependency_record,
            model_metadata=model_metadata,
            references=references,
            provenance_records=provenance_records,
            disposition=disposition,
            risk_flags=normalized_risk_flags,
            evidence_references=evidence_references,
            policy_sha256=policy_sha256,
        )
        return LicenseProvenanceRecord(
            provenance_id=request.provenance_id,
            contract_version=LICENSE_PROVENANCE_CONTRACT_VERSION,
            skill_id=package.manifest.skill_id,
            skill_version=package.manifest.version,
            policy_id=policy.policy_id,
            policy_sha256=policy_sha256,
            tenant_id=review.tenant_id,
            task_id=review.task_id,
            correlation_id=review.correlation_id,
            factory_job_id=proposal.job_id,
            repository_base_sha=repository_sha,
            changeset_sha256=changeset_sha256,
            engineering_agent_id=execution.admission.agent_id,
            engineering_invocation_id=execution.admission.invocation_id,
            reviewer_ids=review.reviewers,
            review_record_sha256=review.record_sha256,
            validation_report_sha256=review.validation_report_sha256,
            dependency_governance_record_sha256=(
                dependency_record.record_sha256 if dependency_record is not None else None
            ),
            model_provider_metadata=model_metadata,
            artifact_references=references,
            provenance_records=provenance_records,
            license_disposition=disposition,
            risk_flags=normalized_risk_flags,
            evidence_references=evidence_references,
            independent_review_required=package.manifest.independent_review_required,
            ip_risk_clearance_claimed=False,
            acceptance_authorized=False,
            promotion_authorized=False,
            deployment_authorized=False,
            production_applied=False,
            subject_mutated=False,
            record_sha256=canonical_sha256(material),
        )

    def _validate_skill_contract(self) -> SkillPackage:
        package = self._registry.resolve(LICENSE_PROVENANCE_SKILL_ID)
        manifest = package.manifest
        if manifest.domain != "supply-chain-commercial":
            raise SoftwareFactoryError(
                "SF-14 license/provenance skill is outside canonical supply-chain-commercial domain"
            )
        if not manifest.independent_review_required:
            raise SoftwareFactoryError(
                "SF-14 license/provenance skill lost its independent-review requirement"
            )
        required_inputs = {"intent", "artifact_references"}
        if not required_inputs.issubset(manifest.inputs):
            raise SoftwareFactoryError(
                "SF-14 license/provenance skill lost canonical provenance inputs"
            )
        required_outputs = {
            "provenance_records",
            "license_disposition",
            "risk_flags",
            "evidence_references",
        }
        if not required_outputs.issubset(manifest.outputs):
            raise SoftwareFactoryError(
                "SF-14 license/provenance skill lost canonical provenance outputs"
            )
        required_evidence = {"provenance", "policy_decision", "reviewer"}
        if not required_evidence.issubset(manifest.emitted_evidence):
            raise SoftwareFactoryError(
                "SF-14 license/provenance skill lost canonical evidence classes"
            )
        return package

    def _validate_review_binding(
        self, request: LicenseProvenanceRequest
    ) -> IndependentReviewRecord:
        if not _trimmed(request.provenance_id):
            raise SoftwareFactoryError("SF-14 provenance_id must be non-blank and trimmed")
        if not _trimmed(request.intent):
            raise SoftwareFactoryError("SF-14 intent must be non-blank and trimmed")
        regenerated = SoftwareFactoryIndependentReview(self._registry).review(
            request.review_request
        )
        if regenerated != request.review_record:
            raise SoftwareFactoryError("SF-14 independent-review record is stale or tampered")
        if regenerated.decision is not ReviewDecision.APPROVE or not regenerated.review_complete:
            raise SoftwareFactoryError(
                "SF-14 requires a completed, approved SF-12 independent review"
            )
        if (
            regenerated.acceptance_authorized
            or regenerated.promotion_authorized
            or regenerated.production_applied
        ):
            raise SoftwareFactoryError(
                "SF-14 cannot consume SF-12 evidence with downstream authority"
            )
        return regenerated

    def _validate_dependency_binding(
        self,
        request: LicenseProvenanceRequest,
        review: IndependentReviewRecord,
    ) -> DependencyGovernanceRecord | None:
        dependency_paths = tuple(
            sorted(path for path in review.changed_paths if _is_dependency_path(path))
        )
        dep_request = request.dependency_governance_request
        dep_record = request.dependency_governance_record
        if (dep_request is None) != (dep_record is None):
            raise SoftwareFactoryError(
                "SF-14 dependency governance request/record must be supplied together"
            )
        if dependency_paths and dep_request is None:
            raise SoftwareFactoryError(
                "SF-14 requires exact SF-13 evidence for reviewed dependency paths"
            )
        if not dependency_paths and dep_request is not None:
            raise SoftwareFactoryError(
                "SF-14 received SF-13 evidence without reviewed dependency paths"
            )
        if dep_request is None or dep_record is None:
            return None
        if (
            dep_request.review_request != request.review_request
            or dep_request.review_record != request.review_record
        ):
            raise SoftwareFactoryError("SF-14 SF-13 lineage does not match SF-12 review")
        regenerated = SoftwareFactoryDependencyGovernance(self._registry).evaluate(dep_request)
        if regenerated != dep_record:
            raise SoftwareFactoryError("SF-14 dependency-governance record is stale or tampered")
        if regenerated.dependency_paths != dependency_paths:
            raise SoftwareFactoryError("SF-14 SF-13 dependency-path scope mismatch")
        if regenerated.review_record_sha256 != review.record_sha256:
            raise SoftwareFactoryError("SF-14 SF-13 review digest mismatch")
        if (
            regenerated.acceptance_authorized
            or regenerated.promotion_authorized
            or regenerated.deployment_authorized
            or regenerated.production_applied
            or regenerated.subject_mutated
        ):
            raise SoftwareFactoryError(
                "SF-14 cannot consume SF-13 evidence with downstream authority"
            )
        return regenerated

    @staticmethod
    def _validate_policy(policy: LicenseProvenancePolicy) -> LicenseProvenancePolicy:
        if not _trimmed(policy.policy_id):
            raise SoftwareFactoryError("SF-14 provenance policy identity is required")
        license_sets = (
            policy.allowed_licenses,
            policy.review_licenses,
            policy.blocked_licenses,
        )
        if any(any(not _trimmed(item) for item in values) for values in license_sets):
            raise SoftwareFactoryError(
                "SF-14 license policy entries must be non-blank and trimmed"
            )
        if (
            policy.allowed_licenses & policy.review_licenses
            or policy.allowed_licenses & policy.blocked_licenses
            or policy.review_licenses & policy.blocked_licenses
        ):
            raise SoftwareFactoryError("SF-14 license policy sets must not overlap")
        if (
            policy.unknown_license_disposition is LicenseDisposition.ALLOW
            or policy.unknown_commercial_disposition is LicenseDisposition.ALLOW
        ):
            raise SoftwareFactoryError(
                "SF-14 unknown license/commercial evidence cannot default to ALLOW"
            )
        if policy.imported_code_disposition is LicenseDisposition.ALLOW:
            raise SoftwareFactoryError(
                "SF-14 imported code/text cannot silently default to ALLOW"
            )
        return policy

    def _validate_artifacts(
        self,
        artifacts: tuple[ArtifactProvenanceInput, ...],
        *,
        references: tuple[str, ...],
        reviewed_paths: tuple[str, ...],
        policy: LicenseProvenancePolicy,
        dependency_record: DependencyGovernanceRecord | None,
    ) -> tuple[ArtifactProvenanceEvidence, ...]:
        if not artifacts:
            raise SoftwareFactoryError("SF-14 requires provenance evidence for artifacts")
        if len(artifacts) != len(references):
            raise SoftwareFactoryError(
                "SF-14 artifact reference inventory does not match provenance records"
            )
        by_reference: dict[str, ArtifactProvenanceInput] = {}
        for artifact in artifacts:
            if not _trimmed(artifact.artifact_reference):
                raise SoftwareFactoryError(
                    "SF-14 artifact reference must be non-blank and trimmed"
                )
            if artifact.artifact_reference in by_reference:
                raise SoftwareFactoryError("SF-14 artifact references must be unique")
            by_reference[artifact.artifact_reference] = artifact
        if set(by_reference) != set(references):
            raise SoftwareFactoryError(
                "SF-14 artifact references and provenance records must match exactly"
            )

        dependency_by_hash: dict[str, DependencyEvidence] = {}
        if dependency_record is not None:
            dependency_by_hash = {
                item.evidence_sha256: item
                for item in dependency_record.dependency_evidence
            }
        validated = tuple(
            self._validate_artifact(
                by_reference[reference],
                reviewed_paths=reviewed_paths,
                policy=policy,
                dependency_by_hash=dependency_by_hash,
            )
            for reference in references
        )
        return validated

    def _validate_artifact(
        self,
        artifact: ArtifactProvenanceInput,
        *,
        reviewed_paths: tuple[str, ...],
        policy: LicenseProvenancePolicy,
        dependency_by_hash: dict[str, DependencyEvidence],
    ) -> ArtifactProvenanceEvidence:
        if _SHA256.fullmatch(artifact.artifact_sha256) is None:
            raise SoftwareFactoryError("SF-14 artifact SHA-256 is invalid")
        if not _trimmed(artifact.source_reference):
            raise SoftwareFactoryError("SF-14 artifact source reference is required")
        paths = _normalize_paths(artifact.repository_paths)
        if not set(paths).issubset(reviewed_paths):
            raise SoftwareFactoryError(
                "SF-14 artifact provenance exceeds exact SF-12 reviewed-path scope"
            )
        evidence_references = _normalize_references(artifact.evidence_references)
        license_value = _optional_trimmed(artifact.license, "license")
        license_evidence = _optional_trimmed(
            artifact.license_evidence_reference,
            "license evidence reference",
        )
        reasons: list[tuple[LicenseDisposition, str]] = []
        risk_flags: set[str] = set()

        if artifact.kind is ProvenanceKind.GENERATED_CODE:
            _require_usage(artifact, ProvenanceUsage.FIRST_PARTY_GENERATION)
            if not paths:
                raise SoftwareFactoryError(
                    "SF-14 generated code must bind to a reviewed repository path"
                )
            if artifact.code_text_imported:
                raise SoftwareFactoryError(
                    "SF-14 generated code cannot be labeled as imported code/text"
                )
            _require_no_dependency_identity(artifact)
            _require_license_evidence(license_value, license_evidence)
            _apply_license_policy(
                license_value,
                artifact.commercial_compatibility,
                policy,
                reasons,
                risk_flags,
            )
            if artifact.generated_by_ai:
                risk_flags.add("AI_GENERATED_CODE_IP_RISK_NOT_CLEARED")
        elif artifact.kind is ProvenanceKind.THIRD_PARTY_DEPENDENCY:
            _require_usage(artifact, ProvenanceUsage.DEPENDENCY_INCLUSION)
            if artifact.generated_by_ai or artifact.code_text_imported:
                raise SoftwareFactoryError(
                    "SF-14 dependency provenance cannot masquerade as generated/imported text"
                )
            _require_license_evidence(license_value, license_evidence)
            matched = _match_dependency_evidence(artifact, dependency_by_hash)
            expected_paths = tuple(
                sorted(
                    path
                    for path in (matched.manifest_path, matched.lockfile_path)
                    if path is not None
                )
            )
            if paths != expected_paths:
                raise SoftwareFactoryError(
                    "SF-14 dependency artifact paths do not match exact SF-13 evidence"
                )
            if (
                license_value != matched.license
                or artifact.commercial_compatibility is not matched.commercial_compatibility
            ):
                raise SoftwareFactoryError(
                    "SF-14 dependency license/commercial evidence conflicts with SF-13"
                )
            upstream_disposition = _map_dependency_disposition(matched.disposition)
            if upstream_disposition is not LicenseDisposition.ALLOW:
                reasons.append(
                    (
                        upstream_disposition,
                        "dependency disposition inherited from exact SF-13 evidence",
                    )
                )
                risk_flags.add(
                    "DEPENDENCY_GOVERNANCE_" + upstream_disposition.value
                )
            _apply_license_policy(
                license_value,
                artifact.commercial_compatibility,
                policy,
                reasons,
                risk_flags,
            )
        elif artifact.kind is ProvenanceKind.THIRD_PARTY_ASSET:
            _require_usage(artifact, ProvenanceUsage.ASSET_IMPORT)
            if not paths:
                raise SoftwareFactoryError(
                    "SF-14 third-party asset must bind to a reviewed repository path"
                )
            if artifact.generated_by_ai or artifact.code_text_imported:
                raise SoftwareFactoryError(
                    "SF-14 third-party asset provenance has invalid generation/import flags"
                )
            _require_no_dependency_identity(artifact)
            _require_license_evidence(license_value, license_evidence)
            _apply_license_policy(
                license_value,
                artifact.commercial_compatibility,
                policy,
                reasons,
                risk_flags,
            )
        elif artifact.kind is ProvenanceKind.EXTERNAL_REFERENCE:
            if artifact.generated_by_ai:
                raise SoftwareFactoryError(
                    "SF-14 external reference cannot be labeled as generated code"
                )
            _require_no_dependency_identity(artifact)
            if artifact.usage is ProvenanceUsage.CONCEPT_REFERENCE:
                if artifact.code_text_imported:
                    raise SoftwareFactoryError(
                        "SF-14 concept reference cannot import code/text"
                    )
                if license_value is not None or license_evidence is not None:
                    raise SoftwareFactoryError(
                        "SF-14 concept-only reference must not masquerade as imported licensed content"
                    )
                if artifact.commercial_compatibility is not CommercialCompatibility.UNKNOWN:
                    raise SoftwareFactoryError(
                        "SF-14 concept-only reference commercial compatibility must remain UNKNOWN"
                    )
                risk_flags.add("REFERENCE_USED_FOR_CONCEPT_ONLY")
            elif artifact.usage is ProvenanceUsage.CODE_TEXT_IMPORT:
                if not artifact.code_text_imported:
                    raise SoftwareFactoryError(
                        "SF-14 code/text import must be explicitly marked imported"
                    )
                if not paths:
                    raise SoftwareFactoryError(
                        "SF-14 imported code/text must bind to a reviewed repository path"
                    )
                _require_license_evidence(license_value, license_evidence)
                _apply_license_policy(
                    license_value,
                    artifact.commercial_compatibility,
                    policy,
                    reasons,
                    risk_flags,
                )
                reasons.append(
                    (
                        policy.imported_code_disposition,
                        "external code/text import requires explicit provenance review",
                    )
                )
                risk_flags.add("CODE_TEXT_IMPORTED_FROM_EXTERNAL_REFERENCE")
            else:
                raise SoftwareFactoryError(
                    "SF-14 external reference usage must be concept-reference or code/text-import"
                )
        else:
            raise SoftwareFactoryError("SF-14 provenance kind is unsupported")

        disposition = _aggregate_disposition(tuple(item[0] for item in reasons))
        policy_reasons = tuple(item[1] for item in reasons)
        normalized_risk_flags = tuple(sorted(risk_flags))
        material = _artifact_material(
            artifact,
            paths=paths,
            license_value=license_value,
            license_evidence=license_evidence,
            disposition=disposition,
            policy_reasons=policy_reasons,
            risk_flags=normalized_risk_flags,
            evidence_references=evidence_references,
        )
        return ArtifactProvenanceEvidence(
            artifact_reference=artifact.artifact_reference,
            kind=artifact.kind,
            usage=artifact.usage,
            artifact_sha256=artifact.artifact_sha256,
            repository_paths=paths,
            source_reference=artifact.source_reference,
            generated_by_ai=artifact.generated_by_ai,
            code_text_imported=artifact.code_text_imported,
            license=license_value,
            license_evidence_reference=license_evidence,
            commercial_compatibility=artifact.commercial_compatibility,
            dependency_package=artifact.dependency_package,
            dependency_version=artifact.dependency_version,
            dependency_source=artifact.dependency_source,
            upstream_dependency_evidence_sha256=artifact.upstream_dependency_evidence_sha256,
            disposition=disposition,
            policy_reasons=policy_reasons,
            risk_flags=normalized_risk_flags,
            evidence_references=evidence_references,
            ip_risk_clearance_claimed=False,
            evidence_sha256=canonical_sha256(material),
        )


def _validate_model_metadata(
    metadata: ModelProviderMetadata,
    *,
    policy: LicenseProvenancePolicy,
    expected_invocation_id: str,
) -> ModelProviderMetadata:
    values = (
        metadata.provider_id,
        metadata.model_id,
        metadata.invocation_id,
        metadata.evidence_reference,
    )
    if policy.model_provider_metadata_permitted:
        if not metadata.disclosure_permitted:
            raise SoftwareFactoryError(
                "SF-14 policy permits model/provider metadata but disclosure evidence is missing"
            )
        if any(value is None or not _trimmed(value) for value in values):
            raise SoftwareFactoryError(
                "SF-14 permitted model/provider metadata must be complete and trimmed"
            )
        if metadata.invocation_id != expected_invocation_id:
            raise SoftwareFactoryError(
                "SF-14 model/provider metadata invocation does not match engineering lineage"
            )
    else:
        if metadata.disclosure_permitted or any(value is not None for value in values):
            raise SoftwareFactoryError(
                "SF-14 model/provider metadata must remain undisclosed when policy forbids it"
            )
    return metadata


def _match_dependency_evidence(
    artifact: ArtifactProvenanceInput,
    dependency_by_hash: dict[str, DependencyEvidence],
) -> DependencyEvidence:
    identity = (
        artifact.dependency_package,
        artifact.dependency_version,
        artifact.dependency_source,
        artifact.upstream_dependency_evidence_sha256,
    )
    if any(value is None or not _trimmed(value) for value in identity):
        raise SoftwareFactoryError(
            "SF-14 dependency provenance requires package/version/source/SF-13 evidence hash"
        )
    upstream_hash = artifact.upstream_dependency_evidence_sha256
    assert upstream_hash is not None
    if _SHA256.fullmatch(upstream_hash) is None:
        raise SoftwareFactoryError("SF-14 upstream SF-13 evidence hash is invalid")
    matched = dependency_by_hash.get(upstream_hash)
    if matched is None:
        raise SoftwareFactoryError(
            "SF-14 dependency provenance is not bound to exact SF-13 evidence"
        )
    if (
        artifact.dependency_package != matched.package
        or artifact.dependency_version != matched.version
        or artifact.dependency_source != matched.source
    ):
        raise SoftwareFactoryError(
            "SF-14 dependency identity conflicts with exact SF-13 evidence"
        )
    return matched


def _require_usage(artifact: ArtifactProvenanceInput, expected: ProvenanceUsage) -> None:
    if artifact.usage is not expected:
        raise SoftwareFactoryError(
            f"SF-14 {artifact.kind.value} requires {expected.value} usage"
        )


def _require_no_dependency_identity(artifact: ArtifactProvenanceInput) -> None:
    values = (
        artifact.dependency_package,
        artifact.dependency_version,
        artifact.dependency_source,
        artifact.upstream_dependency_evidence_sha256,
    )
    if any(value is not None for value in values):
        raise SoftwareFactoryError(
            "SF-14 non-dependency provenance must not carry dependency identity"
        )


def _require_license_evidence(
    license_value: str | None,
    license_evidence: str | None,
) -> None:
    if license_value is None or license_evidence is None:
        raise SoftwareFactoryError(
            "SF-14 distributed/imported artifact requires explicit license evidence"
        )


def _apply_license_policy(
    license_value: str | None,
    commercial_compatibility: CommercialCompatibility,
    policy: LicenseProvenancePolicy,
    reasons: list[tuple[LicenseDisposition, str]],
    risk_flags: set[str],
) -> None:
    assert license_value is not None
    if license_value in policy.blocked_licenses:
        reasons.append(
            (LicenseDisposition.BLOCK, "artifact license is blocked by supplied policy")
        )
    elif license_value in policy.review_licenses:
        reasons.append(
            (
                LicenseDisposition.REVIEW_REQUIRED,
                "artifact license requires supplied-policy review",
            )
        )
    elif license_value not in policy.allowed_licenses:
        reasons.append(
            (
                policy.unknown_license_disposition,
                "artifact license is not explicitly classified by supplied policy",
            )
        )
        risk_flags.add("LICENSE_CLASSIFICATION_UNRESOLVED")

    if commercial_compatibility is CommercialCompatibility.INCOMPATIBLE:
        reasons.append(
            (
                LicenseDisposition.BLOCK,
                "artifact is commercially incompatible under supplied evidence",
            )
        )
    elif commercial_compatibility is CommercialCompatibility.UNKNOWN:
        reasons.append(
            (
                policy.unknown_commercial_disposition,
                "artifact commercial compatibility is unresolved",
            )
        )
        risk_flags.add("COMMERCIAL_COMPATIBILITY_UNRESOLVED")


def _validate_reviewed_path_coverage(
    records: tuple[ArtifactProvenanceEvidence, ...],
    reviewed_paths: tuple[str, ...],
) -> None:
    covered = {
        path
        for record in records
        for path in record.repository_paths
    }
    if covered != set(reviewed_paths):
        missing = sorted(set(reviewed_paths) - covered)
        extra = sorted(covered - set(reviewed_paths))
        raise SoftwareFactoryError(
            f"SF-14 provenance path coverage mismatch: missing={missing}, extra={extra}"
        )


def _validate_dependency_inventory_coverage(
    records: tuple[ArtifactProvenanceEvidence, ...],
    dependency_record: DependencyGovernanceRecord | None,
) -> None:
    actual = {
        record.upstream_dependency_evidence_sha256
        for record in records
        if record.kind is ProvenanceKind.THIRD_PARTY_DEPENDENCY
    }
    actual.discard(None)
    expected = (
        {item.evidence_sha256 for item in dependency_record.dependency_evidence}
        if dependency_record is not None
        else set()
    )
    if actual != expected:
        raise SoftwareFactoryError(
            "SF-14 dependency provenance inventory does not match exact SF-13 evidence"
        )


def _normalize_references(references: tuple[str, ...]) -> tuple[str, ...]:
    if not references:
        raise SoftwareFactoryError("SF-14 requires non-empty evidence references")
    normalized: list[str] = []
    for reference in references:
        if not _trimmed(reference):
            raise SoftwareFactoryError("SF-14 evidence reference must be non-blank and trimmed")
        normalized.append(reference)
    if len(normalized) != len(set(normalized)):
        raise SoftwareFactoryError("SF-14 evidence references must be unique")
    return tuple(sorted(normalized))


def _normalize_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    for path in paths:
        if not _trimmed(path) or path.startswith(("/", "\\")):
            raise SoftwareFactoryError("SF-14 repository paths must be relative")
        candidate = path.replace("\\", "/")
        if any(part in {"", ".", ".."} for part in candidate.split("/")):
            raise SoftwareFactoryError("SF-14 repository paths must be normalized")
        normalized.append(candidate)
    if len(normalized) != len(set(normalized)):
        raise SoftwareFactoryError("SF-14 repository paths must be unique")
    return tuple(sorted(normalized))


def _is_dependency_path(path: str) -> bool:
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    return name in _DEPENDENCY_FILENAMES or (
        name.startswith("requirements") and name.endswith(".txt")
    )


def _optional_trimmed(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    if not _trimmed(value):
        raise SoftwareFactoryError(f"SF-14 {label} must be non-blank and trimmed")
    return value


def _trimmed(value: str) -> bool:
    return bool(value) and value == value.strip()


def _map_dependency_disposition(
    disposition: DependencyDisposition,
) -> LicenseDisposition:
    if disposition is DependencyDisposition.BLOCK:
        return LicenseDisposition.BLOCK
    if disposition is DependencyDisposition.REVIEW_REQUIRED:
        return LicenseDisposition.REVIEW_REQUIRED
    return LicenseDisposition.ALLOW


def _aggregate_disposition(
    dispositions: tuple[LicenseDisposition, ...],
) -> LicenseDisposition:
    if LicenseDisposition.BLOCK in dispositions:
        return LicenseDisposition.BLOCK
    if LicenseDisposition.REVIEW_REQUIRED in dispositions:
        return LicenseDisposition.REVIEW_REQUIRED
    return LicenseDisposition.ALLOW


def _aggregate_evidence_references(
    review: IndependentReviewRecord,
    dependency_record: DependencyGovernanceRecord | None,
    model_metadata: ModelProviderMetadata,
    records: tuple[ArtifactProvenanceEvidence, ...],
) -> tuple[str, ...]:
    references = {
        f"review-sha256:{review.record_sha256}",
        f"validation-sha256:{review.validation_report_sha256}",
    }
    if dependency_record is not None:
        references.add(f"dependency-governance-sha256:{dependency_record.record_sha256}")
    if model_metadata.evidence_reference is not None:
        references.add(model_metadata.evidence_reference)
    for record in records:
        references.update(record.evidence_references)
        if record.license_evidence_reference is not None:
            references.add(record.license_evidence_reference)
        references.add(f"artifact-sha256:{record.artifact_sha256}")
    return tuple(sorted(references))


def _policy_material(policy: LicenseProvenancePolicy) -> dict[str, object]:
    return {
        "policy_id": policy.policy_id,
        "allowed_licenses": sorted(policy.allowed_licenses),
        "review_licenses": sorted(policy.review_licenses),
        "blocked_licenses": sorted(policy.blocked_licenses),
        "unknown_license_disposition": policy.unknown_license_disposition.value,
        "unknown_commercial_disposition": policy.unknown_commercial_disposition.value,
        "imported_code_disposition": policy.imported_code_disposition.value,
        "model_provider_metadata_permitted": policy.model_provider_metadata_permitted,
    }


def _artifact_material(
    artifact: ArtifactProvenanceInput,
    *,
    paths: tuple[str, ...],
    license_value: str | None,
    license_evidence: str | None,
    disposition: LicenseDisposition,
    policy_reasons: tuple[str, ...],
    risk_flags: tuple[str, ...],
    evidence_references: tuple[str, ...],
) -> dict[str, object]:
    return {
        "artifact_reference": artifact.artifact_reference,
        "kind": artifact.kind.value,
        "usage": artifact.usage.value,
        "artifact_sha256": artifact.artifact_sha256,
        "repository_paths": list(paths),
        "source_reference": artifact.source_reference,
        "generated_by_ai": artifact.generated_by_ai,
        "code_text_imported": artifact.code_text_imported,
        "license": license_value,
        "license_evidence_reference": license_evidence,
        "commercial_compatibility": artifact.commercial_compatibility.value,
        "dependency_package": artifact.dependency_package,
        "dependency_version": artifact.dependency_version,
        "dependency_source": artifact.dependency_source,
        "upstream_dependency_evidence_sha256": artifact.upstream_dependency_evidence_sha256,
        "disposition": disposition.value,
        "policy_reasons": list(policy_reasons),
        "risk_flags": list(risk_flags),
        "evidence_references": list(evidence_references),
        "ip_risk_clearance_claimed": False,
    }


def _model_metadata_material(metadata: ModelProviderMetadata) -> dict[str, object]:
    return {
        "disclosure_permitted": metadata.disclosure_permitted,
        "provider_id": metadata.provider_id,
        "model_id": metadata.model_id,
        "invocation_id": metadata.invocation_id,
        "evidence_reference": metadata.evidence_reference,
    }


def _provenance_record_material(record: ArtifactProvenanceEvidence) -> dict[str, object]:
    return {
        "artifact_reference": record.artifact_reference,
        "kind": record.kind.value,
        "usage": record.usage.value,
        "artifact_sha256": record.artifact_sha256,
        "repository_paths": list(record.repository_paths),
        "source_reference": record.source_reference,
        "generated_by_ai": record.generated_by_ai,
        "code_text_imported": record.code_text_imported,
        "license": record.license,
        "license_evidence_reference": record.license_evidence_reference,
        "commercial_compatibility": record.commercial_compatibility.value,
        "dependency_package": record.dependency_package,
        "dependency_version": record.dependency_version,
        "dependency_source": record.dependency_source,
        "upstream_dependency_evidence_sha256": record.upstream_dependency_evidence_sha256,
        "disposition": record.disposition.value,
        "policy_reasons": list(record.policy_reasons),
        "risk_flags": list(record.risk_flags),
        "evidence_references": list(record.evidence_references),
        "ip_risk_clearance_claimed": record.ip_risk_clearance_claimed,
        "evidence_sha256": record.evidence_sha256,
    }


def _record_material(
    *,
    request: LicenseProvenanceRequest,
    package: SkillPackage,
    review: IndependentReviewRecord,
    repository_sha: str,
    changeset_sha256: str,
    dependency_record: DependencyGovernanceRecord | None,
    model_metadata: ModelProviderMetadata,
    references: tuple[str, ...],
    provenance_records: tuple[ArtifactProvenanceEvidence, ...],
    disposition: LicenseDisposition,
    risk_flags: tuple[str, ...],
    evidence_references: tuple[str, ...],
    policy_sha256: str,
) -> dict[str, object]:
    validation_request = request.review_request.validation_request
    proposal = validation_request.software_proposal
    execution = validation_request.engineering_execution
    return {
        "provenance_id": request.provenance_id,
        "contract_version": LICENSE_PROVENANCE_CONTRACT_VERSION,
        "skill_id": package.manifest.skill_id,
        "skill_version": package.manifest.version,
        "policy_id": request.policy.policy_id,
        "policy_sha256": policy_sha256,
        "tenant_id": review.tenant_id,
        "task_id": review.task_id,
        "correlation_id": review.correlation_id,
        "factory_job_id": proposal.job_id,
        "repository_base_sha": repository_sha,
        "changeset_sha256": changeset_sha256,
        "engineering_agent_id": execution.admission.agent_id,
        "engineering_invocation_id": execution.admission.invocation_id,
        "reviewer_ids": list(review.reviewers),
        "review_record_sha256": review.record_sha256,
        "validation_report_sha256": review.validation_report_sha256,
        "dependency_governance_record_sha256": (
            dependency_record.record_sha256 if dependency_record is not None else None
        ),
        "model_provider_metadata": _model_metadata_material(model_metadata),
        "artifact_references": list(references),
        "provenance_records": [
            _provenance_record_material(record) for record in provenance_records
        ],
        "license_disposition": disposition.value,
        "risk_flags": list(risk_flags),
        "evidence_references": list(evidence_references),
        "independent_review_required": package.manifest.independent_review_required,
        "ip_risk_clearance_claimed": False,
        "acceptance_authorized": False,
        "promotion_authorized": False,
        "deployment_authorized": False,
        "production_applied": False,
        "subject_mutated": False,
    }
