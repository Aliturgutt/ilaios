"""Regression coverage for Phase-3 Web App auth/RBAC permission contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.identity import (
    ApprovalRecord,
    AuthenticationBoundary,
    AuthorizationEngine,
    IdentityError,
    IdentityKind,
    IdentityPolicy,
    Principal,
    SessionRegistry,
    VerifiedOIDCClaims,
)
from services.web_app_auth_contract import (
    WebAppAuthContractError,
    action_access_request,
    authenticate_with_canonical_boundary,
    authorize_with_canonical_engine,
    compile_authorization_rules,
    compile_web_app_auth_contract,
    route_access_request,
    validate_bound_session,
)
from services.web_app_spec import WebAppResourceSpec, WebAppSpec


NOW = datetime(2026, 8, 21, 6, 0, tzinfo=timezone.utc)


def _spec(*, auth_required: bool = True) -> WebAppSpec:
    return WebAppSpec(
        app_id="webapp-phase3",
        app_kind="dashboard",
        objective_sha256="a" * 64,
        locales=("en", "tr"),
        auth_required=auth_required,
        resources=(
            WebAppResourceSpec(
                name="projects", operations=("create", "read", "update", "delete")
            ),
            WebAppResourceSpec(name="documents", operations=("read",)),
        ),
        tables_required=True,
        charts_required=True,
        external_api_required=True,
        realtime_required=True,
        booking_required=False,
        commerce_required=False,
        cms_required=False,
        reference_semantic_sha256=None,
        reference_design_constraints=(),
        acceptance_requirements=(),
    )


def _principal(
    role: str,
    *,
    principal_id: str = "user-1",
    tenant_id: str = "tenant-1",
    mfa: bool = False,
    kind: IdentityKind = IdentityKind.HUMAN,
) -> Principal:
    return Principal(
        principal_id=principal_id,
        tenant_id=tenant_id,
        kind=kind,
        roles=frozenset({role}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}) if mfa else frozenset(),
    )


def test_contract_has_required_identity_chain_roles_and_canonical_authorities() -> None:
    contract = compile_web_app_auth_contract(_spec(), project_id="project-1")

    assert contract.identity_chain == (
        "User",
        "Tenant",
        "Project",
        "Role",
        "Permission",
        "ResourceScope",
    )
    assert tuple(role.role for role in contract.roles) == (
        "Owner",
        "Admin",
        "Operator",
        "Reviewer",
        "Viewer",
    )
    assert contract.default_deny is True
    assert contract.server_authoritative is True
    assert contract.ui_visibility_is_authorization is False
    assert contract.authentication_authority == "services.identity.AuthenticationBoundary"
    assert contract.authorization_authority == "services.identity.AuthorizationEngine"
    assert contract.session_authority == "services.identity.SessionRegistry"


def test_contract_is_deterministic_and_rejects_non_authenticated_specs() -> None:
    first = compile_web_app_auth_contract(_spec(), project_id="project-1")
    second = compile_web_app_auth_contract(_spec(), project_id="project-1")
    assert first == second
    assert first.contract_sha256 == second.contract_sha256

    with pytest.raises(WebAppAuthContractError, match="explicitly authenticated"):
        compile_web_app_auth_contract(_spec(auth_required=False), project_id="project-1")


def test_every_declared_resource_route_and_action_has_one_permission_contract() -> None:
    contract = compile_web_app_auth_contract(_spec(), project_id="project-1")
    permission_names = {item.permission for item in contract.permissions}

    route_keys = {(route.path, route.method) for route in contract.routes}
    assert ("/", "GET") in route_keys
    assert ("/resources/projects", "GET") in route_keys
    assert ("/resources/projects", "POST") in route_keys
    assert ("/resources/projects", "PATCH") in route_keys
    assert ("/resources/projects", "DELETE") in route_keys
    assert ("/resources/documents", "GET") in route_keys
    assert ("/analytics", "GET") in route_keys
    assert all(route.permission in permission_names for route in contract.routes)
    assert {action.permission for action in contract.actions} == permission_names
    assert all("*" not in permission for permission in permission_names)


def test_canonical_authorization_engine_enforces_role_and_project_resource_scope() -> None:
    contract = compile_web_app_auth_contract(_spec(), project_id="project-1")
    engine = AuthorizationEngine(compile_authorization_rules(contract))

    operator = _principal("Operator")
    update_request = route_access_request(
        contract,
        path="/resources/projects",
        method="PATCH",
        tenant_id="tenant-1",
        resource_tenant_id="tenant-1",
    )
    authorize_with_canonical_engine(
        engine, principal=operator, request=update_request, now=NOW
    )
    assert ("project_id", "project-1") in update_request.resource_attributes
    assert ("resource_type", "projects") in update_request.resource_attributes

    viewer = _principal("Viewer")
    with pytest.raises(IdentityError, match="deny by default"):
        authorize_with_canonical_engine(
            engine, principal=viewer, request=update_request, now=NOW
        )

    cross_tenant = route_access_request(
        contract,
        path="/resources/projects",
        method="GET",
        tenant_id="tenant-1",
        resource_tenant_id="tenant-2",
    )
    with pytest.raises(IdentityError, match="cross-tenant"):
        authorize_with_canonical_engine(
            engine, principal=operator, request=cross_tenant, now=NOW
        )


def test_unknown_route_and_action_fail_closed() -> None:
    contract = compile_web_app_auth_contract(_spec(), project_id="project-1")

    with pytest.raises(WebAppAuthContractError, match="route/method"):
        route_access_request(
            contract,
            path="/not-declared",
            method="GET",
            tenant_id="tenant-1",
            resource_tenant_id="tenant-1",
        )
    with pytest.raises(WebAppAuthContractError, match="action"):
        action_access_request(
            contract,
            action_id="action:not-declared",
            tenant_id="tenant-1",
            resource_tenant_id="tenant-1",
        )


def test_high_risk_owner_action_requires_mfa_and_independent_approval() -> None:
    contract = compile_web_app_auth_contract(_spec(), project_id="project-1")
    approval = ApprovalRecord(
        approval_id="approval-1",
        tenant_id="tenant-1",
        action="project.delete",
        requester_id="user-1",
        approver_id="reviewer-2",
        expires_at=NOW + timedelta(minutes=10),
    )
    engine = AuthorizationEngine(
        compile_authorization_rules(contract), approvals=(approval,)
    )
    request = action_access_request(
        contract,
        action_id="action:project.delete",
        tenant_id="tenant-1",
        resource_tenant_id="tenant-1",
        approval_id="approval-1",
    )
    assert request.privileged is True
    assert request.high_risk is True

    with pytest.raises(IdentityError, match="requires MFA"):
        authorize_with_canonical_engine(
            engine, principal=_principal("Owner"), request=request, now=NOW
        )

    authorize_with_canonical_engine(
        engine, principal=_principal("Owner", mfa=True), request=request, now=NOW
    )

    service_owner = _principal("Owner", mfa=True, kind=IdentityKind.SERVICE)
    with pytest.raises(IdentityError):
        authorize_with_canonical_engine(
            engine, principal=service_owner, request=request, now=NOW
        )


class _Verifier:
    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        assert encoded_token == "token"
        return VerifiedOIDCClaims(
            issuer="https://issuer.example",
            audience="ilaios-web",
            subject="user-1",
            tenant_id="tenant-1",
            expires_at=NOW + timedelta(minutes=30),
            issued_at=NOW - timedelta(minutes=1),
            kind=IdentityKind.HUMAN,
            roles=frozenset({"Operator"}),
            authentication_methods=frozenset({"mfa"}),
        )


def test_authentication_and_session_helpers_delegate_to_canonical_authorities() -> None:
    boundary = AuthenticationBoundary(
        _Verifier(),
        IdentityPolicy(
            trusted_issuers=frozenset({"https://issuer.example"}),
            audience="ilaios-web",
            maximum_session=timedelta(hours=1),
        ),
    )
    principal = authenticate_with_canonical_boundary(
        boundary, encoded_token="token", now=NOW
    )
    assert principal.principal_id == "user-1"
    assert principal.tenant_id == "tenant-1"

    registry = SessionRegistry(maximum_lifetime=timedelta(hours=1))
    registry.issue("session-1", principal, NOW, timedelta(minutes=20))
    session = validate_bound_session(
        registry, session_id="session-1", principal=principal, now=NOW
    )
    assert session.principal_id == principal.principal_id

    other_principal = _principal("Operator", principal_id="user-2")
    with pytest.raises(IdentityError, match="does not match"):
        validate_bound_session(
            registry, session_id="session-1", principal=other_principal, now=NOW
        )
