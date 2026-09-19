"""Deterministic Phase-3 authentication/RBAC contracts for generated Web Apps.

This module does not create a second identity or authorization authority. It compiles
``WebAppSpec`` requirements into inspectable route/action permission contracts that are
consumable by the canonical ``services.identity`` AuthenticationBoundary,
AuthorizationEngine, and SessionRegistry. Runtime decisions remain owned by those
canonical authorities and fail closed when a route, action, tenant, project, role, or
permission is not explicitly represented here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal

from services.identity import (
    AccessRequest,
    AuthenticationBoundary,
    AuthorizationEngine,
    AuthorizationRule,
    IdentityError,
    IdentityKind,
    Principal,
    Session,
    SessionRegistry,
)
from services.web_app_spec import WebAppSpec


WebAppRole = Literal["Owner", "Admin", "Operator", "Reviewer", "Viewer"]
PermissionScope = Literal["tenant", "project", "resource"]

_CANONICAL_ROLES: tuple[WebAppRole, ...] = (
    "Owner",
    "Admin",
    "Operator",
    "Reviewer",
    "Viewer",
)
_SUPPORTED_METHODS = frozenset({"GET", "POST", "PATCH", "DELETE"})


class WebAppAuthContractError(ValueError):
    """A Web App auth/RBAC contract is ambiguous, incomplete, or unsafe."""


@dataclass(frozen=True, slots=True)
class WebAppPermissionRequirement:
    permission: str
    scope: PermissionScope
    resource_type: str | None = None
    privileged: bool = False
    high_risk: bool = False
    approval_required: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WebAppRolePermissionContract:
    role: WebAppRole
    permissions: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {"role": self.role, "permissions": list(self.permissions)}


@dataclass(frozen=True, slots=True)
class WebAppRoutePermissionContract:
    route_id: str
    path: str
    method: str
    permission: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WebAppActionPermissionContract:
    action_id: str
    permission: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WebAppAuthContract:
    schema_version: str
    app_id: str
    project_id: str
    spec_sha256: str
    identity_chain: tuple[str, ...]
    roles: tuple[WebAppRolePermissionContract, ...]
    permissions: tuple[WebAppPermissionRequirement, ...]
    routes: tuple[WebAppRoutePermissionContract, ...]
    actions: tuple[WebAppActionPermissionContract, ...]
    authentication_required: Literal[True]
    default_deny: Literal[True]
    server_authoritative: Literal[True]
    ui_visibility_is_authorization: Literal[False]
    authentication_authority: Literal["services.identity.AuthenticationBoundary"]
    authorization_authority: Literal["services.identity.AuthorizationEngine"]
    session_authority: Literal["services.identity.SessionRegistry"]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "app_id": self.app_id,
            "project_id": self.project_id,
            "spec_sha256": self.spec_sha256,
            "identity_chain": list(self.identity_chain),
            "roles": [role.to_dict() for role in self.roles],
            "permissions": [permission.to_dict() for permission in self.permissions],
            "routes": [route.to_dict() for route in self.routes],
            "actions": [action.to_dict() for action in self.actions],
            "authentication_required": self.authentication_required,
            "default_deny": self.default_deny,
            "server_authoritative": self.server_authoritative,
            "ui_visibility_is_authorization": self.ui_visibility_is_authorization,
            "authentication_authority": self.authentication_authority,
            "authorization_authority": self.authorization_authority,
            "session_authority": self.session_authority,
        }

    @property
    def contract_sha256(self) -> str:
        encoded = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def compile_web_app_auth_contract(
    spec: WebAppSpec,
    *,
    project_id: str,
) -> WebAppAuthContract:
    """Compile an explicit Web App permission matrix without granting authority."""
    _token(project_id, "project_id")
    if not spec.auth_required:
        raise WebAppAuthContractError(
            "Phase-3 auth/RBAC requires an explicitly authenticated WebAppSpec"
        )

    permissions = _permission_requirements(spec)
    permission_names = frozenset(item.permission for item in permissions)
    if len(permission_names) != len(permissions):
        raise WebAppAuthContractError("permission catalog contains duplicate authority")

    roles = _role_matrix(permissions)
    routes = _route_contracts(spec)
    actions = tuple(
        WebAppActionPermissionContract(
            action_id=f"action:{item.permission}", permission=item.permission
        )
        for item in permissions
    )
    _validate_contract_bindings(permission_names, routes, actions)

    return WebAppAuthContract(
        schema_version="ilaios.web-app-auth-contract.v1",
        app_id=spec.app_id,
        project_id=project_id,
        spec_sha256=spec.spec_sha256,
        identity_chain=(
            "User",
            "Tenant",
            "Project",
            "Role",
            "Permission",
            "ResourceScope",
        ),
        roles=roles,
        permissions=permissions,
        routes=routes,
        actions=actions,
        authentication_required=True,
        default_deny=True,
        server_authoritative=True,
        ui_visibility_is_authorization=False,
        authentication_authority="services.identity.AuthenticationBoundary",
        authorization_authority="services.identity.AuthorizationEngine",
        session_authority="services.identity.SessionRegistry",
    )


def compile_authorization_rules(
    contract: WebAppAuthContract,
) -> tuple[AuthorizationRule, ...]:
    """Translate the contract into rules consumed by the canonical engine."""
    role_permissions = {
        role.role: frozenset(role.permissions) for role in contract.roles
    }
    rules: list[AuthorizationRule] = []
    for requirement in contract.permissions:
        roles = frozenset(
            role for role, values in role_permissions.items() if requirement.permission in values
        )
        if not roles:
            raise WebAppAuthContractError(
                f"permission {requirement.permission} is unreachable from every role"
            )
        attributes = _scope_attributes(contract, requirement)
        identity_kinds = (
            frozenset({IdentityKind.HUMAN})
            if requirement.privileged or requirement.high_risk
            else frozenset({IdentityKind.HUMAN, IdentityKind.SERVICE})
        )
        rules.append(
            AuthorizationRule(
                action=requirement.permission,
                roles=roles,
                resource_attributes=attributes,
                identity_kinds=identity_kinds,
            )
        )
    return tuple(rules)


def route_access_request(
    contract: WebAppAuthContract,
    *,
    path: str,
    method: str,
    tenant_id: str,
    resource_tenant_id: str,
    approval_id: str | None = None,
) -> AccessRequest:
    """Resolve one declared route to a canonical AccessRequest or fail closed."""
    normalized_method = method.upper()
    matches = tuple(
        route
        for route in contract.routes
        if route.path == path and route.method == normalized_method
    )
    if len(matches) != 1:
        raise WebAppAuthContractError("route/method has no unique permission contract")
    return _access_request(
        contract,
        permission=matches[0].permission,
        tenant_id=tenant_id,
        resource_tenant_id=resource_tenant_id,
        approval_id=approval_id,
    )


def action_access_request(
    contract: WebAppAuthContract,
    *,
    action_id: str,
    tenant_id: str,
    resource_tenant_id: str,
    approval_id: str | None = None,
) -> AccessRequest:
    """Resolve one declared action to a canonical AccessRequest or fail closed."""
    matches = tuple(action for action in contract.actions if action.action_id == action_id)
    if len(matches) != 1:
        raise WebAppAuthContractError("action has no unique permission contract")
    return _access_request(
        contract,
        permission=matches[0].permission,
        tenant_id=tenant_id,
        resource_tenant_id=resource_tenant_id,
        approval_id=approval_id,
    )


def authenticate_with_canonical_boundary(
    boundary: AuthenticationBoundary,
    *,
    encoded_token: str,
    now: datetime,
) -> Principal:
    """Delegate authentication to the canonical boundary without alternate logic."""
    return boundary.authenticate(encoded_token, now)


def validate_bound_session(
    registry: SessionRegistry,
    *,
    session_id: str,
    principal: Principal,
    now: datetime,
) -> Session:
    """Delegate session validity to SessionRegistry and bind it to the principal."""
    session = registry.validate(session_id, principal.tenant_id, now)
    if session.principal_id != principal.principal_id:
        raise IdentityError("session principal does not match authenticated principal")
    return session


def authorize_with_canonical_engine(
    engine: AuthorizationEngine,
    *,
    principal: Principal,
    request: AccessRequest,
    now: datetime,
) -> None:
    """Delegate the final deterministic decision to AuthorizationEngine."""
    engine.authorize(principal, request, now)


def _permission_requirements(
    spec: WebAppSpec,
) -> tuple[WebAppPermissionRequirement, ...]:
    values: list[WebAppPermissionRequirement] = [
        WebAppPermissionRequirement("app.view", "project"),
        WebAppPermissionRequirement("project.manage", "project", privileged=True),
        WebAppPermissionRequirement(
            "project.delete",
            "project",
            privileged=True,
            high_risk=True,
            approval_required=True,
        ),
        WebAppPermissionRequirement("approval.review", "project", privileged=True),
        WebAppPermissionRequirement("evidence.review", "project"),
    ]
    for resource in spec.resources:
        for operation in resource.operations:
            values.append(
                WebAppPermissionRequirement(
                    permission=f"resource.{resource.name}.{operation}",
                    scope="resource",
                    resource_type=resource.name,
                    privileged=operation == "delete",
                )
            )
    if spec.charts_required:
        values.append(WebAppPermissionRequirement("analytics.view", "project"))
    if spec.realtime_required:
        values.append(WebAppPermissionRequirement("realtime.subscribe", "project"))
    if spec.external_api_required:
        values.append(
            WebAppPermissionRequirement("integration.use", "project", privileged=True)
        )
    return tuple(values)


def _role_matrix(
    permissions: tuple[WebAppPermissionRequirement, ...],
) -> tuple[WebAppRolePermissionContract, ...]:
    names = tuple(item.permission for item in permissions)
    read_permissions = tuple(
        item.permission
        for item in permissions
        if item.permission == "app.view"
        or item.permission == "analytics.view"
        or item.permission.endswith(".read")
    )
    operator_permissions = tuple(
        item.permission
        for item in permissions
        if item.permission in {"app.view", "analytics.view", "realtime.subscribe"}
        or item.permission.endswith((".read", ".create", ".update"))
    )
    reviewer_permissions = tuple(
        dict.fromkeys((*read_permissions, "approval.review", "evidence.review"))
    )
    admin_permissions = tuple(
        item.permission for item in permissions if item.permission != "project.delete"
    )
    matrix: dict[WebAppRole, tuple[str, ...]] = {
        "Owner": names,
        "Admin": admin_permissions,
        "Operator": operator_permissions,
        "Reviewer": reviewer_permissions,
        "Viewer": read_permissions,
    }
    return tuple(
        WebAppRolePermissionContract(role=role, permissions=matrix[role])
        for role in _CANONICAL_ROLES
    )


def _route_contracts(spec: WebAppSpec) -> tuple[WebAppRoutePermissionContract, ...]:
    values = [
        WebAppRoutePermissionContract(
            route_id="route:home:get", path="/", method="GET", permission="app.view"
        )
    ]
    method_by_operation = {
        "read": "GET",
        "create": "POST",
        "update": "PATCH",
        "delete": "DELETE",
    }
    for resource in spec.resources:
        path = f"/resources/{resource.name}"
        for operation in resource.operations:
            method = method_by_operation[operation]
            values.append(
                WebAppRoutePermissionContract(
                    route_id=f"route:{resource.name}:{operation}",
                    path=path,
                    method=method,
                    permission=f"resource.{resource.name}.{operation}",
                )
            )
    if spec.charts_required:
        values.append(
            WebAppRoutePermissionContract(
                route_id="route:analytics:get",
                path="/analytics",
                method="GET",
                permission="analytics.view",
            )
        )
    return tuple(values)


def _validate_contract_bindings(
    permission_names: frozenset[str],
    routes: tuple[WebAppRoutePermissionContract, ...],
    actions: tuple[WebAppActionPermissionContract, ...],
) -> None:
    route_keys: set[tuple[str, str]] = set()
    route_ids: set[str] = set()
    for route in routes:
        if route.method not in _SUPPORTED_METHODS:
            raise WebAppAuthContractError("route uses unsupported HTTP method")
        if route.permission not in permission_names:
            raise WebAppAuthContractError("route references unknown permission")
        key = (route.path, route.method)
        if key in route_keys or route.route_id in route_ids:
            raise WebAppAuthContractError("route permission contract is ambiguous")
        route_keys.add(key)
        route_ids.add(route.route_id)
    action_ids: set[str] = set()
    for action in actions:
        if action.permission not in permission_names:
            raise WebAppAuthContractError("action references unknown permission")
        if action.action_id in action_ids:
            raise WebAppAuthContractError("action permission contract is ambiguous")
        action_ids.add(action.action_id)


def _access_request(
    contract: WebAppAuthContract,
    *,
    permission: str,
    tenant_id: str,
    resource_tenant_id: str,
    approval_id: str | None,
) -> AccessRequest:
    requirement = _requirement(contract, permission)
    return AccessRequest(
        tenant_id=tenant_id,
        resource_tenant_id=resource_tenant_id,
        action=requirement.permission,
        resource_attributes=_scope_attributes(contract, requirement),
        privileged=requirement.privileged,
        high_risk=requirement.high_risk,
        approval_id=approval_id,
    )


def _requirement(
    contract: WebAppAuthContract, permission: str
) -> WebAppPermissionRequirement:
    matches = tuple(item for item in contract.permissions if item.permission == permission)
    if len(matches) != 1:
        raise WebAppAuthContractError("permission is missing or ambiguous")
    return matches[0]


def _scope_attributes(
    contract: WebAppAuthContract,
    requirement: WebAppPermissionRequirement,
) -> frozenset[tuple[str, str]]:
    values: set[tuple[str, str]] = set()
    if requirement.scope in {"project", "resource"}:
        values.add(("project_id", contract.project_id))
    if requirement.scope == "resource":
        if requirement.resource_type is None:
            raise WebAppAuthContractError("resource permission requires resource type")
        values.add(("resource_type", requirement.resource_type))
    return frozenset(values)


def _token(value: str, field: str) -> None:
    if (
        not value
        or value != value.strip()
        or len(value) > 160
        or any(character.isspace() for character in value)
        or "*" in value
    ):
        raise WebAppAuthContractError(f"{field} must be a bounded non-wildcard token")
