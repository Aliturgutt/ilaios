"""Provider-neutral enterprise identity and tenant authorization contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol


class IdentityError(PermissionError):
    """An identity, session, or authorization control denied the operation."""


class IdentityKind(str, Enum):
    HUMAN = "human"
    SERVICE = "service"


@dataclass(frozen=True, slots=True)
class VerifiedOIDCClaims:
    """Claims returned only after an adapter verifies signature and token binding."""

    issuer: str
    audience: str
    subject: str
    tenant_id: str
    expires_at: datetime
    issued_at: datetime
    kind: IdentityKind
    roles: frozenset[str]
    attributes: frozenset[tuple[str, str]] = frozenset()
    authentication_methods: frozenset[str] = frozenset()


class OIDCTokenVerifier(Protocol):
    """Replaceable OIDC/OAuth validation boundary; raw tokens remain adapter-owned."""

    def verify(self, encoded_token: str) -> VerifiedOIDCClaims: ...


@dataclass(frozen=True, slots=True)
class IdentityPolicy:
    trusted_issuers: frozenset[str]
    audience: str
    maximum_session: timedelta
    privileged_mfa_methods: frozenset[str] = frozenset({"mfa"})


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    tenant_id: str
    kind: IdentityKind
    roles: frozenset[str]
    attributes: frozenset[tuple[str, str]]
    authentication_methods: frozenset[str]


class AuthenticationBoundary:
    """Normalizes verified federation claims and rejects unsafe sessions."""

    def __init__(self, verifier: OIDCTokenVerifier, policy: IdentityPolicy) -> None:
        self._verifier = verifier
        self._policy = policy

    def authenticate(self, encoded_token: str, now: datetime) -> Principal:
        if not encoded_token:
            raise IdentityError("token is required")
        claims = self._verifier.verify(encoded_token)
        if claims.issuer not in self._policy.trusted_issuers:
            raise IdentityError("untrusted issuer")
        if claims.audience != self._policy.audience:
            raise IdentityError("invalid audience")
        if claims.issued_at > now or claims.expires_at <= now:
            raise IdentityError("token is not currently valid")
        if claims.expires_at - claims.issued_at > self._policy.maximum_session:
            raise IdentityError("token lifetime exceeds policy")
        if not claims.subject.strip() or not claims.tenant_id.strip():
            raise IdentityError("subject and tenant claims are required")
        return Principal(
            claims.subject,
            claims.tenant_id,
            claims.kind,
            claims.roles,
            claims.attributes,
            claims.authentication_methods,
        )


@dataclass(frozen=True, slots=True)
class AccessRequest:
    tenant_id: str
    resource_tenant_id: str
    action: str
    resource_attributes: frozenset[tuple[str, str]] = frozenset()
    privileged: bool = False
    high_risk: bool = False
    approval_id: str | None = None


@dataclass(frozen=True, slots=True)
class AuthorizationRule:
    action: str
    roles: frozenset[str]
    subject_attributes: frozenset[tuple[str, str]] = frozenset()
    resource_attributes: frozenset[tuple[str, str]] = frozenset()
    identity_kinds: frozenset[IdentityKind] = frozenset(
        {IdentityKind.HUMAN, IdentityKind.SERVICE}
    )


@dataclass(frozen=True, slots=True)
class ApprovalRecord:
    approval_id: str
    tenant_id: str
    action: str
    requester_id: str
    approver_id: str
    expires_at: datetime
    revoked: bool = False


class AuthorizationEngine:
    """Deterministic tenant-scoped RBAC/ABAC; no probabilistic decision hook."""

    def __init__(
        self,
        rules: tuple[AuthorizationRule, ...],
        approvals: tuple[ApprovalRecord, ...] = (),
        *,
        privileged_mfa_methods: frozenset[str] = frozenset({"mfa"}),
    ) -> None:
        self._rules = rules
        self._approvals = {item.approval_id: item for item in approvals}
        self._consumed_approvals: set[str] = set()
        self._privileged_mfa = privileged_mfa_methods

    def authorize(
        self, principal: Principal, request: AccessRequest, now: datetime
    ) -> None:
        if request.tenant_id != principal.tenant_id:
            raise IdentityError("request tenant does not match principal")
        if request.resource_tenant_id != principal.tenant_id:
            raise IdentityError("cross-tenant access denied")
        if request.privileged and not (
            principal.authentication_methods & self._privileged_mfa
        ):
            raise IdentityError("privileged access requires MFA")
        approval_id: str | None = None
        if request.high_risk:
            approval_id = self._check_approval(principal, request, now)
        for rule in self._rules:
            if (
                rule.action == request.action
                and principal.kind in rule.identity_kinds
                and bool(principal.roles & rule.roles)
                and rule.subject_attributes <= principal.attributes
                and rule.resource_attributes <= request.resource_attributes
            ):
                if approval_id is not None:
                    self._consumed_approvals.add(approval_id)
                return
        raise IdentityError("deny by default")

    def _check_approval(
        self, principal: Principal, request: AccessRequest, now: datetime
    ) -> str:
        approval_id = request.approval_id or ""
        approval = self._approvals.get(approval_id)
        if (
            approval is None
            or approval_id in self._consumed_approvals
            or approval.revoked
            or approval.expires_at <= now
            or approval.tenant_id != principal.tenant_id
            or approval.action != request.action
            or approval.requester_id != principal.principal_id
            or approval.approver_id == principal.principal_id
        ):
            raise IdentityError("valid independent approval is required")
        return approval_id


@dataclass(frozen=True, slots=True)
class Session:
    session_id: str
    principal_id: str
    tenant_id: str
    expires_at: datetime
    privileged: bool = False


class SessionRegistry:
    """Short-lived session issuance and immediate credential/session revocation."""

    def __init__(self, maximum_lifetime: timedelta) -> None:
        self._maximum_lifetime = maximum_lifetime
        self._sessions: dict[str, Session] = {}
        self._revoked_principals: set[str] = set()

    def issue(
        self, session_id: str, principal: Principal, now: datetime, lifetime: timedelta
    ) -> Session:
        if (
            not session_id.strip()
            or not principal.principal_id.strip()
            or not principal.tenant_id.strip()
        ):
            raise IdentityError("session identity is required")
        if lifetime <= timedelta(0) or lifetime > self._maximum_lifetime:
            raise IdentityError("session lifetime violates policy")
        if (
            session_id in self._sessions
            or principal.principal_id in self._revoked_principals
        ):
            raise IdentityError("session cannot be issued")
        session = Session(
            session_id, principal.principal_id, principal.tenant_id, now + lifetime
        )
        self._sessions[session_id] = session
        return session

    def validate(self, session_id: str, tenant_id: str, now: datetime) -> Session:
        if not session_id.strip() or not tenant_id.strip():
            raise IdentityError("session is invalid or revoked")
        session = self._sessions.get(session_id)
        if (
            session is None
            or session.expires_at <= now
            or session.tenant_id != tenant_id
            or session.principal_id in self._revoked_principals
        ):
            raise IdentityError("session is invalid or revoked")
        return session

    def revoke_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def revoke_principal(self, principal_id: str) -> None:
        if not principal_id.strip():
            raise IdentityError("principal identity is required")
        self._revoked_principals.add(principal_id)


@dataclass(frozen=True, slots=True)
class RecoveryRecord:
    recovery_id: str
    principal_id: str
    verified_by: str
    expires_at: datetime
    consumed: bool = False


@dataclass(frozen=True, slots=True)
class BreakGlassRecord:
    event_id: str
    principal_id: str
    tenant_id: str
    reason: str
    approved_by: str
    expires_at: datetime
    reviewed: bool = False


class EmergencyAccessRegistry:
    """Auditable recovery and break-glass records; never ordinary credentials."""

    def __init__(self) -> None:
        self._recoveries: dict[str, RecoveryRecord] = {}
        self._break_glass: dict[str, BreakGlassRecord] = {}

    def record_recovery(self, record: RecoveryRecord) -> None:
        if record.principal_id == record.verified_by:
            raise IdentityError("recovery requires independent verification")
        if record.recovery_id in self._recoveries:
            raise IdentityError("recovery record already exists")
        self._recoveries[record.recovery_id] = record

    def activate_break_glass(self, record: BreakGlassRecord, now: datetime) -> None:
        if (
            not record.reason
            or record.principal_id == record.approved_by
            or record.expires_at <= now
        ):
            raise IdentityError("break-glass requires reason, expiry, and approver")
        if record.event_id in self._break_glass:
            raise IdentityError("break-glass event already exists")
        self._break_glass[record.event_id] = record

    def active_break_glass(self, event_id: str, now: datetime) -> BreakGlassRecord:
        record = self._break_glass.get(event_id)
        if record is None or record.expires_at <= now:
            raise IdentityError("break-glass access is not active")
        return record
