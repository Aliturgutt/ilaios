"""SF-12 independent review over validated Software Factory evidence.

This layer operationalizes the existing first-party ``sf-code-review`` and
``sf-security-review`` contracts. It does not create a second review framework,
does not mutate the reviewed subject, and never grants acceptance, promotion,
deployment, or production authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.software_factory import SoftwareFactoryError
from services.software_factory_skills import SkillRegistry
from services.software_factory_validation import (
    SoftwareFactoryValidationPipeline,
    SoftwareValidationRequest,
)
from src.core.validation_pipeline import ValidationReport, ValidationStatus, canonical_sha256

REQUIRED_REVIEW_SKILLS = ("sf-code-review", "sf-security-review")
REVIEW_CONTRACT_VERSION = "1.0.0"
REVIEW_POLICY_ID = "ilaios.software-factory.independent-review.v1"
_ALLOWED_ENVIRONMENTS = frozenset(
    {"ci-ephemeral-read-only", "local-deterministic-read-only"}
)


class ReviewDecision(str, Enum):
    """Canonical SF-7 review decisions used by the SF-12 aggregate gate."""

    APPROVE = "APPROVE"
    REJECT = "REJECT"
    CHANGES_REQUIRED = "CHANGES_REQUIRED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    """Evidence-backed finding required by the canonical review-skill contract."""

    finding_id: str
    severity: str
    location: str
    evidence: str
    reason: str
    required_remediation: str
    status: str


@dataclass(frozen=True, slots=True)
class IndependentReviewSubmission:
    """One independent execution of a canonical SF-7 review skill."""

    skill_id: str
    skill_version: str
    reviewer_id: str
    reviewed_subject_sha256: str
    validation_report_sha256: str
    reviewed_paths: tuple[str, ...]
    findings: tuple[ReviewFinding, ...]
    decision: ReviewDecision
    evidence_references: tuple[str, ...]
    read_only: bool = True


@dataclass(frozen=True, slots=True)
class SoftwareIndependentReviewRequest:
    """Exact SF-12 intake bound to one deterministic SF-11 report."""

    review_id: str
    tenant_id: str
    task_id: str
    correlation_id: str
    policy_reference: str
    environment_id: str
    changed_paths: tuple[str, ...]
    validation_request: SoftwareValidationRequest
    validation_report: ValidationReport
    submissions: tuple[IndependentReviewSubmission, ...]


@dataclass(frozen=True, slots=True)
class IndependentReviewRecord:
    """Content-addressed SF-12 evidence with no downstream authority."""

    review_id: str
    contract_version: str
    policy_id: str
    tenant_id: str
    task_id: str
    correlation_id: str
    subject_sha256: str
    validation_report_sha256: str
    changed_paths: tuple[str, ...]
    submissions: tuple[IndependentReviewSubmission, ...]
    reviewers: tuple[str, ...]
    decision: ReviewDecision
    review_complete: bool
    acceptance_authorized: bool
    promotion_authorized: bool
    production_applied: bool
    record_sha256: str

    @property
    def approved(self) -> bool:
        """Review approval is evidence only and is not product acceptance."""

        return self.decision is ReviewDecision.APPROVE


class SoftwareFactoryIndependentReview:
    """Fail-closed SF-12 gate over the canonical SF-7 and SF-11 contracts."""

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    def review(self, request: SoftwareIndependentReviewRequest) -> IndependentReviewRecord:
        self._validate_request_identity(request)
        validated_report = self._validate_sf11_binding(request)
        changed_paths = _normalize_paths(request.changed_paths)
        submissions = self._validate_submissions(request, changed_paths)
        decision = _aggregate_decision(submissions)
        reviewers = tuple(sorted({submission.reviewer_id for submission in submissions}))
        material = _record_material(
            request=request,
            report=validated_report,
            changed_paths=changed_paths,
            submissions=submissions,
            reviewers=reviewers,
            decision=decision,
        )
        return IndependentReviewRecord(
            review_id=request.review_id,
            contract_version=REVIEW_CONTRACT_VERSION,
            policy_id=REVIEW_POLICY_ID,
            tenant_id=request.tenant_id,
            task_id=request.task_id,
            correlation_id=request.correlation_id,
            subject_sha256=validated_report.subject_sha256,
            validation_report_sha256=validated_report.report_sha256,
            changed_paths=changed_paths,
            submissions=submissions,
            reviewers=reviewers,
            decision=decision,
            review_complete=True,
            acceptance_authorized=False,
            promotion_authorized=False,
            production_applied=False,
            record_sha256=canonical_sha256(material),
        )

    def _validate_request_identity(self, request: SoftwareIndependentReviewRequest) -> None:
        required_text = {
            "review_id": request.review_id,
            "tenant_id": request.tenant_id,
            "task_id": request.task_id,
            "correlation_id": request.correlation_id,
            "policy_reference": request.policy_reference,
            "environment_id": request.environment_id,
        }
        for field, value in required_text.items():
            if not _trimmed(value):
                raise SoftwareFactoryError(f"SF-12 {field} must be non-blank and trimmed")
        if request.environment_id not in _ALLOWED_ENVIRONMENTS:
            raise SoftwareFactoryError("SF-12 requires an approved read-only environment")

        validation_request = request.validation_request
        expected_identity = (
            validation_request.tenant_id,
            validation_request.task_id,
            validation_request.correlation_id,
            validation_request.policy_reference,
            validation_request.environment_id,
        )
        actual_identity = (
            request.tenant_id,
            request.task_id,
            request.correlation_id,
            request.policy_reference,
            request.environment_id,
        )
        if actual_identity != expected_identity:
            raise SoftwareFactoryError("SF-12 identity/policy lineage does not match SF-11")

    def _validate_sf11_binding(
        self, request: SoftwareIndependentReviewRequest
    ) -> ValidationReport:
        regenerated = SoftwareFactoryValidationPipeline().validate(request.validation_request)
        if regenerated != request.validation_report:
            raise SoftwareFactoryError("SF-12 validation report is stale or tampered")
        if regenerated.status is not ValidationStatus.PASS or not regenerated.passed:
            raise SoftwareFactoryError("SF-12 requires a passing SF-11 validation report")
        if regenerated.acceptance_authorized:
            raise SoftwareFactoryError("SF-12 cannot consume validation with acceptance authority")
        if regenerated.subject_mutated:
            raise SoftwareFactoryError("SF-12 cannot review a mutated validation subject")
        return regenerated

    def _validate_submissions(
        self,
        request: SoftwareIndependentReviewRequest,
        changed_paths: tuple[str, ...],
    ) -> tuple[IndependentReviewSubmission, ...]:
        if len(request.submissions) != len(REQUIRED_REVIEW_SKILLS):
            raise SoftwareFactoryError("SF-12 requires code and security review submissions")
        by_skill = {submission.skill_id: submission for submission in request.submissions}
        if len(by_skill) != len(request.submissions) or set(by_skill) != set(REQUIRED_REVIEW_SKILLS):
            raise SoftwareFactoryError("SF-12 review-skill set is incomplete or duplicated")

        execution = request.validation_request.engineering_execution
        blocked_reviewers = {
            execution.admission.agent_id,
            execution.admission.verifier_id,
            request.validation_request.validator_id,
        }
        validated: list[IndependentReviewSubmission] = []
        for skill_id in REQUIRED_REVIEW_SKILLS:
            submission = by_skill[skill_id]
            package = self._registry.resolve(skill_id)
            manifest = package.manifest
            if manifest.domain != "independent-verification":
                raise SoftwareFactoryError("SF-12 review skill is outside independent verification")
            if not manifest.independent_review_required:
                raise SoftwareFactoryError("SF-12 review skill lost its independence requirement")
            if submission.skill_version != manifest.version:
                raise SoftwareFactoryError("SF-12 review skill version mismatch")
            self._validate_submission(
                submission,
                request=request,
                changed_paths=changed_paths,
                blocked_reviewers=blocked_reviewers,
            )
            validated.append(submission)
        return tuple(validated)

    @staticmethod
    def _validate_submission(
        submission: IndependentReviewSubmission,
        *,
        request: SoftwareIndependentReviewRequest,
        changed_paths: tuple[str, ...],
        blocked_reviewers: set[str],
    ) -> None:
        if not _trimmed(submission.reviewer_id):
            raise SoftwareFactoryError("SF-12 reviewer identity is required")
        if submission.reviewer_id in blocked_reviewers:
            raise SoftwareFactoryError(
                "SF-12 reviewer must be independent from producer, verifier, and validator"
            )
        if not submission.read_only:
            raise SoftwareFactoryError("SF-12 review submission must be read-only")
        if submission.reviewed_subject_sha256 != request.validation_report.subject_sha256:
            raise SoftwareFactoryError("SF-12 review subject digest mismatch")
        if submission.validation_report_sha256 != request.validation_report.report_sha256:
            raise SoftwareFactoryError("SF-12 validation-report digest mismatch")
        if _normalize_paths(submission.reviewed_paths) != changed_paths:
            raise SoftwareFactoryError("SF-12 reviewer did not cover the exact changed-path scope")
        _validate_evidence_references(submission.evidence_references)
        _validate_findings(submission.findings)
        if submission.decision is not ReviewDecision.APPROVE and not submission.findings:
            raise SoftwareFactoryError("SF-12 non-approval decision requires a finding")


def _validate_findings(findings: tuple[ReviewFinding, ...]) -> None:
    seen: set[str] = set()
    for finding in findings:
        required_text = (
            finding.finding_id,
            finding.severity,
            finding.location,
            finding.evidence,
            finding.reason,
            finding.required_remediation,
            finding.status,
        )
        if any(not _trimmed(value) for value in required_text):
            raise SoftwareFactoryError("SF-12 finding fields must be non-blank and trimmed")
        if finding.finding_id in seen:
            raise SoftwareFactoryError("SF-12 finding IDs must be unique per review submission")
        seen.add(finding.finding_id)


def _validate_evidence_references(references: tuple[str, ...]) -> None:
    if not references or any(not _trimmed(reference) for reference in references):
        raise SoftwareFactoryError("SF-12 review requires evidence references")
    if len(references) != len(set(references)):
        raise SoftwareFactoryError("SF-12 review evidence references must be unique")


def _normalize_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    if not paths:
        raise SoftwareFactoryError("SF-12 requires changed paths")
    normalized: list[str] = []
    for path in paths:
        if not _trimmed(path) or path.startswith(("/", "\\")):
            raise SoftwareFactoryError("SF-12 changed paths must be repository-relative")
        parts = path.replace("\\", "/").split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise SoftwareFactoryError("SF-12 changed paths must be normalized")
        normalized.append("/".join(parts))
    if len(normalized) != len(set(normalized)):
        raise SoftwareFactoryError("SF-12 changed paths must be unique")
    return tuple(sorted(normalized))


def _aggregate_decision(
    submissions: tuple[IndependentReviewSubmission, ...]
) -> ReviewDecision:
    decisions = {submission.decision for submission in submissions}
    for decision in (
        ReviewDecision.REJECT,
        ReviewDecision.CHANGES_REQUIRED,
        ReviewDecision.REVIEW_REQUIRED,
        ReviewDecision.APPROVE,
    ):
        if decision in decisions:
            return decision
    raise SoftwareFactoryError("SF-12 review decision set is empty")


def _record_material(
    *,
    request: SoftwareIndependentReviewRequest,
    report: ValidationReport,
    changed_paths: tuple[str, ...],
    submissions: tuple[IndependentReviewSubmission, ...],
    reviewers: tuple[str, ...],
    decision: ReviewDecision,
) -> dict[str, object]:
    return {
        "review_id": request.review_id,
        "contract_version": REVIEW_CONTRACT_VERSION,
        "policy_id": REVIEW_POLICY_ID,
        "tenant_id": request.tenant_id,
        "task_id": request.task_id,
        "correlation_id": request.correlation_id,
        "policy_reference": request.policy_reference,
        "environment_id": request.environment_id,
        "subject_sha256": report.subject_sha256,
        "validation_report_sha256": report.report_sha256,
        "changed_paths": list(changed_paths),
        "submissions": [_submission_material(submission) for submission in submissions],
        "reviewers": list(reviewers),
        "decision": decision.value,
        "review_complete": True,
        "acceptance_authorized": False,
        "promotion_authorized": False,
        "production_applied": False,
    }


def _submission_material(submission: IndependentReviewSubmission) -> dict[str, object]:
    return {
        "skill_id": submission.skill_id,
        "skill_version": submission.skill_version,
        "reviewer_id": submission.reviewer_id,
        "reviewed_subject_sha256": submission.reviewed_subject_sha256,
        "validation_report_sha256": submission.validation_report_sha256,
        "reviewed_paths": list(_normalize_paths(submission.reviewed_paths)),
        "findings": [
            {
                "finding_id": finding.finding_id,
                "severity": finding.severity,
                "location": finding.location,
                "evidence": finding.evidence,
                "reason": finding.reason,
                "required_remediation": finding.required_remediation,
                "status": finding.status,
            }
            for finding in submission.findings
        ],
        "decision": submission.decision.value,
        "evidence_references": list(submission.evidence_references),
        "read_only": submission.read_only,
    }


def _trimmed(value: str) -> bool:
    return bool(value) and value == value.strip()
