from __future__ import annotations

import pytest

from services.account_lifecycle_projection import (
    AccountLifecycleProjectionError,
    account_lifecycle_projections,
    resolve_account_lifecycle_projection,
    validate_account_lifecycle_projection_catalog,
)


def test_projection_catalog_is_unique_and_server_authoritative() -> None:
    validate_account_lifecycle_projection_catalog()
    projections = account_lifecycle_projections()

    assert len(projections) == 8
    assert len({(item.path, item.method) for item in projections}) == len(projections)
    assert len({item.surface_id for item in projections}) == len(projections)
    assert all(item.server_authoritative is True for item in projections)
    assert all(item.ui_visibility_is_authorization is False for item in projections)
    assert all(item.service_authority.startswith("services.") for item in projections)


def test_destructive_surfaces_require_recent_auth_and_confirmation() -> None:
    account_delete = resolve_account_lifecycle_projection(
        path="/api/account/delete", method="DELETE"
    )
    tenant_delete = resolve_account_lifecycle_projection(
        path="/api/tenant/delete", method="DELETE"
    )
    privacy_delete = resolve_account_lifecycle_projection(
        path="/api/account/privacy-delete", method="DELETE"
    )

    for projection in (account_delete, tenant_delete, privacy_delete):
        assert projection.recent_auth_required is True
        assert projection.explicit_confirmation_required is True


def test_export_and_revoke_all_require_recent_auth_without_delete_confirmation() -> None:
    export = resolve_account_lifecycle_projection(
        path="/api/account/export", method="POST"
    )
    revoke_all = resolve_account_lifecycle_projection(
        path="/api/account/sessions/revoke-all", method="POST"
    )

    assert export.recent_auth_required is True
    assert export.explicit_confirmation_required is False
    assert revoke_all.recent_auth_required is True
    assert revoke_all.explicit_confirmation_required is False


def test_tenant_scoped_actions_remain_explicitly_tenant_bound() -> None:
    unlink = resolve_account_lifecycle_projection(
        path="/api/account/identities/unlink", method="POST"
    )
    logout = resolve_account_lifecycle_projection(
        path="/api/account/sessions/logout", method="POST"
    )
    revoke_all = resolve_account_lifecycle_projection(
        path="/api/account/sessions/revoke-all", method="POST"
    )
    tenant_delete = resolve_account_lifecycle_projection(
        path="/api/tenant/delete", method="DELETE"
    )

    assert all(
        item.tenant_scope_required is True
        for item in (unlink, logout, revoke_all, tenant_delete)
    )


def test_route_resolution_is_exact_and_fail_closed() -> None:
    resolved = resolve_account_lifecycle_projection(
        path="/api/account/export", method="post"
    )
    assert resolved.surface_id == "account.export_my_data"
    assert resolved.action == "identity.account.export"

    for path, method in (
        ("/api/account/export/extra", "POST"),
        ("/api/account/export", "GET"),
        ("/api/account/delete", "POST"),
        ("/api/unknown", "DELETE"),
    ):
        with pytest.raises(AccountLifecycleProjectionError):
            resolve_account_lifecycle_projection(path=path, method=method)


def test_projection_does_not_embed_credentials_or_identity_metadata() -> None:
    serialized = repr([item.to_dict() for item in account_lifecycle_projections()]).lower()

    for forbidden in (
        "password",
        "client_secret",
        "access_token",
        "refresh_token",
        "provider_subject",
        "email_address",
        "session_id",
    ):
        assert forbidden not in serialized
