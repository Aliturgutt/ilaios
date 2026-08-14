"""SF-17 signing and attestation for governed Software Factory build outputs.

SF-17 binds exact SF-16 build provenance to a deterministic attestation
statement and a trusted signing boundary.  Private-key material never enters
this service.  A host-provided KMS/HSM/signing service is responsible for the
cryptographic operation and verification; ILAIOS validates the returned public
identity and verification evidence fail-closed.

This phase does not publish, promote, deploy, or claim release completeness.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from services.software_factory import SoftwareFactoryError
from services.software_factory_build_provenance import (
    BuildDisposition,
    BuildProvenanceRecord,
    BuildProvenanceRequest,
    SoftwareFactoryBuildProvenance,
)
from services.software_factory_skills import SkillRegistry
from src.core.validation_pipeline import canonical_sha256

SIGNING_ATTESTATION_CONTRACT_VERSION = "1.0.0"
ATTESTATION_STATEMENT_TYPE = "ILAIOS-SIGNED-BUILD-ATTESTATION"
ATTESTATION_STATEMENT_VERSION = "1.0"
ATTESTATION_PREDICATE_TYPE = "ilaios.software-factory.build-provenance.v1"
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SUPPORTED_SIGNATURE_ALGORITHMS = frozenset(
    {"ed25519", "ecdsa-p256-sha256", "rsa-pss-sha256"}
)


class AttestationDisposition(str, Enum):
    ALLOW = "ALLOW"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class TrustedSigningKey:
    signer_id: str
    key_id: str
    key_version: str
    algorithm: str
    public_key_sha256: str
    hardware_backed: bool
    active: bool
    trust_root_reference: str


@dataclass(frozen=True, slots=True)
class SigningAttestationPolicy:
    policy_id: str
    trusted_keys: tuple[TrustedSigningKey, ...]
    require_hardware_backed: bool = True
    max_signature_bytes: int = 8192


@dataclass(frozen=True, slots=True)
class SigningTarget:
    signer_id: str
    key_id: str
    key_version: str


@dataclass(frozen=True, slots=True)
class AttestationSubject:
    artifact_reference: str
    relative_path: str
    artifact_sha256: str
    size_bytes: int
    media_type: str
    build_artifact_evidence_sha256: str


@dataclass(frozen=True, slots=True)
class BuildAttestationStatement:
    statement_type: str
    statement_version: str
    predicate_type: str
    attestation_id: str
    tenant_id: str
    task_id: str
    correlation_id: str
    factory_job_id: str
    repository_base_sha: str
    changeset_sha256: str
    sbom_document_sha256: str
    sbom_serial_number: str
    build_provenance_record_sha256: str
    runtime_evidence_sha256: str
    builder_sha256: str
    builder_id: str
    workflow_id: str
    workflow_run_id: str
    build_disposition: BuildDisposition
    build_risk_flags: tuple[str, ...]
    subjects: tuple[AttestationSubject, ...]


@dataclass(frozen=True, slots=True)
class SignatureEnvelope:
    signer_id: str
    key_id: str
    key_version: str
    algorithm: str
    public_key_sha256: str
    statement_sha256: str
    signature_base64: str
    signing_evidence_reference: str


@dataclass(frozen=True, slots=True)
class SignatureVerification:
    verified: bool
    signer_id: str
    key_id: str
    key_version: str
    algorithm: str
    public_key_sha256: str
    statement_sha256: str
    signature_sha256: str
    trust_policy_id: str
    hardware_backed: bool
    key_active: bool
    verification_reference: str


class SigningBoundary(Protocol):
    """Secure external signing boundary; no private key crosses this interface."""

    def sign(
        self,
        statement: bytes,
        key: TrustedSigningKey,
        policy: SigningAttestationPolicy,
    ) -> SignatureEnvelope: ...

    def verify(
        self,
        statement: bytes,
        envelope: SignatureEnvelope,
        key: TrustedSigningKey,
        policy: SigningAttestationPolicy,
    ) -> SignatureVerification: ...


class UnavailableSigningBoundary:
    """Fail closed until a host supplies a trusted KMS/HSM/signing boundary."""

    def sign(
        self,
        statement: bytes,
        key: TrustedSigningKey,
        policy: SigningAttestationPolicy,
    ) -> SignatureEnvelope:
        del statement, key, policy
        raise SoftwareFactoryError("secure signing boundary is unavailable")

    def verify(
        self,
        statement: bytes,
        envelope: SignatureEnvelope,
        key: TrustedSigningKey,
        policy: SigningAttestationPolicy,
    ) -> SignatureVerification:
        del statement, envelope, key, policy
        raise SoftwareFactoryError("secure signing boundary is unavailable")


@dataclass(frozen=True, slots=True)
class SigningAttestationRequest:
    attestation_id: str
    build_request: BuildProvenanceRequest
    build_record: BuildProvenanceRecord
    signing_target: SigningTarget
    policy: SigningAttestationPolicy


@dataclass(frozen=True, slots=True)
class SigningAttestationRecord:
    attestation_id: str
    contract_version: str
    statement: BuildAttestationStatement
    statement_sha256: str
    signature: SignatureEnvelope
    signature_sha256: str
    verification: SignatureVerification
    verification_sha256: str
    trust_policy_sha256: str
    build_provenance_record_sha256: str
    sbom_document_sha256: str
    repository_base_sha: str
    changeset_sha256: str
    subjects: tuple[AttestationSubject, ...]
    disposition: AttestationDisposition
    risk_flags: tuple[str, ...]
    evidence_references: tuple[str, ...]
    signed: bool
    signature_verified: bool
    build_provenance_bound: bool
    signing_attestation_bound: bool
    release_complete: bool
    publication_authorized: bool
    acceptance_authorized: bool
    promotion_authorized: bool
    deployment_authorized: bool
    production_applied: bool
    subject_mutated: bool
    record_sha256: str


class SoftwareFactorySigningAttestation:
    """Create verified SF-17 signing/attestation evidence for exact SF-16 output."""

    def __init__(self, registry: SkillRegistry, boundary: SigningBoundary) -> None:
        self._registry = registry
        self._boundary = boundary

    def attest(self, request: SigningAttestationRequest) -> SigningAttestationRecord:
        _validate_request_identity(request)
        policy = _validate_policy(request.policy)
        key = _resolve_trusted_key(policy, request.signing_target)

        build = SoftwareFactoryBuildProvenance(self._registry).generate(
            request.build_request
        )
        if build != request.build_record:
            raise SoftwareFactoryError(
                "SF-17 build provenance record is stale, tampered, or mismatched"
            )
        _validate_build_boundary(build)

        statement = _statement_from_build(request.attestation_id, build)
        statement_bytes = render_attestation_statement_json(statement).encode("utf-8")
        statement_sha256 = canonical_sha256(_statement_material(statement))

        envelope = self._boundary.sign(statement_bytes, key, policy)
        signature_bytes, signature_sha256 = _validate_signature_envelope(
            envelope,
            statement_sha256=statement_sha256,
            key=key,
            policy=policy,
        )
        del signature_bytes

        verification = self._boundary.verify(statement_bytes, envelope, key, policy)
        _validate_verification(
            verification,
            statement_sha256=statement_sha256,
            signature_sha256=signature_sha256,
            key=key,
            policy=policy,
        )

        disposition = AttestationDisposition(build.disposition.value)
        if disposition is AttestationDisposition.BLOCK:
            raise SoftwareFactoryError(
                "SF-17 cannot attest an upstream BLOCK build disposition"
            )
        risk_flags = set(build.risk_flags)
        if disposition is AttestationDisposition.REVIEW_REQUIRED:
            risk_flags.add("UPSTREAM_BUILD_REVIEW_REQUIRED")
        normalized_risk_flags = tuple(sorted(risk_flags))
        evidence_references = tuple(
            sorted(
                set(build.evidence_references)
                | {
                    key.trust_root_reference,
                    envelope.signing_evidence_reference,
                    verification.verification_reference,
                }
            )
        )
        verification_sha256 = canonical_sha256(_verification_material(verification))
        trust_policy_sha256 = canonical_sha256(_policy_material(policy))
        record_material = {
            "attestation_id": request.attestation_id,
            "contract_version": SIGNING_ATTESTATION_CONTRACT_VERSION,
            "statement_sha256": statement_sha256,
            "signature_sha256": signature_sha256,
            "signature": _signature_material(envelope),
            "verification_sha256": verification_sha256,
            "trust_policy_sha256": trust_policy_sha256,
            "build_provenance_record_sha256": build.record_sha256,
            "sbom_document_sha256": build.sbom_document_sha256,
            "repository_base_sha": build.repository_base_sha,
            "changeset_sha256": build.changeset_sha256,
            "subjects": [_subject_material(item) for item in statement.subjects],
            "disposition": disposition.value,
            "risk_flags": list(normalized_risk_flags),
            "evidence_references": list(evidence_references),
            "signed": True,
            "signature_verified": True,
            "build_provenance_bound": True,
            "signing_attestation_bound": True,
            "release_complete": False,
            "publication_authorized": False,
            "acceptance_authorized": False,
            "promotion_authorized": False,
            "deployment_authorized": False,
            "production_applied": False,
            "subject_mutated": False,
        }
        return SigningAttestationRecord(
            attestation_id=request.attestation_id,
            contract_version=SIGNING_ATTESTATION_CONTRACT_VERSION,
            statement=statement,
            statement_sha256=statement_sha256,
            signature=envelope,
            signature_sha256=signature_sha256,
            verification=verification,
            verification_sha256=verification_sha256,
            trust_policy_sha256=trust_policy_sha256,
            build_provenance_record_sha256=build.record_sha256,
            sbom_document_sha256=build.sbom_document_sha256,
            repository_base_sha=build.repository_base_sha,
            changeset_sha256=build.changeset_sha256,
            subjects=statement.subjects,
            disposition=disposition,
            risk_flags=normalized_risk_flags,
            evidence_references=evidence_references,
            signed=True,
            signature_verified=True,
            build_provenance_bound=True,
            signing_attestation_bound=True,
            release_complete=False,
            publication_authorized=False,
            acceptance_authorized=False,
            promotion_authorized=False,
            deployment_authorized=False,
            production_applied=False,
            subject_mutated=False,
            record_sha256=canonical_sha256(record_material),
        )


def render_attestation_statement(statement: BuildAttestationStatement) -> dict[str, object]:
    """Render stable JSON-compatible attestation statement material."""

    return {
        "type": statement.statement_type,
        "version": statement.statement_version,
        "predicateType": statement.predicate_type,
        "attestationId": statement.attestation_id,
        "identity": {
            "tenantId": statement.tenant_id,
            "taskId": statement.task_id,
            "correlationId": statement.correlation_id,
            "factoryJobId": statement.factory_job_id,
        },
        "source": {
            "repositoryBaseSha": statement.repository_base_sha,
            "changeSetSha256": statement.changeset_sha256,
        },
        "supplyChain": {
            "sbomDocumentSha256": statement.sbom_document_sha256,
            "sbomSerialNumber": statement.sbom_serial_number,
            "buildProvenanceRecordSha256": statement.build_provenance_record_sha256,
            "runtimeEvidenceSha256": statement.runtime_evidence_sha256,
            "builderSha256": statement.builder_sha256,
        },
        "builder": {
            "builderId": statement.builder_id,
            "workflowId": statement.workflow_id,
            "workflowRunId": statement.workflow_run_id,
        },
        "policy": {
            "buildDisposition": statement.build_disposition.value,
            "buildRiskFlags": list(statement.build_risk_flags),
        },
        "subjects": [_subject_material(item) for item in statement.subjects],
    }


def render_attestation_statement_json(statement: BuildAttestationStatement) -> str:
    return json.dumps(
        render_attestation_statement(statement),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _validate_request_identity(request: SigningAttestationRequest) -> None:
    if not _trimmed(request.attestation_id):
        raise SoftwareFactoryError("SF-17 attestation_id must be non-blank and trimmed")
    if len(request.attestation_id) > 160:
        raise SoftwareFactoryError("SF-17 attestation_id exceeds bounded identifier length")
    for label, value in (
        ("signer_id", request.signing_target.signer_id),
        ("key_id", request.signing_target.key_id),
        ("key_version", request.signing_target.key_version),
    ):
        if not _trimmed(value):
            raise SoftwareFactoryError(f"SF-17 signing target {label} is required")


def _validate_policy(policy: SigningAttestationPolicy) -> SigningAttestationPolicy:
    if not _trimmed(policy.policy_id):
        raise SoftwareFactoryError("SF-17 signing policy identity is required")
    if not policy.trusted_keys:
        raise SoftwareFactoryError("SF-17 signing policy requires at least one trusted key")
    if policy.max_signature_bytes < 32 or policy.max_signature_bytes > 65536:
        raise SoftwareFactoryError("SF-17 signing policy signature bound is invalid")
    seen: set[tuple[str, str, str]] = set()
    for key in policy.trusted_keys:
        identity = (key.signer_id, key.key_id, key.key_version)
        if identity in seen:
            raise SoftwareFactoryError("SF-17 signing policy contains duplicate key identity")
        seen.add(identity)
        for label, value in (
            ("signer_id", key.signer_id),
            ("key_id", key.key_id),
            ("key_version", key.key_version),
            ("algorithm", key.algorithm),
            ("trust_root_reference", key.trust_root_reference),
        ):
            if not _trimmed(value):
                raise SoftwareFactoryError(f"SF-17 trusted key {label} is required")
        if key.algorithm not in _SUPPORTED_SIGNATURE_ALGORITHMS:
            raise SoftwareFactoryError("SF-17 trusted key algorithm is unsupported")
        if _SHA256.fullmatch(key.public_key_sha256) is None:
            raise SoftwareFactoryError("SF-17 trusted public-key SHA-256 is invalid")
    return policy


def _resolve_trusted_key(
    policy: SigningAttestationPolicy,
    target: SigningTarget,
) -> TrustedSigningKey:
    matches = tuple(
        key
        for key in policy.trusted_keys
        if (
            key.signer_id == target.signer_id
            and key.key_id == target.key_id
            and key.key_version == target.key_version
        )
    )
    if len(matches) != 1:
        raise SoftwareFactoryError("SF-17 signing target is not uniquely trusted by policy")
    key = matches[0]
    if not key.active:
        raise SoftwareFactoryError("SF-17 signing key is inactive or revoked")
    if policy.require_hardware_backed and not key.hardware_backed:
        raise SoftwareFactoryError("SF-17 policy requires a hardware-backed signing key")
    return key


def _validate_build_boundary(build: BuildProvenanceRecord) -> None:
    if not build.build_succeeded or not build.build_provenance_bound:
        raise SoftwareFactoryError("SF-17 requires complete passing SF-16 build provenance")
    if build.signing_attestation_bound:
        raise SoftwareFactoryError("SF-17 expects pre-attestation SF-16 evidence")
    if build.release_complete:
        raise SoftwareFactoryError("SF-17 cannot consume a build claiming release completeness")
    if (
        build.acceptance_authorized
        or build.promotion_authorized
        or build.deployment_authorized
        or build.production_applied
        or build.subject_mutated
    ):
        raise SoftwareFactoryError(
            "SF-17 cannot consume build evidence carrying downstream authority"
        )
    if _SHA1.fullmatch(build.repository_base_sha) is None:
        raise SoftwareFactoryError("SF-17 repository base SHA is invalid")
    for label, value in (
        ("ChangeSet", build.changeset_sha256),
        ("SBOM", build.sbom_document_sha256),
        ("build provenance", build.record_sha256),
        ("runtime evidence", build.runtime_evidence_sha256),
        ("builder", build.builder_sha256),
    ):
        if _SHA256.fullmatch(value) is None:
            raise SoftwareFactoryError(f"SF-17 {label} SHA-256 is invalid")
    if not build.artifacts:
        raise SoftwareFactoryError("SF-17 requires signed build artifact subjects")


def _statement_from_build(
    attestation_id: str,
    build: BuildProvenanceRecord,
) -> BuildAttestationStatement:
    subjects = tuple(
        sorted(
            (
                AttestationSubject(
                    artifact_reference=item.artifact_reference,
                    relative_path=item.relative_path,
                    artifact_sha256=item.artifact_sha256,
                    size_bytes=item.size_bytes,
                    media_type=item.media_type,
                    build_artifact_evidence_sha256=item.evidence_sha256,
                )
                for item in build.artifacts
            ),
            key=lambda item: item.artifact_reference,
        )
    )
    return BuildAttestationStatement(
        statement_type=ATTESTATION_STATEMENT_TYPE,
        statement_version=ATTESTATION_STATEMENT_VERSION,
        predicate_type=ATTESTATION_PREDICATE_TYPE,
        attestation_id=attestation_id,
        tenant_id=build.tenant_id,
        task_id=build.task_id,
        correlation_id=build.correlation_id,
        factory_job_id=build.factory_job_id,
        repository_base_sha=build.repository_base_sha,
        changeset_sha256=build.changeset_sha256,
        sbom_document_sha256=build.sbom_document_sha256,
        sbom_serial_number=build.sbom_serial_number,
        build_provenance_record_sha256=build.record_sha256,
        runtime_evidence_sha256=build.runtime_evidence_sha256,
        builder_sha256=build.builder_sha256,
        builder_id=build.builder.builder_id,
        workflow_id=build.builder.workflow_id,
        workflow_run_id=build.builder.workflow_run_id,
        build_disposition=build.disposition,
        build_risk_flags=build.risk_flags,
        subjects=subjects,
    )


def _validate_signature_envelope(
    envelope: SignatureEnvelope,
    *,
    statement_sha256: str,
    key: TrustedSigningKey,
    policy: SigningAttestationPolicy,
) -> tuple[bytes, str]:
    expected = (
        ("signer_id", envelope.signer_id, key.signer_id),
        ("key_id", envelope.key_id, key.key_id),
        ("key_version", envelope.key_version, key.key_version),
        ("algorithm", envelope.algorithm, key.algorithm),
        ("public_key_sha256", envelope.public_key_sha256, key.public_key_sha256),
        ("statement_sha256", envelope.statement_sha256, statement_sha256),
    )
    for label, actual, wanted in expected:
        if actual != wanted:
            raise SoftwareFactoryError(f"SF-17 signature envelope {label} binding mismatch")
    if not _trimmed(envelope.signing_evidence_reference):
        raise SoftwareFactoryError("SF-17 signing evidence reference is required")
    try:
        signature = base64.b64decode(envelope.signature_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SoftwareFactoryError("SF-17 signature is not valid base64") from exc
    if not signature:
        raise SoftwareFactoryError("SF-17 signature must not be empty")
    if len(signature) > policy.max_signature_bytes:
        raise SoftwareFactoryError("SF-17 signature exceeds policy byte bound")
    return signature, canonical_sha256(signature.hex())


def _validate_verification(
    verification: SignatureVerification,
    *,
    statement_sha256: str,
    signature_sha256: str,
    key: TrustedSigningKey,
    policy: SigningAttestationPolicy,
) -> None:
    if not verification.verified:
        raise SoftwareFactoryError("SF-17 cryptographic signature verification failed")
    expected = (
        ("signer_id", verification.signer_id, key.signer_id),
        ("key_id", verification.key_id, key.key_id),
        ("key_version", verification.key_version, key.key_version),
        ("algorithm", verification.algorithm, key.algorithm),
        ("public_key_sha256", verification.public_key_sha256, key.public_key_sha256),
        ("statement_sha256", verification.statement_sha256, statement_sha256),
        ("signature_sha256", verification.signature_sha256, signature_sha256),
        ("trust_policy_id", verification.trust_policy_id, policy.policy_id),
    )
    for label, actual, wanted in expected:
        if actual != wanted:
            raise SoftwareFactoryError(f"SF-17 verification {label} binding mismatch")
    if not verification.key_active:
        raise SoftwareFactoryError("SF-17 verification reports an inactive/revoked key")
    if policy.require_hardware_backed and not verification.hardware_backed:
        raise SoftwareFactoryError(
            "SF-17 verification did not prove the required hardware-backed key boundary"
        )
    if not _trimmed(verification.verification_reference):
        raise SoftwareFactoryError("SF-17 verification evidence reference is required")


def _statement_material(statement: BuildAttestationStatement) -> dict[str, object]:
    return render_attestation_statement(statement)


def _subject_material(subject: AttestationSubject) -> dict[str, object]:
    return {
        "artifactReference": subject.artifact_reference,
        "relativePath": subject.relative_path,
        "sha256": subject.artifact_sha256,
        "sizeBytes": subject.size_bytes,
        "mediaType": subject.media_type,
        "buildArtifactEvidenceSha256": subject.build_artifact_evidence_sha256,
    }


def _signature_material(envelope: SignatureEnvelope) -> dict[str, object]:
    return {
        "signer_id": envelope.signer_id,
        "key_id": envelope.key_id,
        "key_version": envelope.key_version,
        "algorithm": envelope.algorithm,
        "public_key_sha256": envelope.public_key_sha256,
        "statement_sha256": envelope.statement_sha256,
        "signature_base64": envelope.signature_base64,
        "signing_evidence_reference": envelope.signing_evidence_reference,
    }


def _verification_material(verification: SignatureVerification) -> dict[str, object]:
    return {
        "verified": verification.verified,
        "signer_id": verification.signer_id,
        "key_id": verification.key_id,
        "key_version": verification.key_version,
        "algorithm": verification.algorithm,
        "public_key_sha256": verification.public_key_sha256,
        "statement_sha256": verification.statement_sha256,
        "signature_sha256": verification.signature_sha256,
        "trust_policy_id": verification.trust_policy_id,
        "hardware_backed": verification.hardware_backed,
        "key_active": verification.key_active,
        "verification_reference": verification.verification_reference,
    }


def _policy_material(policy: SigningAttestationPolicy) -> dict[str, object]:
    return {
        "policy_id": policy.policy_id,
        "require_hardware_backed": policy.require_hardware_backed,
        "max_signature_bytes": policy.max_signature_bytes,
        "trusted_keys": [
            {
                "signer_id": key.signer_id,
                "key_id": key.key_id,
                "key_version": key.key_version,
                "algorithm": key.algorithm,
                "public_key_sha256": key.public_key_sha256,
                "hardware_backed": key.hardware_backed,
                "active": key.active,
                "trust_root_reference": key.trust_root_reference,
            }
            for key in sorted(
                policy.trusted_keys,
                key=lambda item: (item.signer_id, item.key_id, item.key_version),
            )
        ],
    }


def _trimmed(value: str) -> bool:
    return bool(value) and value == value.strip()
