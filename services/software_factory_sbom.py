"""SF-15 deterministic Software Bill of Materials evidence.

The SBOM gate derives a machine-readable, change-scoped component inventory from
exact SF-14 license/IP provenance and, when dependencies are present, exact
SF-13 dependency-governance evidence.  It does not scan the network, invent
package metadata, claim release completeness, or grant downstream authority.

SF-16 owns build provenance.  Consequently this module deliberately records
``build_provenance_bound=False`` and ``release_complete=False``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum

from services.software_factory import SoftwareFactoryError
from services.software_factory_dependencies import (
    CommercialCompatibility,
    DependencyEvidence,
    DependencyOperation,
    DependencyRole,
)
from services.software_factory_license_provenance import (
    ArtifactProvenanceEvidence,
    LicenseDisposition,
    LicenseProvenanceRecord,
    LicenseProvenanceRequest,
    ProvenanceKind,
    ProvenanceUsage,
    SoftwareFactoryLicenseProvenance,
)
from services.software_factory_skills import SkillRegistry
from src.core.validation_pipeline import canonical_sha256

SBOM_CONTRACT_VERSION = "1.0.0"
SBOM_DOCUMENT_FORMAT = "ILAIOS-SBOM-JSON"
SBOM_DOCUMENT_SPEC_VERSION = "1.0"
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SBOMCoverage(str, Enum):
    """The evidence scope represented by this phase."""

    REVIEWED_CHANGESET = "REVIEWED_CHANGESET"


class SBOMComponentType(str, Enum):
    APPLICATION = "APPLICATION"
    LIBRARY = "LIBRARY"
    FILE = "FILE"
    IMPORTED_SOURCE = "IMPORTED_SOURCE"


@dataclass(frozen=True, slots=True)
class SBOMComponent:
    bom_ref: str
    component_type: SBOMComponentType
    artifact_reference: str
    name: str
    version: str | None
    source_reference: str
    artifact_sha256: str
    integrity: str | None
    integrity_verified: bool | None
    license: str | None
    license_evidence_reference: str | None
    commercial_compatibility: CommercialCompatibility
    dependency_role: DependencyRole | None
    dependency_operation: DependencyOperation | None
    repository_paths: tuple[str, ...]
    generated_by_ai: bool
    code_text_imported: bool
    present_after_change: bool
    disposition: LicenseDisposition
    risk_flags: tuple[str, ...]
    evidence_references: tuple[str, ...]
    provenance_evidence_sha256: str
    dependency_evidence_sha256: str | None
    component_sha256: str


@dataclass(frozen=True, slots=True)
class SBOMReferenceEvidence:
    """Concept-only references are evidence, not shipped/material components."""

    artifact_reference: str
    source_reference: str
    artifact_sha256: str
    disposition: LicenseDisposition
    risk_flags: tuple[str, ...]
    evidence_references: tuple[str, ...]
    provenance_evidence_sha256: str
    reference_sha256: str


@dataclass(frozen=True, slots=True)
class SoftwareSBOMRequest:
    sbom_id: str
    document_name: str
    provenance_request: LicenseProvenanceRequest
    provenance_record: LicenseProvenanceRecord


@dataclass(frozen=True, slots=True)
class SoftwareSBOMDocument:
    sbom_id: str
    contract_version: str
    document_format: str
    document_spec_version: str
    document_name: str
    coverage: SBOMCoverage
    serial_number: str
    tenant_id: str
    task_id: str
    correlation_id: str
    factory_job_id: str
    repository_base_sha: str
    changeset_sha256: str
    review_record_sha256: str
    validation_report_sha256: str
    dependency_governance_record_sha256: str | None
    license_provenance_record_sha256: str
    dependency_paths: tuple[str, ...]
    components: tuple[SBOMComponent, ...]
    non_material_references: tuple[SBOMReferenceEvidence, ...]
    disposition: LicenseDisposition
    risk_flags: tuple[str, ...]
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]
    independent_review_required: bool
    ip_risk_clearance_claimed: bool
    release_complete: bool
    build_provenance_bound: bool
    acceptance_authorized: bool
    promotion_authorized: bool
    deployment_authorized: bool
    production_applied: bool
    subject_mutated: bool
    document_sha256: str


class SoftwareFactorySBOM:
    """Generate deterministic SF-15 SBOM evidence from exact upstream lineage."""

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    def generate(self, request: SoftwareSBOMRequest) -> SoftwareSBOMDocument:
        _validate_request_identity(request)
        provenance = SoftwareFactoryLicenseProvenance(self._registry).evaluate(
            request.provenance_request
        )
        if provenance != request.provenance_record:
            raise SoftwareFactoryError(
                "SF-15 license/provenance record is stale, tampered, or mismatched"
            )
        _validate_upstream_authority(provenance)
        _validate_upstream_digests(provenance)

        dependency_by_digest, dependency_paths = _dependency_inventory(request)
        components: list[SBOMComponent] = []
        references: list[SBOMReferenceEvidence] = []
        for evidence in provenance.provenance_records:
            if (
                evidence.kind is ProvenanceKind.EXTERNAL_REFERENCE
                and evidence.usage is ProvenanceUsage.CONCEPT_REFERENCE
            ):
                references.append(_reference_from_provenance(evidence))
                continue
            components.append(
                _component_from_provenance(evidence, dependency_by_digest)
            )

        normalized_components = tuple(sorted(components, key=lambda item: item.bom_ref))
        normalized_references = tuple(
            sorted(references, key=lambda item: item.artifact_reference)
        )
        _validate_dependency_component_coverage(
            normalized_components,
            dependency_by_digest,
        )

        limitations = (
            "BUILD_PROVENANCE_NOT_BOUND_UNTIL_SF16",
            "RELEASE_COMPLETENESS_NOT_CLAIMED",
            "REVIEWED_CHANGESET_SCOPE_ONLY",
        )
        evidence_references = tuple(
            sorted(
                set(provenance.evidence_references)
                | {
                    reference
                    for component in normalized_components
                    for reference in component.evidence_references
                }
                | {
                    reference
                    for item in normalized_references
                    for reference in item.evidence_references
                }
            )
        )
        material = _document_material(
            request=request,
            provenance=provenance,
            dependency_paths=dependency_paths,
            components=normalized_components,
            references=normalized_references,
            evidence_references=evidence_references,
            limitations=limitations,
        )
        document_sha256 = canonical_sha256(material)
        serial_number = f"urn:ilaios:sbom:{document_sha256}"

        return SoftwareSBOMDocument(
            sbom_id=request.sbom_id,
            contract_version=SBOM_CONTRACT_VERSION,
            document_format=SBOM_DOCUMENT_FORMAT,
            document_spec_version=SBOM_DOCUMENT_SPEC_VERSION,
            document_name=request.document_name,
            coverage=SBOMCoverage.REVIEWED_CHANGESET,
            serial_number=serial_number,
            tenant_id=provenance.tenant_id,
            task_id=provenance.task_id,
            correlation_id=provenance.correlation_id,
            factory_job_id=provenance.factory_job_id,
            repository_base_sha=provenance.repository_base_sha,
            changeset_sha256=provenance.changeset_sha256,
            review_record_sha256=provenance.review_record_sha256,
            validation_report_sha256=provenance.validation_report_sha256,
            dependency_governance_record_sha256=(
                provenance.dependency_governance_record_sha256
            ),
            license_provenance_record_sha256=provenance.record_sha256,
            dependency_paths=dependency_paths,
            components=normalized_components,
            non_material_references=normalized_references,
            disposition=provenance.license_disposition,
            risk_flags=provenance.risk_flags,
            evidence_references=evidence_references,
            limitations=limitations,
            independent_review_required=provenance.independent_review_required,
            ip_risk_clearance_claimed=False,
            release_complete=False,
            build_provenance_bound=False,
            acceptance_authorized=False,
            promotion_authorized=False,
            deployment_authorized=False,
            production_applied=False,
            subject_mutated=False,
            document_sha256=document_sha256,
        )


def render_sbom(document: SoftwareSBOMDocument) -> dict[str, object]:
    """Render the canonical deterministic JSON-compatible SBOM payload."""

    return {
        "format": document.document_format,
        "specVersion": document.document_spec_version,
        "serialNumber": document.serial_number,
        "version": 1,
        "metadata": {
            "sbomId": document.sbom_id,
            "name": document.document_name,
            "coverage": document.coverage.value,
            "tenantId": document.tenant_id,
            "taskId": document.task_id,
            "correlationId": document.correlation_id,
            "factoryJobId": document.factory_job_id,
            "repositoryBaseSha": document.repository_base_sha,
            "changeSetSha256": document.changeset_sha256,
            "reviewRecordSha256": document.review_record_sha256,
            "validationReportSha256": document.validation_report_sha256,
            "dependencyGovernanceRecordSha256": (
                document.dependency_governance_record_sha256
            ),
            "licenseProvenanceRecordSha256": (
                document.license_provenance_record_sha256
            ),
            "dependencyPaths": list(document.dependency_paths),
        },
        "components": [_component_payload(item) for item in document.components],
        "nonMaterialReferences": [
            _reference_payload(item) for item in document.non_material_references
        ],
        "policy": {
            "disposition": document.disposition.value,
            "riskFlags": list(document.risk_flags),
            "limitations": list(document.limitations),
            "independentReviewRequired": document.independent_review_required,
            "ipRiskClearanceClaimed": document.ip_risk_clearance_claimed,
        },
        "authority": {
            "releaseComplete": document.release_complete,
            "buildProvenanceBound": document.build_provenance_bound,
            "acceptanceAuthorized": document.acceptance_authorized,
            "promotionAuthorized": document.promotion_authorized,
            "deploymentAuthorized": document.deployment_authorized,
            "productionApplied": document.production_applied,
            "subjectMutated": document.subject_mutated,
        },
        "evidenceReferences": list(document.evidence_references),
        "documentSha256": document.document_sha256,
    }


def render_sbom_json(document: SoftwareSBOMDocument) -> str:
    """Return stable JSON bytes-as-text for evidence storage or later packaging."""

    return json.dumps(
        render_sbom(document),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _validate_request_identity(request: SoftwareSBOMRequest) -> None:
    for label, value in (
        ("sbom_id", request.sbom_id),
        ("document_name", request.document_name),
    ):
        if not _trimmed(value):
            raise SoftwareFactoryError(f"SF-15 {label} must be non-blank and trimmed")
    if len(request.sbom_id) > 160:
        raise SoftwareFactoryError("SF-15 sbom_id exceeds the bounded identifier length")
    if len(request.document_name) > 240:
        raise SoftwareFactoryError("SF-15 document_name exceeds the bounded name length")


def _validate_upstream_authority(record: LicenseProvenanceRecord) -> None:
    if (
        record.acceptance_authorized
        or record.promotion_authorized
        or record.deployment_authorized
        or record.production_applied
        or record.subject_mutated
    ):
        raise SoftwareFactoryError(
            "SF-15 cannot consume provenance evidence carrying downstream authority"
        )
    if record.ip_risk_clearance_claimed:
        raise SoftwareFactoryError(
            "SF-15 cannot consume provenance that claims automatic IP-risk clearance"
        )


def _validate_upstream_digests(record: LicenseProvenanceRecord) -> None:
    if _SHA1.fullmatch(record.repository_base_sha) is None:
        raise SoftwareFactoryError("SF-15 requires a lowercase repository base SHA")
    for label, value in (
        ("ChangeSet", record.changeset_sha256),
        ("review", record.review_record_sha256),
        ("validation", record.validation_report_sha256),
        ("license/provenance", record.record_sha256),
    ):
        if _SHA256.fullmatch(value) is None:
            raise SoftwareFactoryError(f"SF-15 requires a valid {label} SHA-256")
    dependency_digest = record.dependency_governance_record_sha256
    if dependency_digest is not None and _SHA256.fullmatch(dependency_digest) is None:
        raise SoftwareFactoryError(
            "SF-15 requires a valid dependency-governance SHA-256"
        )


def _dependency_inventory(
    request: SoftwareSBOMRequest,
) -> tuple[dict[str, DependencyEvidence], tuple[str, ...]]:
    dependency_record = request.provenance_request.dependency_governance_record
    if dependency_record is None:
        if request.provenance_record.dependency_governance_record_sha256 is not None:
            raise SoftwareFactoryError("SF-15 dependency lineage is incomplete")
        return {}, ()
    if (
        request.provenance_record.dependency_governance_record_sha256
        != dependency_record.record_sha256
    ):
        raise SoftwareFactoryError("SF-15 dependency lineage digest mismatch")
    by_digest: dict[str, DependencyEvidence] = {}
    for evidence in dependency_record.dependency_evidence:
        if _SHA256.fullmatch(evidence.evidence_sha256) is None:
            raise SoftwareFactoryError("SF-15 dependency evidence digest is malformed")
        if evidence.evidence_sha256 in by_digest:
            raise SoftwareFactoryError("SF-15 dependency evidence digest is duplicated")
        by_digest[evidence.evidence_sha256] = evidence
    return by_digest, tuple(sorted(dependency_record.dependency_paths))


def _component_from_provenance(
    evidence: ArtifactProvenanceEvidence,
    dependencies: dict[str, DependencyEvidence],
) -> SBOMComponent:
    if _SHA256.fullmatch(evidence.artifact_sha256) is None:
        raise SoftwareFactoryError("SF-15 provenance artifact digest is malformed")
    if _SHA256.fullmatch(evidence.evidence_sha256) is None:
        raise SoftwareFactoryError("SF-15 provenance evidence digest is malformed")

    dependency: DependencyEvidence | None = None
    if evidence.kind is ProvenanceKind.THIRD_PARTY_DEPENDENCY:
        digest = evidence.upstream_dependency_evidence_sha256
        if digest is None or digest not in dependencies:
            raise SoftwareFactoryError(
                "SF-15 dependency component is not bound to exact SF-13 evidence"
            )
        dependency = dependencies[digest]
        if (
            evidence.dependency_package != dependency.package
            or evidence.dependency_version != dependency.version
            or evidence.dependency_source != dependency.source
            or evidence.license != dependency.license
            or evidence.commercial_compatibility
            is not dependency.commercial_compatibility
        ):
            raise SoftwareFactoryError(
                "SF-15 dependency component conflicts with upstream SF-13/SF-14 evidence"
            )
    elif evidence.upstream_dependency_evidence_sha256 is not None:
        raise SoftwareFactoryError(
            "SF-15 non-dependency component carries dependency evidence"
        )

    component_type = _component_type(evidence)
    name = dependency.package if dependency is not None else evidence.artifact_reference
    version = dependency.version if dependency is not None else None
    material: dict[str, object] = {
        "component_type": component_type.value,
        "artifact_reference": evidence.artifact_reference,
        "name": name,
        "version": version,
        "source_reference": evidence.source_reference,
        "artifact_sha256": evidence.artifact_sha256,
        "integrity": dependency.integrity if dependency is not None else None,
        "integrity_verified": (
            dependency.integrity_verified if dependency is not None else None
        ),
        "license": evidence.license,
        "license_evidence_reference": evidence.license_evidence_reference,
        "commercial_compatibility": evidence.commercial_compatibility.value,
        "dependency_role": dependency.role.value if dependency is not None else None,
        "dependency_operation": (
            dependency.operation.value if dependency is not None else None
        ),
        "repository_paths": list(evidence.repository_paths),
        "generated_by_ai": evidence.generated_by_ai,
        "code_text_imported": evidence.code_text_imported,
        "present_after_change": (
            dependency is None or dependency.operation is not DependencyOperation.REMOVE
        ),
        "disposition": evidence.disposition.value,
        "risk_flags": list(evidence.risk_flags),
        "evidence_references": list(evidence.evidence_references),
        "provenance_evidence_sha256": evidence.evidence_sha256,
        "dependency_evidence_sha256": (
            dependency.evidence_sha256 if dependency is not None else None
        ),
    }
    component_sha256 = canonical_sha256(material)
    bom_ref = f"urn:ilaios:component:{component_sha256}"
    return SBOMComponent(
        bom_ref=bom_ref,
        component_type=component_type,
        artifact_reference=evidence.artifact_reference,
        name=name,
        version=version,
        source_reference=evidence.source_reference,
        artifact_sha256=evidence.artifact_sha256,
        integrity=dependency.integrity if dependency is not None else None,
        integrity_verified=(
            dependency.integrity_verified if dependency is not None else None
        ),
        license=evidence.license,
        license_evidence_reference=evidence.license_evidence_reference,
        commercial_compatibility=evidence.commercial_compatibility,
        dependency_role=dependency.role if dependency is not None else None,
        dependency_operation=dependency.operation if dependency is not None else None,
        repository_paths=evidence.repository_paths,
        generated_by_ai=evidence.generated_by_ai,
        code_text_imported=evidence.code_text_imported,
        present_after_change=(
            dependency is None or dependency.operation is not DependencyOperation.REMOVE
        ),
        disposition=evidence.disposition,
        risk_flags=evidence.risk_flags,
        evidence_references=evidence.evidence_references,
        provenance_evidence_sha256=evidence.evidence_sha256,
        dependency_evidence_sha256=(
            dependency.evidence_sha256 if dependency is not None else None
        ),
        component_sha256=component_sha256,
    )


def _component_type(evidence: ArtifactProvenanceEvidence) -> SBOMComponentType:
    if evidence.kind is ProvenanceKind.GENERATED_CODE:
        return SBOMComponentType.APPLICATION
    if evidence.kind is ProvenanceKind.THIRD_PARTY_DEPENDENCY:
        return SBOMComponentType.LIBRARY
    if evidence.kind is ProvenanceKind.THIRD_PARTY_ASSET:
        return SBOMComponentType.FILE
    if (
        evidence.kind is ProvenanceKind.EXTERNAL_REFERENCE
        and evidence.usage is ProvenanceUsage.CODE_TEXT_IMPORT
    ):
        return SBOMComponentType.IMPORTED_SOURCE
    raise SoftwareFactoryError(
        "SF-15 unsupported provenance kind/usage cannot become a material component"
    )


def _reference_from_provenance(
    evidence: ArtifactProvenanceEvidence,
) -> SBOMReferenceEvidence:
    if evidence.repository_paths:
        raise SoftwareFactoryError(
            "SF-15 concept-only reference cannot claim shipped repository paths"
        )
    material = {
        "artifact_reference": evidence.artifact_reference,
        "source_reference": evidence.source_reference,
        "artifact_sha256": evidence.artifact_sha256,
        "disposition": evidence.disposition.value,
        "risk_flags": list(evidence.risk_flags),
        "evidence_references": list(evidence.evidence_references),
        "provenance_evidence_sha256": evidence.evidence_sha256,
    }
    return SBOMReferenceEvidence(
        artifact_reference=evidence.artifact_reference,
        source_reference=evidence.source_reference,
        artifact_sha256=evidence.artifact_sha256,
        disposition=evidence.disposition,
        risk_flags=evidence.risk_flags,
        evidence_references=evidence.evidence_references,
        provenance_evidence_sha256=evidence.evidence_sha256,
        reference_sha256=canonical_sha256(material),
    )


def _validate_dependency_component_coverage(
    components: tuple[SBOMComponent, ...],
    dependencies: dict[str, DependencyEvidence],
) -> None:
    represented = {
        component.dependency_evidence_sha256
        for component in components
        if component.dependency_evidence_sha256 is not None
    }
    expected = set(dependencies)
    if represented != expected:
        raise SoftwareFactoryError(
            "SF-15 dependency component coverage does not match exact SF-13 inventory"
        )


def _document_material(
    *,
    request: SoftwareSBOMRequest,
    provenance: LicenseProvenanceRecord,
    dependency_paths: tuple[str, ...],
    components: tuple[SBOMComponent, ...],
    references: tuple[SBOMReferenceEvidence, ...],
    evidence_references: tuple[str, ...],
    limitations: tuple[str, ...],
) -> dict[str, object]:
    return {
        "sbom_id": request.sbom_id,
        "contract_version": SBOM_CONTRACT_VERSION,
        "document_format": SBOM_DOCUMENT_FORMAT,
        "document_spec_version": SBOM_DOCUMENT_SPEC_VERSION,
        "document_name": request.document_name,
        "coverage": SBOMCoverage.REVIEWED_CHANGESET.value,
        "tenant_id": provenance.tenant_id,
        "task_id": provenance.task_id,
        "correlation_id": provenance.correlation_id,
        "factory_job_id": provenance.factory_job_id,
        "repository_base_sha": provenance.repository_base_sha,
        "changeset_sha256": provenance.changeset_sha256,
        "review_record_sha256": provenance.review_record_sha256,
        "validation_report_sha256": provenance.validation_report_sha256,
        "dependency_governance_record_sha256": (
            provenance.dependency_governance_record_sha256
        ),
        "license_provenance_record_sha256": provenance.record_sha256,
        "dependency_paths": list(dependency_paths),
        "components": [_component_material(item) for item in components],
        "non_material_references": [
            _reference_material(item) for item in references
        ],
        "disposition": provenance.license_disposition.value,
        "risk_flags": list(provenance.risk_flags),
        "evidence_references": list(evidence_references),
        "limitations": list(limitations),
        "independent_review_required": provenance.independent_review_required,
        "ip_risk_clearance_claimed": False,
        "release_complete": False,
        "build_provenance_bound": False,
        "acceptance_authorized": False,
        "promotion_authorized": False,
        "deployment_authorized": False,
        "production_applied": False,
        "subject_mutated": False,
    }


def _component_material(component: SBOMComponent) -> dict[str, object]:
    return {
        "bom_ref": component.bom_ref,
        "component_type": component.component_type.value,
        "artifact_reference": component.artifact_reference,
        "name": component.name,
        "version": component.version,
        "source_reference": component.source_reference,
        "artifact_sha256": component.artifact_sha256,
        "integrity": component.integrity,
        "integrity_verified": component.integrity_verified,
        "license": component.license,
        "license_evidence_reference": component.license_evidence_reference,
        "commercial_compatibility": component.commercial_compatibility.value,
        "dependency_role": (
            component.dependency_role.value
            if component.dependency_role is not None
            else None
        ),
        "dependency_operation": (
            component.dependency_operation.value
            if component.dependency_operation is not None
            else None
        ),
        "repository_paths": list(component.repository_paths),
        "generated_by_ai": component.generated_by_ai,
        "code_text_imported": component.code_text_imported,
        "present_after_change": component.present_after_change,
        "disposition": component.disposition.value,
        "risk_flags": list(component.risk_flags),
        "evidence_references": list(component.evidence_references),
        "provenance_evidence_sha256": component.provenance_evidence_sha256,
        "dependency_evidence_sha256": component.dependency_evidence_sha256,
        "component_sha256": component.component_sha256,
    }


def _reference_material(reference: SBOMReferenceEvidence) -> dict[str, object]:
    return {
        "artifact_reference": reference.artifact_reference,
        "source_reference": reference.source_reference,
        "artifact_sha256": reference.artifact_sha256,
        "disposition": reference.disposition.value,
        "risk_flags": list(reference.risk_flags),
        "evidence_references": list(reference.evidence_references),
        "provenance_evidence_sha256": reference.provenance_evidence_sha256,
        "reference_sha256": reference.reference_sha256,
    }


def _component_payload(component: SBOMComponent) -> dict[str, object]:
    return _component_material(component)


def _reference_payload(reference: SBOMReferenceEvidence) -> dict[str, object]:
    return _reference_material(reference)


def _trimmed(value: str) -> bool:
    return bool(value) and value == value.strip()
