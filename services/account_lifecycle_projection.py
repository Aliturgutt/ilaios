"""Web/App projection contracts for canonical account lifecycle operations.

This module exposes inspectable API/UI surface metadata only. It does not make
identity, session, tenant, policy, approval, audit, or persistence decisions.
Every projected action delegates to an existing canonical service and remains
server-authoritative; UI visibility is never authorization.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


HttpMethod = Literal["GET", "POST", "DELETE"]


class AccountLifecycleProjectionError(ValueError):
    """The requested account-lifecycle projection is missing or ambiguous."""


@dataclass(frozen=True, slots=True)
class AccountLifecycleProjection:
    surface_id: str
    path: str
    method: HttpMethod
    action: str
    service_authority: str
    recent_auth_required: bool
    explicit_confirmation_required: bool
    tenant_scope_required: bool
    server_authoritative: Literal[True] = True
    ui_visibility_is_authorization: Literal[False] = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_PROJECTIONS: tuple[AccountLifecycleProjection, ...] = (
    AccountLifecycleProjection(
        surface_id="account.recover",
        path="/api/account/recover",
        method="POST",
        action="identity.account.recover",
        service_authority="services.account_lifecycle.AccountLifecycleService",
        recent_auth_required=False,
        explicit_confirmation_required=False,
        tenant_scope_required=False,
    ),
    AccountLifecycleProjection(
        surface_id="account.unlink_identity",
        path="/api/account/identities/unlink",
        method="POST",
        action="identity.account.unlink",
        service_authority="services.account_lifecycle.AccountLifecycleService",
        recent_auth_required=True,
        explicit_confirmation_required=False,
        tenant_scope_required=True,
    ),
    AccountLifecycleProjection(
        surface_id="account.logout",
        path="/api/account/sessions/logout",
        method="POST",
        action="identity.session.logout",
        service_authority="services.account_session_lifecycle.AccountSessionLifecycleService",
        recent_auth_required=False,
        explicit_confirmation_required=False,
        tenant_scope_required=True,
    ),
    AccountLifecycleProjection(
        surface_id="account.revoke_all_sessions",
        path="/api/account/sessions/revoke-all",
        method="POST",
        action="identity.session.revoke_all",
        service_authority="services.account_session_lifecycle.AccountSessionLifecycleService",
        recent_auth_required=True,
        explicit_confirmation_required=False,
        tenant_scope_required=True,
    ),
    AccountLifecycleProjection(
        surface_id="account.export_my_data",
        path="/api/account/export",
        method="POST",
        action="identity.account.export",
        service_authority="services.account_data_export.AccountDataExportService",
        recent_auth_required=True,
        explicit_confirmation_required=False,
        tenant_scope_required=False,
    ),
    AccountLifecycleProjection(
        surface_id="account.delete",
        path="/api/account/delete",
        method="DELETE",
        action="identity.account.delete",
        service_authority="services.account_delete.AccountDeletionService",
        recent_auth_required=True,
        explicit_confirmation_required=True,
        tenant_scope_required=False,
    ),
    AccountLifecycleProjection(
        surface_id="tenant.delete",
        path="/api/tenant/delete",
        method="DELETE",
        action="identity.tenant.delete",
        service_authority="services.tenant_delete.TenantDeletionService",
        recent_auth_required=True,
        explicit_confirmation_required=True,
        tenant_scope_required=True,
    ),
    AccountLifecycleProjection(
        surface_id="account.privacy_delete",
        path="/api/account/privacy-delete",
        method="DELETE",
        action="identity.account.privacy_delete",
        service_authority="services.privacy_retention.PrivacyRetentionService",
        recent_auth_required=True,
        explicit_confirmation_required=True,
        tenant_scope_required=False,
    ),
)


def account_lifecycle_projections() -> tuple[AccountLifecycleProjection, ...]:
    """Return the immutable projection catalog consumed by Web/App clients."""
    return _PROJECTIONS


def resolve_account_lifecycle_projection(
    *, path: str, method: str
) -> AccountLifecycleProjection:
    """Resolve an exact route/method pair or fail closed."""
    normalized_path = path.strip()
    normalized_method = method.strip().upper()
    matches = tuple(
        projection
        for projection in _PROJECTIONS
        if projection.path == normalized_path and projection.method == normalized_method
    )
    if len(matches) != 1:
        raise AccountLifecycleProjectionError(
            "account lifecycle route/method has no unique projection"
        )
    return matches[0]


def validate_account_lifecycle_projection_catalog() -> None:
    """Fail closed if the static catalog contains ambiguous or unsafe entries."""
    route_keys: set[tuple[str, str]] = set()
    surface_ids: set[str] = set()
    actions: set[str] = set()
    for projection in _PROJECTIONS:
        if not projection.path.startswith("/api/"):
            raise AccountLifecycleProjectionError("projection path must be API-scoped")
        if not projection.action.startswith("identity."):
            raise AccountLifecycleProjectionError("projection action must be identity-scoped")
        if not projection.service_authority.startswith("services."):
            raise AccountLifecycleProjectionError(
                "projection must delegate to an existing service authority"
            )
        route_key = (projection.path, projection.method)
        if route_key in route_keys:
            raise AccountLifecycleProjectionError("duplicate lifecycle route/method")
        if projection.surface_id in surface_ids:
            raise AccountLifecycleProjectionError("duplicate lifecycle surface id")
        if projection.action in actions:
            raise AccountLifecycleProjectionError("duplicate lifecycle action")
        route_keys.add(route_key)
        surface_ids.add(projection.surface_id)
        actions.add(projection.action)


validate_account_lifecycle_projection_catalog()
