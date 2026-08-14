"""SF-13 dependency governance over independently reviewed Software Factory changes.

This gate operationalizes the canonical first-party ``sf-dependency-governance``
skill. It consumes exact SF-12 evidence, evaluates only reviewed dependency
manifest/lockfile changes, and emits deterministic policy evidence without
acceptance, promotion, deployment, production, or mutation authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from services.software_factory import SoftwareFactoryError
from services.software_factory_review import (
    IndependentReviewRecord,
    ReviewDecision,
    SoftwareFactoryIndependentReview,
    SoftwareIndependentReviewRequest,
)
from services.software_factory_skills import SkillPackage, SkillRegistry
from src.core.validation_pipeline import canonical_sha256

DEPENDENCY_SKILL_ID = "sf-dependency-governance"
DEPENDENCY_CONTRACT_VERSION = "1.0.0"
_SHA1 = re.compile(r"^[0-9a-f]{40}$")


class DependencyDisposition(str, Enum):
    ALLOW = "ALLOW"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCK = "BLOCK"


class DependencyRole(str, Enum):
    DIRECT = "DIRECT"
    TRANSITIVE = "TRANSITIVE"


class DependencyOperation(str, Enum):
    ADD = "ADD"
    UPDATE = "UPDATE"
    REMOVE = "REMOVE"


class DependencySecurityStatus(str, Enum):
    CLEAR = "CLEAR"
    VULNERABLE = "VULNERABLE"
    UNKNOWN = "UNKNOWN"


class CommercialCompatibility(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class DependencyPolicy:
    """Explicit supply-chain policy; classifications are policy inputs."""

    policy_id: str
    allowed_sources: frozenset[str]
    allowed_licenses: frozenset[str]
    review_licenses: frozenset[str]
    blocked_licenses: frozenset[str]
    unknown_license_disposition: DependencyDisposition = DependencyDisposition.REVIEW_REQUIRED
    unknown_security_disposition: DependencyDisposition = DependencyDisposition.REVIEW_REQUIRED
    unknown_commercial_disposition: DependencyDisposition = DependencyDisposition.REVIEW_REQUIRED
    require_verified_integrity: bool = True


@dataclass(frozen=True, slots=True)
class DependencyChange:
    package: str
    version: str
    source: str
    role: DependencyRole
    reason: str
    integrity: str
    integrity_verified: bool
    security_status: DependencySecurityStatus
    license: str
    commercial_compatibility: CommercialCompatibility
    operation: DependencyOperation
    manifest_path: str | None = None
    lockfile_path: str | None = None


@dataclass(frozen=True, slots=True)
class DependencyEvidence:
    package: str
    version: str
    source: str
    role: DependencyRole
    reason: str
    integrity: str
    integrity_verified: bool
    security_status: DependencySecurityStatus
    license: str
    commercial_compatibility: CommercialCompatibility
    operation: DependencyOperation
    manifest_path: str | None
    lockfile_path: str | None
    disposition: DependencyDisposition
    policy_reasons: tuple[str, ...]
    evidence_sha256: str


@dataclass(frozen=True, slots=True)
class DependencyGovernanceRequest:
    governance_id: str
    review_request: SoftwareIndependentReviewRequest
    review_record: IndependentReviewRecord
    dependency_changes: tuple[DependencyChange, ...]
    policy: DependencyPolicy


@dataclass(frozen=True, slots=True)
class DependencyGovernanceRecord:
    governance_id: str
    contract_version: str
    skill_id: str
    skill_version: str
    policy_id: str
    policy_sha256: str
    tenant_id: str
    task_id: str
    correlation_id: str
    repository_sha: str
    review_record_sha256: str
    validation_report_sha256: str
    dependency_paths: tuple[str, ...]
    dependency_evidence: tuple[DependencyEvidence, ...]
    disposition: DependencyDisposition
    policy_reasons: tuple[str, ...]
    independent_review_required: bool
    acceptance_authorized: bool
    promotion_authorized: bool
    deployment_authorized: bool
    production_applied: bool
    subject_mutated: bool
    record_sha256: str


class SoftwareFactoryDependencyGovernance:
    """Fail-closed SF-13 gate bound to canonical SF-7 and SF-12 evidence."""

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    def evaluate(self, request: DependencyGovernanceRequest) -> DependencyGovernanceRecord:
        package = self._validate_skill_contract()
        review = self._validate_review_binding(request)
        policy = self._validate_policy(request.policy)
        repository_sha = (
            request.review_request.validation_request.software_proposal.evidence.repository_sha
        )
        if _SHA1.fullmatch(repository_sha) is None:
            raise SoftwareFactoryError("SF-13 requires a lowercase repository SHA")

        dependency_paths = tuple(
            path for path in review.changed_paths if _is_dependency_path(path)
        )
        changes = self._validate_change_scope(request.dependency_changes, dependency_paths)
        evidence = tuple(self._evaluate_change(change, policy) for change in changes)
        policy_reasons: tuple[str, ...] = ()
        if dependency_paths and not evidence:
            policy_reasons = (
                "reviewed dependency manifest/lockfile changed without explained dependency inventory",
            )
        disposition = _aggregate_disposition(
            tuple(item.disposition for item in evidence),
            force_block=bool(policy_reasons),
        )
        policy_sha256 = canonical_sha256(_policy_material(policy))
        material = _record_material(
            request,
            package,
            review,
            repository_sha,
            dependency_paths,
            evidence,
            disposition,
            policy_reasons,
            policy_sha256,
        )
        return DependencyGovernanceRecord(
            governance_id=request.governance_id,
            contract_version=DEPENDENCY_CONTRACT_VERSION,
            skill_id=package.manifest.skill_id,
            skill_version=package.manifest.version,
            policy_id=policy.policy_id,
            policy_sha256=policy_sha256,
            tenant_id=review.tenant_id,
            task_id=review.task_id,
            correlation_id=review.correlation_id,
            repository_sha=repository_sha,
            review_record_sha256=review.record_sha256,
            validation_report_sha256=review.validation_report_sha256,
            dependency_paths=dependency_paths,
            dependency_evidence=evidence,
            disposition=disposition,
            policy_reasons=policy_reasons,
            independent_review_required=package.manifest.independent_review_required,
            acceptance_authorized=False,
            promotion_authorized=False,
            deployment_authorized=False,
            production_applied=False,
            subject_mutated=False,
            record_sha256=canonical_sha256(material),
        )

    def _validate_skill_contract(self) -> SkillPackage:
        package = self._registry.resolve(DEPENDENCY_SKILL_ID)
        manifest = package.manifest
        if manifest.domain != "supply-chain-commercial":
            raise SoftwareFactoryError(
                "SF-13 dependency skill is outside canonical supply-chain-commercial domain"
            )
        if not manifest.independent_review_required:
            raise SoftwareFactoryError(
                "SF-13 dependency skill lost its independent-review requirement"
            )
        required_inputs = {"intent", "dependency_changes"}
        if not required_inputs.issubset(manifest.inputs):
            raise SoftwareFactoryError(
                "SF-13 dependency skill lost canonical dependency inputs"
            )
        required_outputs = {"dependencies", "policy_disposition", "evidence_references"}
        if not required_outputs.issubset(manifest.outputs):
            raise SoftwareFactoryError(
                "SF-13 dependency skill lost canonical dependency outputs"
            )
        required_evidence = {"policy_decision", "provenance", "reviewer"}
        if not required_evidence.issubset(manifest.emitted_evidence):
            raise SoftwareFactoryError(
                "SF-13 dependency skill lost canonical governance evidence"
            )
        return package

    def _validate_review_binding(
        self, request: DependencyGovernanceRequest
    ) -> IndependentReviewRecord:
        if not _trimmed(request.governance_id):
            raise SoftwareFactoryError(
                "SF-13 governance_id must be non-blank and trimmed"
            )
        regenerated = SoftwareFactoryIndependentReview(self._registry).review(
            request.review_request
        )
        if regenerated != request.review_record:
            raise SoftwareFactoryError(
                "SF-13 independent-review record is stale or tampered"
            )
        if (
            regenerated.decision is not ReviewDecision.APPROVE
            or not regenerated.review_complete
        ):
            raise SoftwareFactoryError(
                "SF-13 requires a completed, approved SF-12 independent review"
            )
        if (
            regenerated.acceptance_authorized
            or regenerated.promotion_authorized
            or regenerated.production_applied
        ):
            raise SoftwareFactoryError(
                "SF-13 cannot consume review evidence with downstream authority"
            )
        return regenerated

    @staticmethod
    def _validate_policy(policy: DependencyPolicy) -> DependencyPolicy:
        if not _trimmed(policy.policy_id):
            raise SoftwareFactoryError("SF-13 dependency policy identity is required")
        if not policy.allowed_sources or any(
            not _trimmed(item) for item in policy.allowed_sources
        ):
            raise SoftwareFactoryError(
                "SF-13 requires an explicit non-empty source allowlist"
            )
        license_sets = (
            policy.allowed_licenses,
            policy.review_licenses,
            policy.blocked_licenses,
        )
        if any(any(not _trimmed(item) for item in values) for values in license_sets):
            raise SoftwareFactoryError(
                "SF-13 license policy entries must be non-blank and trimmed"
            )
        if (
            policy.allowed_licenses & policy.review_licenses
            or policy.allowed_licenses & policy.blocked_licenses
            or policy.review_licenses & policy.blocked_licenses
        ):
            raise SoftwareFactoryError("SF-13 license policy sets must not overlap")
        unknowns = (
            policy.unknown_license_disposition,
            policy.unknown_security_disposition,
            policy.unknown_commercial_disposition,
        )
        if DependencyDisposition.ALLOW in unknowns:
            raise SoftwareFactoryError(
                "SF-13 unknown dependency evidence cannot default to ALLOW"
            )
        return policy

    @staticmethod
    def _validate_change_scope(
        changes: tuple[DependencyChange, ...],
        dependency_paths: tuple[str, ...],
    ) -> tuple[DependencyChange, ...]:
        if changes and not dependency_paths:
            raise SoftwareFactoryError(
                "SF-13 dependency evidence has no reviewed manifest/lockfile change"
            )
        allowed_paths = set(dependency_paths)
        seen: set[tuple[str, str, str, str, str | None, str | None]] = set()
        validated: list[DependencyChange] = []
        for change in changes:
            for label, value in (
                ("package", change.package),
                ("version", change.version),
                ("source", change.source),
                ("integrity", change.integrity),
                ("license", change.license),
            ):
                if not _trimmed(value):
                    raise SoftwareFactoryError(
                        f"SF-13 dependency {label} must be non-blank and trimmed"
                    )
            manifest_path = _optional_dependency_path(change.manifest_path)
            lockfile_path = _optional_dependency_path(change.lockfile_path)
            if manifest_path is None and lockfile_path is None:
                raise SoftwareFactoryError(
                    "SF-13 dependency evidence must reference manifest or lockfile"
                )
            for path in (manifest_path, lockfile_path):
                if path is not None and path not in allowed_paths:
                    raise SoftwareFactoryError(
                        "SF-13 dependency evidence exceeds reviewed dependency-path scope"
                    )
            identity = (
                change.package,
                change.version,
                change.source,
                change.operation.value,
                manifest_path,
                lockfile_path,
            )
            if identity in seen:
                raise SoftwareFactoryError(
                    "SF-13 dependency evidence contains duplicate change identity"
                )
            seen.add(identity)
            validated.append(
                replace_paths(change, manifest_path=manifest_path, lockfile_path=lockfile_path)
            )
        return tuple(validated)

    @staticmethod
    def _evaluate_change(
        change: DependencyChange, policy: DependencyPolicy
    ) -> DependencyEvidence:
        reasons: list[tuple[DependencyDisposition, str]] = []
        if not _trimmed(change.reason):
            reasons.append(
                (
                    DependencyDisposition.BLOCK,
                    "dependency change has no business/technical reason",
                )
            )
        if policy.require_verified_integrity and not change.integrity_verified:
            reasons.append(
                (DependencyDisposition.BLOCK, "dependency integrity is not verified")
            )
        if change.operation is not DependencyOperation.REMOVE:
            _apply_add_update_policy(change, policy, reasons)

        disposition = _aggregate_disposition(tuple(item[0] for item in reasons))
        policy_reasons = tuple(item[1] for item in reasons)
        material = _change_material(change)
        material["disposition"] = disposition.value
        material["policy_reasons"] = list(policy_reasons)
        return DependencyEvidence(
            package=change.package,
            version=change.version,
            source=change.source,
            role=change.role,
            reason=change.reason,
            integrity=change.integrity,
            integrity_verified=change.integrity_verified,
            security_status=change.security_status,
            license=change.license,
            commercial_compatibility=change.commercial_compatibility,
            operation=change.operation,
            manifest_path=change.manifest_path,
            lockfile_path=change.lockfile_path,
            disposition=disposition,
            policy_reasons=policy_reasons,
            evidence_sha256=canonical_sha256(material),
        )


def replace_paths(
    change: DependencyChange,
    *,
    manifest_path: str | None,
    lockfile_path: str | None,
) -> DependencyChange:
    return DependencyChange(
        package=change.package,
        version=change.version,
        source=change.source,
        role=change.role,
        reason=change.reason,
        integrity=change.integrity,
        integrity_verified=change.integrity_verified,
        security_status=change.security_status,
        license=change.license,
        commercial_compatibility=change.commercial_compatibility,
        operation=change.operation,
        manifest_path=manifest_path,
        lockfile_path=lockfile_path,
    )


def _apply_add_update_policy(
    change: DependencyChange,
    policy: DependencyPolicy,
    reasons: list[tuple[DependencyDisposition, str]],
) -> None:
    if change.source not in policy.allowed_sources:
        reasons.append(
            (DependencyDisposition.BLOCK, "dependency source is not allowlisted")
        )
    if change.security_status is DependencySecurityStatus.VULNERABLE:
        reasons.append(
            (
                DependencyDisposition.BLOCK,
                "dependency has a known vulnerable security status",
            )
        )
    elif change.security_status is DependencySecurityStatus.UNKNOWN:
        reasons.append(
            (policy.unknown_security_disposition, "dependency security status is unknown")
        )
    if change.commercial_compatibility is CommercialCompatibility.INCOMPATIBLE:
        reasons.append(
            (
                DependencyDisposition.BLOCK,
                "dependency is commercially incompatible under supplied evidence",
            )
        )
    elif change.commercial_compatibility is CommercialCompatibility.UNKNOWN:
        reasons.append(
            (
                policy.unknown_commercial_disposition,
                "dependency commercial compatibility is unknown",
            )
        )
    if change.license in policy.blocked_licenses:
        reasons.append(
            (DependencyDisposition.BLOCK, "dependency license is blocked by policy")
        )
    elif change.license in policy.review_licenses:
        reasons.append(
            (
                DependencyDisposition.REVIEW_REQUIRED,
                "dependency license requires policy review",
            )
        )
    elif change.license not in policy.allowed_licenses:
        reasons.append(
            (
                policy.unknown_license_disposition,
                "dependency license is not explicitly classified by policy",
            )
        )


def _aggregate_disposition(
    dispositions: tuple[DependencyDisposition, ...],
    *,
    force_block: bool = False,
) -> DependencyDisposition:
    if force_block or DependencyDisposition.BLOCK in dispositions:
        return DependencyDisposition.BLOCK
    if DependencyDisposition.REVIEW_REQUIRED in dispositions:
        return DependencyDisposition.REVIEW_REQUIRED
    return DependencyDisposition.ALLOW


def _optional_dependency_path(path: str | None) -> str | None:
    if path is None:
        return None
    normalized = _normalize_path(path)
    if not _is_dependency_path(normalized):
        raise SoftwareFactoryError(
            "SF-13 evidence path is not a supported dependency manifest/lockfile"
        )
    return normalized


def _normalize_path(path: str) -> str:
    if not _trimmed(path) or path.startswith(("/", "\\")):
        raise SoftwareFactoryError(
            "SF-13 dependency paths must be repository-relative"
        )
    normalized = path.replace("\\", "/")
    if any(part in {"", ".", ".."} for part in normalized.split("/")):
        raise SoftwareFactoryError("SF-13 dependency paths must be normalized")
    return normalized


def _is_dependency_path(path: str) -> bool:
    name = _normalize_path(path).rsplit("/", 1)[-1]
    fixed = {
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
    return name in fixed or (
        name.startswith("requirements") and name.endswith(".txt")
    )


def _policy_material(policy: DependencyPolicy) -> dict[str, object]:
    return {
        "policy_id": policy.policy_id,
        "allowed_sources": sorted(policy.allowed_sources),
        "allowed_licenses": sorted(policy.allowed_licenses),
        "review_licenses": sorted(policy.review_licenses),
        "blocked_licenses": sorted(policy.blocked_licenses),
        "unknown_license_disposition": policy.unknown_license_disposition.value,
        "unknown_security_disposition": policy.unknown_security_disposition.value,
        "unknown_commercial_disposition": policy.unknown_commercial_disposition.value,
        "require_verified_integrity": policy.require_verified_integrity,
    }


def _change_material(change: DependencyChange) -> dict[str, object]:
    return {
        "package": change.package,
        "version": change.version,
        "source": change.source,
        "role": change.role.value,
        "reason": change.reason,
        "integrity": change.integrity,
        "integrity_verified": change.integrity_verified,
        "security_status": change.security_status.value,
        "license": change.license,
        "commercial_compatibility": change.commercial_compatibility.value,
        "operation": change.operation.value,
        "manifest_path": change.manifest_path,
        "lockfile_path": change.lockfile_path,
    }


def _evidence_material(evidence: DependencyEvidence) -> dict[str, object]:
    return {
        "package": evidence.package,
        "version": evidence.version,
        "source": evidence.source,
        "role": evidence.role.value,
        "reason": evidence.reason,
        "integrity": evidence.integrity,
        "integrity_verified": evidence.integrity_verified,
        "security_status": evidence.security_status.value,
        "license": evidence.license,
        "commercial_compatibility": evidence.commercial_compatibility.value,
        "operation": evidence.operation.value,
        "manifest_path": evidence.manifest_path,
        "lockfile_path": evidence.lockfile_path,
        "disposition": evidence.disposition.value,
        "policy_reasons": list(evidence.policy_reasons),
        "evidence_sha256": evidence.evidence_sha256,
    }


def _record_material(
    request: DependencyGovernanceRequest,
    package: SkillPackage,
    review: IndependentReviewRecord,
    repository_sha: str,
    dependency_paths: tuple[str, ...],
    evidence: tuple[DependencyEvidence, ...],
    disposition: DependencyDisposition,
    policy_reasons: tuple[str, ...],
    policy_sha256: str,
) -> dict[str, object]:
    return {
        "governance_id": request.governance_id,
        "contract_version": DEPENDENCY_CONTRACT_VERSION,
        "skill_id": package.manifest.skill_id,
        "skill_version": package.manifest.version,
        "policy_id": request.policy.policy_id,
        "policy_sha256": policy_sha256,
        "tenant_id": review.tenant_id,
        "task_id": review.task_id,
        "correlation_id": review.correlation_id,
        "repository_sha": repository_sha,
        "review_record_sha256": review.record_sha256,
        "validation_report_sha256": review.validation_report_sha256,
        "dependency_paths": list(dependency_paths),
        "dependency_evidence": [_evidence_material(item) for item in evidence],
        "disposition": disposition.value,
        "policy_reasons": list(policy_reasons),
        "independent_review_required": package.manifest.independent_review_required,
        "acceptance_authorized": False,
        "promotion_authorized": False,
        "deployment_authorized": False,
        "production_applied": False,
        "subject_mutated": False,
    }


def _trimmed(value: str) -> bool:
    return bool(value) and value == value.strip()
