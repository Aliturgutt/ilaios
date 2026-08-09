"""RACI, risk, exception, review, and lifecycle governance records."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum


class GovernanceRecordError(PermissionError):
    """A governance record is incomplete, conflicted, or unauthorized."""


@dataclass(frozen=True, slots=True)
class RACIRecord:
    control_id: str
    accountable: str
    responsible: frozenset[str]
    consulted: frozenset[str]
    informed: frozenset[str]
    verifier: str
    effective_at: datetime
    review_due: datetime

    def __post_init__(self) -> None:
        if not self.control_id or not self.accountable or not self.responsible:
            raise ValueError("control requires one accountable and responsible roles")
        if self.accountable == self.verifier or self.verifier in self.responsible:
            raise GovernanceRecordError("independent verifier must be separated")
        if self.review_due <= self.effective_at:
            raise ValueError("RACI review must be future-dated")


class RiskStatus(str, Enum):
    OPEN = "open"
    TREATED = "treated"
    ACCEPTED = "accepted"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class RiskRecord:
    risk_id: str
    owner: str
    classification: str
    treatment: str
    due_at: datetime
    status: RiskStatus = RiskStatus.OPEN
    accepted_by: str | None = None
    verification_reference: str | None = None


class ExceptionStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class ExceptionRecord:
    exception_id: str
    control_id: str
    requester: str
    approver: str
    reason: str
    compensating_controls: tuple[str, ...]
    expires_at: datetime
    review_due: datetime
    status: ExceptionStatus = ExceptionStatus.PROPOSED

    def __post_init__(self) -> None:
        if self.requester == self.approver:
            raise GovernanceRecordError("exception requires independent approval")
        if not self.reason or not self.compensating_controls:
            raise GovernanceRecordError(
                "exception requires reason and compensating controls"
            )
        if self.review_due > self.expires_at:
            raise GovernanceRecordError("exception review cannot follow expiry")


class LifecycleStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class LifecycleRecord:
    asset_id: str
    owner: str
    status: LifecycleStatus
    review_due: datetime
    replacement_id: str | None = None
    migration_deadline: datetime | None = None
    retirement_evidence: str | None = None


@dataclass(frozen=True, slots=True)
class AssuranceClaim:
    claim_id: str
    statement: str
    scope: str
    evidence_reference: str
    assessed_by: str
    assessed_at: datetime
    independently_assessed: bool
    certification: str | None = None

    def __post_init__(self) -> None:
        if self.certification is not None and not self.independently_assessed:
            raise GovernanceRecordError("certification requires independent assessment")


class GovernanceRegistry:
    def __init__(self) -> None:
        self._raci: dict[str, RACIRecord] = {}
        self._risks: dict[str, RiskRecord] = {}
        self._exceptions: dict[str, ExceptionRecord] = {}
        self._lifecycle: dict[str, LifecycleRecord] = {}
        self._claims: dict[str, AssuranceClaim] = {}

    def register_raci(self, record: RACIRecord) -> None:
        if record.control_id in self._raci:
            raise GovernanceRecordError("control already has an accountable owner")
        self._raci[record.control_id] = record

    def register_risk(self, record: RiskRecord) -> None:
        if record.risk_id in self._risks:
            raise GovernanceRecordError("risk already exists")
        self._risks[record.risk_id] = record

    def accept_risk(self, risk_id: str, authority: str) -> RiskRecord:
        risk = self._risks[risk_id]
        if authority == risk.owner:
            raise GovernanceRecordError("risk acceptance requires separate authority")
        updated = replace(risk, status=RiskStatus.ACCEPTED, accepted_by=authority)
        self._risks[risk_id] = updated
        return updated

    def approve_exception(
        self, record: ExceptionRecord, now: datetime
    ) -> ExceptionRecord:
        if now >= record.expires_at or now >= record.review_due:
            raise GovernanceRecordError("exception is expired or overdue for review")
        if record.exception_id in self._exceptions:
            raise GovernanceRecordError("exception already exists")
        updated = replace(record, status=ExceptionStatus.APPROVED)
        self._exceptions[record.exception_id] = updated
        return updated

    def authorize_exception(
        self, exception_id: str, control_id: str, now: datetime
    ) -> None:
        record = self._exceptions.get(exception_id)
        if (
            record is None
            or record.status is not ExceptionStatus.APPROVED
            or record.control_id != control_id
            or now >= record.expires_at
            or now >= record.review_due
        ):
            raise GovernanceRecordError("active reviewed exception not found")

    def register_lifecycle(self, record: LifecycleRecord) -> None:
        if record.status is LifecycleStatus.DEPRECATED and (
            record.replacement_id is None or record.migration_deadline is None
        ):
            raise GovernanceRecordError(
                "deprecation requires replacement and migration deadline"
            )
        if record.status is LifecycleStatus.RETIRED and not record.retirement_evidence:
            raise GovernanceRecordError("retirement requires evidence")
        self._lifecycle[record.asset_id] = record

    def register_claim(self, claim: AssuranceClaim) -> None:
        if not all(
            (claim.statement, claim.scope, claim.evidence_reference, claim.assessed_by)
        ):
            raise GovernanceRecordError("assurance claim requires scoped evidence")
        self._claims[claim.claim_id] = claim
