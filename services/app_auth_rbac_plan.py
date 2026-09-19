"""Deterministic Stage-2 enterprise application authentication/RBAC contracts.

This module is specification/planning only. It does not authenticate users, issue
sessions, evaluate runtime permissions, access credentials, mutate source, deploy,
sign, submit, publish, or create a second identity/authorization authority. Runtime
identity remains owned by ``services.identity`` and implementation remains downstream
through the canonical Software Factory and governance/evidence boundaries.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal, TypeVar

from services.app_architecture_plan import ApplicationArchitecturePlan
from services.app_data_migration_plan import DataMigrationPlan
from services.app_product_spec import ProductSpec


AuthProvider = Literal["oidc", "password", "google", "apple", "microsoft", "github"]
ResourceScope = Literal["tenant", "project", "resource"]
_T = TypeVar("_T", bound=str)


class AppAuthRbacPlanError(ValueError):
    """Authentication/RBAC planning input is invalid, ambiguous, or unsafe."""


@dataclass(frozen=True, slots=True)
class PermissionGrant:
    permission: str
    scope: ResourceScope
    resource: str | None = None
    privileged: bool = False
    high_risk: bool = False
    approval_required: bool = False


@dataclass(frozen=True, slots=True)
class RoleRequirement:
    role_id: str
    grants: tuple[PermissionGrant, ...]


@dataclass(frozen=True, slots=True)
class ActorRoleBinding:
    actor: str
    role_id: str


@dataclass(frozen=True, slots=True)
class AuthRbacPlan:
    project_id: str
    spec_sha256: str
    architecture_plan_sha256: str
    data_migration_plan_sha256: str
    auth_providers: tuple[AuthProvider, ...]
    roles: tuple[RoleRequirement, ...]
    actor_role_bindings: tuple[ActorRoleBinding, ...]
    authentication_required: bool
    authorization_required: bool
    session_required: bool
    refresh_required: bool
    logout_required: bool
    recovery_required: bool
    privileged_mfa_required: bool
    high_risk_approval_required: bool
    default_deny: Literal[True]
    server_authoritative: Literal[True]
    ui_visibility_is_authorization: Literal[False]
    raw_credentials_allowed_in_plan: Literal[False]
    authentication_authority: Literal["services.identity.AuthenticationBoundary"]
    authorization_authority: Literal["services.identity.AuthorizationEngine"]
    session_authority: Literal["services.identity.SessionRegistry"]
    implementation_authority: Literal["software-factory"]
    direct_permission_mutation_allowed: Literal[False]
    plan_sha256: str


def build_auth_rbac_plan(
    *,
    spec: ProductSpec,
    architecture: ApplicationArchitecturePlan,
    data_migration: DataMigrationPlan,
    auth_providers: tuple[AuthProvider, ...],
    roles: tuple[RoleRequirement, ...] = (),
    actor_role_bindings: tuple[ActorRoleBinding, ...] = (),
) -> AuthRbacPlan:
    """Validate an immutable auth/RBAC plan without granting runtime authority."""
    if architecture.project_id != spec.project_id or architecture.spec_sha256 != spec.spec_sha256:
        raise AppAuthRbacPlanError("architecture plan must be bound to the supplied ProductSpec")
    if (
        data_migration.project_id != spec.project_id
        or data_migration.spec_sha256 != spec.spec_sha256
        or data_migration.architecture_plan_sha256 != architecture.plan_sha256
    ):
        raise AppAuthRbacPlanError(
            "data/migration plan must be bound to the supplied ProductSpec and architecture"
        )

    providers = _unique(auth_providers, "auth_providers")
    if architecture.requires_authorization and not architecture.requires_authentication:
        raise AppAuthRbacPlanError("authorization requires authenticated principal identity")
    if architecture.requires_authentication and not providers:
        raise AppAuthRbacPlanError("authentication architecture requires at least one auth provider")
    if not architecture.requires_authentication and providers:
        raise AppAuthRbacPlanError("non-authentication architecture cannot declare auth providers")

    if architecture.requires_authorization:
        if not roles:
            raise AppAuthRbacPlanError("authorization architecture requires at least one role")
        if not actor_role_bindings:
            raise AppAuthRbacPlanError("authorization architecture requires actor-role bindings")
    elif roles or actor_role_bindings:
        raise AppAuthRbacPlanError("non-authorization architecture cannot declare roles or bindings")

    role_ids = tuple(role.role_id for role in roles)
    _unique(role_ids, "role_id")
    known_roles = frozenset(role_ids)
    has_privileged = False
    has_high_risk = False
    for role in roles:
        _token(role.role_id, "role_id")
        if not role.grants:
            raise AppAuthRbacPlanError(f"role {role.role_id} requires at least one permission grant")
        grant_keys: list[str] = []
        for grant in role.grants:
            _validate_grant(grant)
            grant_keys.append(f"{grant.permission}|{grant.scope}|{grant.resource or ''}")
            has_privileged = has_privileged or grant.privileged
            has_high_risk = has_high_risk or grant.high_risk
        _unique(tuple(grant_keys), f"{role.role_id}.grants")

    if actor_role_bindings:
        binding_keys: list[str] = []
        bound_actors: set[str] = set()
        known_actors = frozenset(spec.actors)
        for binding in actor_role_bindings:
            _token(binding.actor, "binding.actor")
            _token(binding.role_id, "binding.role_id")
            if binding.actor not in known_actors:
                raise AppAuthRbacPlanError("actor-role binding references unknown ProductSpec actor")
            if binding.role_id not in known_roles:
                raise AppAuthRbacPlanError("actor-role binding references unknown role")
            binding_keys.append(f"{binding.actor}|{binding.role_id}")
            bound_actors.add(binding.actor)
        _unique(tuple(binding_keys), "actor_role_bindings")
        if bound_actors != set(spec.actors):
            raise AppAuthRbacPlanError("every ProductSpec actor requires at least one role binding")

    authentication_required = architecture.requires_authentication
    authorization_required = architecture.requires_authorization
    canonical: dict[str, object] = {
        "actor_role_bindings": [
            {"actor": item.actor, "role_id": item.role_id} for item in actor_role_bindings
        ],
        "architecture_plan_sha256": architecture.plan_sha256,
        "auth_providers": list(providers),
        "authentication_authority": "services.identity.AuthenticationBoundary",
        "authentication_required": authentication_required,
        "authorization_authority": "services.identity.AuthorizationEngine",
        "authorization_required": authorization_required,
        "data_migration_plan_sha256": data_migration.plan_sha256,
        "default_deny": True,
        "direct_permission_mutation_allowed": False,
        "high_risk_approval_required": has_high_risk,
        "implementation_authority": "software-factory",
        "logout_required": authentication_required,
        "privileged_mfa_required": has_privileged,
        "project_id": spec.project_id,
        "raw_credentials_allowed_in_plan": False,
        "recovery_required": authentication_required,
        "refresh_required": authentication_required,
        "roles": [_role_payload(role) for role in roles],
        "server_authoritative": True,
        "session_authority": "services.identity.SessionRegistry",
        "session_required": authentication_required,
        "spec_sha256": spec.spec_sha256,
        "ui_visibility_is_authorization": False,
    }
    return AuthRbacPlan(
        project_id=spec.project_id,
        spec_sha256=spec.spec_sha256,
        architecture_plan_sha256=architecture.plan_sha256,
        data_migration_plan_sha256=data_migration.plan_sha256,
        auth_providers=providers,
        roles=roles,
        actor_role_bindings=actor_role_bindings,
        authentication_required=authentication_required,
        authorization_required=authorization_required,
        session_required=authentication_required,
        refresh_required=authentication_required,
        logout_required=authentication_required,
        recovery_required=authentication_required,
        privileged_mfa_required=has_privileged,
        high_risk_approval_required=has_high_risk,
        default_deny=True,
        server_authoritative=True,
        ui_visibility_is_authorization=False,
        raw_credentials_allowed_in_plan=False,
        authentication_authority="services.identity.AuthenticationBoundary",
        authorization_authority="services.identity.AuthorizationEngine",
        session_authority="services.identity.SessionRegistry",
        implementation_authority="software-factory",
        direct_permission_mutation_allowed=False,
        plan_sha256=_sha256_json(canonical),
    )


def _validate_grant(grant: PermissionGrant) -> None:
    _token(grant.permission, "permission")
    if grant.scope == "resource":
        if grant.resource is None:
            raise AppAuthRbacPlanError("resource-scoped permission requires a resource type")
        _token(grant.resource, "resource")
    elif grant.resource is not None:
        raise AppAuthRbacPlanError("tenant/project-scoped permission cannot declare resource type")
    if grant.high_risk and not grant.approval_required:
        raise AppAuthRbacPlanError("high-risk permission requires explicit approval")


def _role_payload(role: RoleRequirement) -> dict[str, object]:
    return {
        "grants": [
            {
                "approval_required": grant.approval_required,
                "high_risk": grant.high_risk,
                "permission": grant.permission,
                "privileged": grant.privileged,
                "resource": grant.resource,
                "scope": grant.scope,
            }
            for grant in role.grants
        ],
        "role_id": role.role_id,
    }


def _unique(values: tuple[_T, ...], field: str) -> tuple[_T, ...]:
    for value in values:
        _token(value, field)
    if len(values) != len(set(values)):
        raise AppAuthRbacPlanError(f"{field} values must be unique")
    return values


def _token(value: str, field: str) -> None:
    if not value or value != value.strip() or any(ch.isspace() for ch in value):
        raise AppAuthRbacPlanError(f"{field} must be a non-empty token")
    if "*" in value:
        raise AppAuthRbacPlanError(f"{field} cannot contain wildcard authority")


def _sha256_json(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
