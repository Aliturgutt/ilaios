"""Project canonical Identity membership into the incumbent authorization Principal.

This module creates no identity, membership, role, session, token, or authorization
authority. It reads the canonical migration-v9 identity tables after a canonical
account has already been resolved and fails closed unless that exact User/Tenant
primary membership is active. ``services.identity.Principal`` remains the existing
authorization subject contract.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from services.central_identity import CanonicalAccount, CentralIdentityError
from services.control_plane.migrations import migrate_database
from services.identity import IdentityKind, Principal


class CanonicalIdentityPrincipalError(CentralIdentityError):
    """Canonical membership/role projection is missing, ambiguous, or inactive."""


class CanonicalIdentityPrincipalResolver:
    """Resolve one canonical account to its server-authoritative primary role."""

    def __init__(self, identity_database: Path) -> None:
        self._identity_database = identity_database
        if migrate_database(identity_database) < 9:
            raise CanonicalIdentityPrincipalError("canonical identity schema is unavailable")

    def resolve(self, account: CanonicalAccount) -> Principal:
        user_id = account.user_id.strip()
        tenant_id = account.tenant_id.strip()
        if not account.enabled or not user_id or not tenant_id:
            raise CanonicalIdentityPrincipalError("canonical account is unavailable")

        with sqlite3.connect(self._identity_database) as connection:
            rows = connection.execute(
                """
                SELECT u.enabled, t.status, m.status, m.role
                  FROM identity_users AS u
                  JOIN identity_memberships AS m ON m.user_id = u.user_id
                  JOIN identity_tenants AS t ON t.tenant_id = m.tenant_id
                 WHERE u.user_id = ? AND m.tenant_id = ? AND m.is_primary = 1
                """,
                (user_id, tenant_id),
            ).fetchall()

        if len(rows) != 1:
            raise CanonicalIdentityPrincipalError(
                "canonical primary membership is missing or ambiguous"
            )
        enabled, tenant_status, membership_status, role = rows[0]
        normalized_role = str(role).strip()
        if (
            not bool(enabled)
            or tenant_status != "ACTIVE"
            or membership_status != "ACTIVE"
            or not normalized_role
        ):
            raise CanonicalIdentityPrincipalError(
                "canonical primary membership is not active"
            )

        return Principal(
            principal_id=user_id,
            tenant_id=tenant_id,
            kind=IdentityKind.HUMAN,
            roles=frozenset({normalized_role}),
            attributes=frozenset(),
            authentication_methods=frozenset(),
        )


__all__ = [
    "CanonicalIdentityPrincipalError",
    "CanonicalIdentityPrincipalResolver",
]
