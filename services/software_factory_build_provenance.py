"""SF-16 deterministic build provenance for governed Software Factory outputs.

This phase operationalizes the existing first-party ``sf-build`` contract.  It
binds exact SF-15 SBOM evidence to canonical SF-6 RuntimeAdapter evidence and
content-addressed build/package artifacts.  It does not spawn a parallel build
engine, publish artifacts, sign/attest them, or grant downstream authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from services.software_factory import SoftwareFactoryError
from services.software_factory_license_provenance import LicenseDisposition
from services.software_factory_runtime import RuntimeEvidence, RuntimeStepResult
from services.software_factory_sbom import (
    SoftwareFactorySBOM,
    SoftwareSBOMDocument,
    SoftwareSBOMRequest,
)
from services.software_factory_skills import SkillPackage, SkillRegistry
from src.core.validation_pipeline import canonical_sha256

BUILD_PROVENANCE_SKILL_ID = "sf-build"
BUILD_PROVENANCE_CONTRACT_VERSION = "1.0.0"
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_RUNTIME_STAGES = (
    "prepare",
    "resolve_dependencies",
    "lint",
    "typecheck",
    "test",
    "build",
    "package",
    "smoke_test",
)
_ARTIFACT_STAGES = frozenset({"build", "package"})


class BuildDisposition(str, Enum):
    ALLOW = "ALLOW"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class BuilderIdentity:
    builder_id: str
    workflow_id: str
    workflow_run_id: str
    runner_environment: str
    source_checkout_read_only: bool
    ephemeral: bool
    evidence_reference: str


@dataclass(frozen=True, slots=True)
class BuildArtifactInput:
    artifact_reference: str
    relative_path: str
    artifact_sha256: str
    size_bytes: int
    media_type: str
    producing_stage: str


@dataclass(frozen=True, slots=True)
class BuildArtifactEvidence:
    artifact_reference: str
    relative_path: str
    artifact_sha256: str
    size_bytes: int
    media_type: str
    producing_stage: str
    repository_base_sha: str
    changeset_sha256: str
    sbom_document_sha256: str
    runtime_workspace_sha256: str
    builder_sha256: str
    evidence_sha256: str


@dataclass(frozen=True, slots=True)
class BuildProvenanceRequest:
    build_id: str
    sbom_request: SoftwareSBOMRequest
    sbom_document: SoftwareSBOMDocument
    runtime_evidence: RuntimeEvidence
    builder: BuilderIdentity
    artifacts: tuple[BuildArtifactInput, ...]


@dataclass(frozen=True, slots=True)
class BuildProvenanceRecord:
    build_id: str
    contract_version: str
    skill_id: str
    skill_version: str
    tenant_id: str
    task_id: str
    correlation_id: str
    factory_job_id: str
    repository_base_sha: str
    changeset_sha256: str
    sbom_document_sha256: str
    sbom_serial_number: str
    runtime_adapter_id: str
    runtime_workspace_sha256: str
    runtime_evidence_sha256: str
    builder: BuilderIdentity
    builder_sha256: str
    artifacts: tuple[BuildArtifactEvidence, ...]
    disposition: BuildDisposition
    risk_flags: tuple[str, ...]
    evidence_references: tuple[str, ...]
    build_succeeded: bool
    build_provenance_bound: bool
    signing_attestation_bound: bool
    release_complete: bool
    acceptance_authorized: bool
    promotion_authorized: bool
    deployment_authorized: bool
    production_applied: bool
    subject_mutated: bool
    record_sha256: str


class SoftwareFactoryBuildProvenance:
    """Fail-closed SF-16 build provenance bound to SF-15 and SF-6 evidence."""

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    def generate(self, request: BuildProvenanceRequest) -> BuildProvenanceRecord:
        package = self._validate_skill_contract()
        _validate_request_identity(request)
        sbom = SoftwareFactorySBOM(self._registry).generate(request.sbom_request)
        if sbom != request.sbom_document:
            raise SoftwareFactoryError(
                "SF-16 SBOM document is stale, tampered, or mismatched"
            )
        _validate_sbom_boundary(sbom)
        runtime = _validate_runtime_evidence(request.runtime_evidence, package)
        builder = _validate_builder(request.builder)
        runtime_sha256 = canonical_sha256(_runtime_material(runtime))
        builder_sha256 = canonical_sha256(_builder_material(builder))
        artifacts = _validate_artifacts(
            request.artifacts,
            sbom=sbom,
            runtime=runtime,
            builder_sha256=builder_sha256,
        )
        disposition = _map_disposition(sbom.disposition)
        if disposition is BuildDisposition.BLOCK:
            raise SoftwareFactoryError(
                "SF-16 cannot accept build provenance for an upstream BLOCK disposition"
            )
        risk_flags = set(sbom.risk_flags)
        if disposition is BuildDisposition.REVIEW_REQUIRED:
            risk_flags.add("UPSTREAM_SUPPLY_CHAIN_REVIEW_REQUIRED")
        normalized_risk_flags = tuple(sorted(risk_flags))
        evidence_references = tuple(
            sorted(set(sbom.evidence_references) | {builder.evidence_reference})
        )
        material = _record_material(
            request=request,
            package=package,
            sbom=sbom,
            runtime=runtime,
            runtime_sha256=runtime_sha256,
            builder=builder,
            builder_sha256=builder_sha256,
            artifacts=artifacts,
            disposition=disposition,
            risk_flags=normalized_risk_flags,
            evidence_references=evidence_references,
        )
        return BuildProvenanceRecord(
            build_id=request.build_id,
            contract_version=BUILD_PROVENANCE_CONTRACT_VERSION,
            skill_id=package.manifest.skill_id,
            skill_version=package.manifest.version,
            tenant_id=sbom.tenant_id,
            task_id=sbom.task_id,
            correlation_id=sbom.correlation_id,
            factory_job_id=sbom.factory_job_id,
            repository_base_sha=sbom.repository_base_sha,
            changeset_sha256=sbom.changeset_sha256,
            sbom_document_sha256=sbom.document_sha256,
            sbom_serial_number=sbom.serial_number,
            runtime_adapter_id=runtime.adapter_id,
            runtime_workspace_sha256=runtime.workspace_sha256,
            runtime_evidence_sha256=runtime_sha256,
            builder=builder,
            builder_sha256=builder_sha256,
            artifacts=artifacts,
            disposition=disposition,
            risk_flags=normalized_risk_flags,
            evidence_references=evidence_references,
            build_succeeded=True,
            build_provenance_bound=True,
            signing_attestation_bound=False,
            release_complete=False,
            acceptance_authorized=False,
            promotion_authorized=False,
            deployment_authorized=False,
            production_applied=False,
            subject_mutated=False,
            record_sha256=canonical_sha256(material),
        )

    def _validate_skill_contract(self) -> SkillPackage:
        package = self._registry.resolve(BUILD_PROVENANCE_SKILL_ID)
        manifest = package.manifest
        if manifest.domain != "build-release-operations":
            raise SoftwareFactoryError(
                "SF-16 build skill is outside canonical build-release-operations domain"
            )
        required_inputs = {"intent", "changed_paths"}
        if not required_inputs.issubset(manifest.inputs):
            raise SoftwareFactoryError("SF-16 build skill lost canonical inputs")
        required_outputs = {
            "artifact_references",
            "artifact_hashes",
            "source_binding",
            "runtime_evidence",
        }
        if not required_outputs.issubset(manifest.outputs):
            raise SoftwareFactoryError("SF-16 build skill lost canonical outputs")
        if "runtime_adapter" not in manifest.required_capabilities:
            raise SoftwareFactoryError(
                "SF-16 build skill lost canonical RuntimeAdapter capability"
            )
        if not manifest.allowed_runtime_adapters:
            raise SoftwareFactoryError(
                "SF-16 build skill has no governed runtime adapter allowlist"
            )
        required_evidence = {
            "repository_base_sha",
            "provenance",
            "validation_results",
            "runtime_evidence",
        }
        if not required_evidence.issubset(manifest.emitted_evidence):
            raise SoftwareFactoryError("SF-16 build skill lost canonical evidence classes")
        return package


def _validate_request_identity(request: BuildProvenanceRequest) -> None:
    if not _trimmed(request.build_id):
        raise SoftwareFactoryError("SF-16 build_id must be non-blank and trimmed")
    if len(request.build_id) > 160:
        raise SoftwareFactoryError("SF-16 build_id exceeds bounded identifier length")


def _validate_sbom_boundary(sbom: SoftwareSBOMDocument) -> None:
    if _SHA1.fullmatch(sbom.repository_base_sha) is None:
        raise SoftwareFactoryError("SF-16 requires a lowercase repository base SHA")
    for label, value in (
        ("ChangeSet", sbom.changeset_sha256),
        ("SBOM", sbom.document_sha256),
    ):
        if _SHA256.fullmatch(value) is None:
            raise SoftwareFactoryError(f"SF-16 {label} SHA-256 is invalid")
    if sbom.build_provenance_bound:
        raise SoftwareFactoryError(
            "SF-16 expects pre-build-provenance SF-15 evidence"
        )
    if sbom.release_complete:
        raise SoftwareFactoryError(
            "SF-16 cannot consume an SF-15 document claiming release completeness"
        )
    if (
        sbom.acceptance_authorized
        or sbom.promotion_authorized
        or sbom.deployment_authorized
        or sbom.production_applied
        or sbom.subject_mutated
    ):
        raise SoftwareFactoryError(
            "SF-16 cannot consume SBOM evidence carrying downstream authority"
        )


def _validate_runtime_evidence(
    evidence: RuntimeEvidence,
    package: SkillPackage,
) -> RuntimeEvidence:
    if evidence.adapter_id not in package.manifest.allowed_runtime_adapters:
        raise SoftwareFactoryError("SF-16 runtime adapter is outside sf-build allowlist")
    if _SHA256.fullmatch(evidence.workspace_sha256) is None:
        raise SoftwareFactoryError("SF-16 runtime workspace SHA-256 is invalid")
    if not evidence.passed:
        raise SoftwareFactoryError("SF-16 requires passing canonical runtime evidence")
    stages = tuple(step.stage for step in evidence.steps)
    if stages != _REQUIRED_RUNTIME_STAGES:
        raise SoftwareFactoryError(
            "SF-16 runtime evidence must preserve the exact canonical SF-6 lifecycle"
        )
    for step in evidence.steps:
        _validate_runtime_step(step)
    return evidence


def _validate_runtime_step(step: RuntimeStepResult) -> None:
    if not _trimmed(step.stage):
        raise SoftwareFactoryError("SF-16 runtime stage identity is required")
    if not step.command or any(not _trimmed(token) for token in step.command):
        raise SoftwareFactoryError("SF-16 runtime command evidence is incomplete")
    if step.exit_code != 0 or not step.passed:
        raise SoftwareFactoryError("SF-16 runtime lifecycle contains a failed step")
    for label, value in (
        ("stdout", step.stdout_sha256),
        ("stderr", step.stderr_sha256),
    ):
        if _SHA256.fullmatch(value) is None:
            raise SoftwareFactoryError(f"SF-16 runtime {label} SHA-256 is invalid")


def _validate_builder(builder: BuilderIdentity) -> BuilderIdentity:
    for label, value in (
        ("builder_id", builder.builder_id),
        ("workflow_id", builder.workflow_id),
        ("workflow_run_id", builder.workflow_run_id),
        ("runner_environment", builder.runner_environment),
        ("evidence_reference", builder.evidence_reference),
    ):
        if not _trimmed(value):
            raise SoftwareFactoryError(f"SF-16 builder {label} is required")
    if not builder.source_checkout_read_only:
        raise SoftwareFactoryError(
            "SF-16 build provenance requires a read-only source checkout boundary"
        )
    if not builder.ephemeral:
        raise SoftwareFactoryError(
            "SF-16 build provenance requires an ephemeral builder identity"
        )
    return builder


def _validate_artifacts(
    artifacts: tuple[BuildArtifactInput, ...],
    *,
    sbom: SoftwareSBOMDocument,
    runtime: RuntimeEvidence,
    builder_sha256: str,
) -> tuple[BuildArtifactEvidence, ...]:
    if not artifacts:
        raise SoftwareFactoryError("SF-16 requires at least one build/package artifact")
    successful_stages = {step.stage for step in runtime.steps if step.passed}
    source_paths = {
        path
        for component in sbom.components
        for path in component.repository_paths
    }
    seen_references: set[str] = set()
    seen_paths: set[str] = set()
    validated: list[BuildArtifactEvidence] = []
    for artifact in artifacts:
        if not _trimmed(artifact.artifact_reference):
            raise SoftwareFactoryError("SF-16 artifact reference is required")
        if artifact.artifact_reference in seen_references:
            raise SoftwareFactoryError("SF-16 artifact references must be unique")
        seen_references.add(artifact.artifact_reference)
        path = _normalize_relative_path(artifact.relative_path)
        if path in seen_paths:
            raise SoftwareFactoryError("SF-16 artifact paths must be unique")
        seen_paths.add(path)
        if path in source_paths:
            raise SoftwareFactoryError(
                "SF-16 build artifact path cannot overwrite reviewed source input"
            )
        if _SHA256.fullmatch(artifact.artifact_sha256) is None:
            raise SoftwareFactoryError("SF-16 artifact SHA-256 is invalid")
        if artifact.size_bytes <= 0:
            raise SoftwareFactoryError("SF-16 artifact size must be positive")
        if not _trimmed(artifact.media_type):
            raise SoftwareFactoryError("SF-16 artifact media type is required")
        if artifact.producing_stage not in _ARTIFACT_STAGES:
            raise SoftwareFactoryError(
                "SF-16 artifact must originate from canonical build or package stage"
            )
        if artifact.producing_stage not in successful_stages:
            raise SoftwareFactoryError(
                "SF-16 artifact references a runtime stage that did not pass"
            )
        material = {
            "artifact_reference": artifact.artifact_reference,
            "relative_path": path,
            "artifact_sha256": artifact.artifact_sha256,
            "size_bytes": artifact.size_bytes,
            "media_type": artifact.media_type,
            "producing_stage": artifact.producing_stage,
            "repository_base_sha": sbom.repository_base_sha,
            "changeset_sha256": sbom.changeset_sha256,
            "sbom_document_sha256": sbom.document_sha256,
            "runtime_workspace_sha256": runtime.workspace_sha256,
            "builder_sha256": builder_sha256,
        }
        validated.append(
            BuildArtifactEvidence(
                artifact_reference=artifact.artifact_reference,
                relative_path=path,
                artifact_sha256=artifact.artifact_sha256,
                size_bytes=artifact.size_bytes,
                media_type=artifact.media_type,
                producing_stage=artifact.producing_stage,
                repository_base_sha=sbom.repository_base_sha,
                changeset_sha256=sbom.changeset_sha256,
                sbom_document_sha256=sbom.document_sha256,
                runtime_workspace_sha256=runtime.workspace_sha256,
                builder_sha256=builder_sha256,
                evidence_sha256=canonical_sha256(material),
            )
        )
    return tuple(sorted(validated, key=lambda item: item.artifact_reference))


def _normalize_relative_path(path: str) -> str:
    if not _trimmed(path) or path.startswith(("/", "\\")):
        raise SoftwareFactoryError("SF-16 artifact path must be repository-relative")
    normalized = path.replace("\\", "/")
    if any(part in {"", ".", ".."} for part in normalized.split("/")):
        raise SoftwareFactoryError("SF-16 artifact path must be normalized")
    return normalized


def _map_disposition(disposition: LicenseDisposition) -> BuildDisposition:
    return BuildDisposition(disposition.value)


def _runtime_material(evidence: RuntimeEvidence) -> dict[str, object]:
    return {
        "adapter_id": evidence.adapter_id,
        "workspace_sha256": evidence.workspace_sha256,
        "passed": evidence.passed,
        "steps": [_runtime_step_material(step) for step in evidence.steps],
    }


def _runtime_step_material(step: RuntimeStepResult) -> dict[str, object]:
    return {
        "stage": step.stage,
        "command": list(step.command),
        "exit_code": step.exit_code,
        "stdout_sha256": step.stdout_sha256,
        "stderr_sha256": step.stderr_sha256,
        "passed": step.passed,
    }


def _builder_material(builder: BuilderIdentity) -> dict[str, object]:
    return {
        "builder_id": builder.builder_id,
        "workflow_id": builder.workflow_id,
        "workflow_run_id": builder.workflow_run_id,
        "runner_environment": builder.runner_environment,
        "source_checkout_read_only": builder.source_checkout_read_only,
        "ephemeral": builder.ephemeral,
        "evidence_reference": builder.evidence_reference,
    }


def _artifact_material(artifact: BuildArtifactEvidence) -> dict[str, object]:
    return {
        "artifact_reference": artifact.artifact_reference,
        "relative_path": artifact.relative_path,
        "artifact_sha256": artifact.artifact_sha256,
        "size_bytes": artifact.size_bytes,
        "media_type": artifact.media_type,
        "producing_stage": artifact.producing_stage,
        "repository_base_sha": artifact.repository_base_sha,
        "changeset_sha256": artifact.changeset_sha256,
        "sbom_document_sha256": artifact.sbom_document_sha256,
        "runtime_workspace_sha256": artifact.runtime_workspace_sha256,
        "builder_sha256": artifact.builder_sha256,
        "evidence_sha256": artifact.evidence_sha256,
    }


def _record_material(
    *,
    request: BuildProvenanceRequest,
    package: SkillPackage,
    sbom: SoftwareSBOMDocument,
    runtime: RuntimeEvidence,
    runtime_sha256: str,
    builder: BuilderIdentity,
    builder_sha256: str,
    artifacts: tuple[BuildArtifactEvidence, ...],
    disposition: BuildDisposition,
    risk_flags: tuple[str, ...],
    evidence_references: tuple[str, ...],
) -> dict[str, object]:
    return {
        "build_id": request.build_id,
        "contract_version": BUILD_PROVENANCE_CONTRACT_VERSION,
        "skill_id": package.manifest.skill_id,
        "skill_version": package.manifest.version,
        "tenant_id": sbom.tenant_id,
        "task_id": sbom.task_id,
        "correlation_id": sbom.correlation_id,
        "factory_job_id": sbom.factory_job_id,
        "repository_base_sha": sbom.repository_base_sha,
        "changeset_sha256": sbom.changeset_sha256,
        "sbom_document_sha256": sbom.document_sha256,
        "sbom_serial_number": sbom.serial_number,
        "runtime_adapter_id": runtime.adapter_id,
        "runtime_workspace_sha256": runtime.workspace_sha256,
        "runtime_evidence_sha256": runtime_sha256,
        "builder": _builder_material(builder),
        "builder_sha256": builder_sha256,
        "artifacts": [_artifact_material(item) for item in artifacts],
        "disposition": disposition.value,
        "risk_flags": list(risk_flags),
        "evidence_references": list(evidence_references),
        "build_succeeded": True,
        "build_provenance_bound": True,
        "signing_attestation_bound": False,
        "release_complete": False,
        "acceptance_authorized": False,
        "promotion_authorized": False,
        "deployment_authorized": False,
        "production_applied": False,
        "subject_mutated": False,
    }


def _trimmed(value: str) -> bool:
    return bool(value) and value == value.strip()
