"""Bounded HTTP request-handler wiring for canonical account lifecycle services.

This runtime does not own identity, session, authorization, tenant, audit, or
persistence authority. It authenticates and binds a canonical session through
``AuthenticationBoundary``/``SessionRegistry``, delegates authorization to the
canonical ``AuthorizationEngine``, resolves only declared lifecycle projection
routes, and calls the existing lifecycle service. Client payload never selects
canonical user or tenant authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Protocol

from services.account_lifecycle_projection import (
    AccountLifecycleProjectionError,
    resolve_account_lifecycle_projection,
)
from services.central_identity import CentralIdentityError
from services.identity import (
    AccessRequest,
    AuthenticationBoundary,
    AuthorizationEngine,
    IdentityError,
    IdentityKind,
    SessionRegistry,
)
from services.web_app_auth_contract import (
    authenticate_with_canonical_boundary,
    authorize_with_canonical_engine,
    validate_bound_session,
)


class AccountDeletionAuthority(Protocol):
    """Exact canonical service contract consumed by the HTTP adapter."""

    def delete_account(
        self,
        *,
        user_id: str,
        recent_authentication_verified: bool,
        deletion_confirmation_verified: bool,
        occurred_at: str,
    ) -> tuple[int, int, int]: ...


@dataclass(frozen=True, slots=True)
class AccountLifecycleHttpRequest:
    """Trusted server request context plus an untrusted client body."""

    path: str
    method: str
    encoded_token: str
    session_id: str
    body: Mapping[str, object]
    recent_authentication_verified: bool


@dataclass(frozen=True, slots=True)
class AccountLifecycleHttpResponse:
    status_code: int
    body: dict[str, object]


class AccountLifecycleHttpRuntime:
    """Fail-closed lifecycle adapter subordinate to canonical authorities."""

    def __init__(
        self,
        *,
        authentication: AuthenticationBoundary,
        sessions: SessionRegistry,
        authorization: AuthorizationEngine,
        account_deletion: AccountDeletionAuthority,
    ) -> None:
        self._authentication = authentication
        self._sessions = sessions
        self._authorization = authorization
        self._account_deletion = account_deletion

    def handle(
        self,
        request: AccountLifecycleHttpRequest,
        *,
        now: datetime,
    ) -> AccountLifecycleHttpResponse:
        """Handle one declared lifecycle route or return a sanitized denial."""

        try:
            projection = resolve_account_lifecycle_projection(
                path=request.path,
                method=request.method,
            )
        except AccountLifecycleProjectionError:
            return self._error(404, "LIFECYCLE_ROUTE_NOT_FOUND")

        if projection.surface_id != "account.delete":
            return self._error(404, "LIFECYCLE_ROUTE_NOT_WIRED")

        try:
            principal = authenticate_with_canonical_boundary(
                self._authentication,
                encoded_token=request.encoded_token,
                now=now,
            )
            validate_bound_session(
                self._sessions,
                session_id=request.session_id,
                principal=principal,
                now=now,
            )
            if principal.kind is not IdentityKind.HUMAN:
                raise IdentityError("human identity is required")
            if projection.recent_auth_required and not request.recent_authentication_verified:
                raise IdentityError("recent authentication is required")

            authorization_request = AccessRequest(
                tenant_id=principal.tenant_id,
                resource_tenant_id=principal.tenant_id,
                action=projection.action,
            )
            authorize_with_canonical_engine(
                self._authorization,
                principal=principal,
                request=authorization_request,
                now=now,
            )

            confirmation = self._deletion_confirmation(request.body)
            revoked_memberships, revoked_sessions, deleted_identities = (
                self._account_deletion.delete_account(
                    user_id=principal.principal_id,
                    recent_authentication_verified=request.recent_authentication_verified,
                    deletion_confirmation_verified=confirmation,
                    occurred_at=self._utc(now),
                )
            )
        except IdentityError:
            return self._error(403, "IDENTITY_DENIED")
        except CentralIdentityError:
            return self._error(409, "ACCOUNT_DELETE_DENIED")
        except ValueError:
            return self._error(400, "INVALID_REQUEST")

        return AccountLifecycleHttpResponse(
            status_code=200,
            body={
                "status": "deleted",
                "revoked_memberships": revoked_memberships,
                "revoked_sessions": revoked_sessions,
                "deleted_identities": deleted_identities,
            },
        )

    @staticmethod
    def _deletion_confirmation(body: Mapping[str, object]) -> bool:
        if set(body) != {"confirm"}:
            raise ValueError("account delete body must contain only confirmation")
        confirmation = body.get("confirm")
        if confirmation is not True:
            raise CentralIdentityError("explicit account deletion confirmation is required")
        return True

    @staticmethod
    def _utc(now: datetime) -> str:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        return now.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _error(status_code: int, code: str) -> AccountLifecycleHttpResponse:
        return AccountLifecycleHttpResponse(
            status_code=status_code,
            body={"error": code},
        )
