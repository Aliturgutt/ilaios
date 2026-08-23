from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from services.identity import AuthorizationEngine, IdentityError, IdentityKind, Principal
from services.web_app_auth_contract import (
    WebAppActionPermissionContract,
    WebAppAuthContract,
    WebAppPermissionRequirement,
    WebAppRolePermissionContract,
    compile_authorization_rules,
)
from services.web_app_crud_runtime import WebAppCrudRuntime
from services.web_app_realtime_runtime import (
    WebAppRealtimeRuntime,
    WebAppRealtimeRuntimeError,
)
from src.core.audit_engine import AuditEngine

NOW = datetime(2026, 8, 21, 22, 55, tzinfo=timezone.utc)


def _contract() -> WebAppAuthContract:
    permission = WebAppPermissionRequirement(
        permission="resource.Goal.read",
        scope="resource",
        resource_type="Goal",
        privileged=False,
    )
    return WebAppAuthContract(
        schema_version="ilaios.web-app-auth-contract.v1",
        app_id="app-realtime",
        project_id="project-1",
        spec_sha256="c" * 64,
        identity_chain=("User", "Tenant", "Project", "Role", "Permission", "ResourceScope"),
        roles=(WebAppRolePermissionContract(role="Viewer", permissions=(permission.permission,)),),
        permissions=(permission,),
        routes=(),
        actions=(
            WebAppActionPermissionContract(
                action_id="action:resource.Goal.read", permission=permission.permission
            ),
        ),
        authentication_required=True,
        default_deny=True,
        server_authoritative=True,
        ui_visibility_is_authorization=False,
        authentication_authority="services.identity.AuthenticationBoundary",
        authorization_authority="services.identity.AuthorizationEngine",
        session_authority="services.identity.SessionRegistry",
    )


def _principal(*, tenant_id: str = "tenant-1", role: str = "Viewer") -> Principal:
    return Principal(
        principal_id="user-1",
        tenant_id=tenant_id,
        kind=IdentityKind.HUMAN,
        roles=frozenset({role}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )


def _runtime(*, max_history: int = 1000, max_batch: int = 100) -> WebAppRealtimeRuntime:
    contract = _contract()
    authorization = AuthorizationEngine(compile_authorization_rules(contract))
    connection = sqlite3.connect(":memory:")
    crud = WebAppCrudRuntime(connection, contract, authorization, AuditEngine())
    return WebAppRealtimeRuntime(crud, max_history=max_history, max_batch=max_batch)


def test_publish_and_reconnect_replay_use_monotonic_sequences() -> None:
    realtime = _runtime()
    first = realtime.publish(
        principal=_principal(),
        resource_type="Goal",
        resource_id="goal-1",
        event_type="created",
        payload={"status": "open"},
        now=NOW,
        resource_version=1,
    )
    second = realtime.publish(
        principal=_principal(),
        resource_type="Goal",
        resource_id="goal-1",
        event_type="updated",
        payload={"status": "done"},
        now=NOW,
        resource_version=2,
    )
    assert first.sequence == 1
    assert second.sequence == 2
    assert first.event_id != second.event_id

    batch = realtime.subscribe(
        principal=_principal(),
        resource_type="Goal",
        resource_id="goal-1",
        after_sequence=first.sequence,
        now=NOW,
    )
    assert batch.events == (second,)
    assert batch.latest_sequence == 2
    assert batch.has_more is False


def test_subscription_is_tenant_scoped() -> None:
    realtime = _runtime()
    realtime.publish(
        principal=_principal(tenant_id="tenant-1"),
        resource_type="Goal",
        resource_id="goal-1",
        event_type="state_changed",
        payload={"state": "Executing"},
        now=NOW,
    )
    batch = realtime.subscribe(
        principal=_principal(tenant_id="tenant-2"),
        resource_type="Goal",
        now=NOW,
    )
    assert batch.events == ()
    assert batch.latest_sequence == 0


def test_other_tenant_history_eviction_cannot_stale_or_advance_cursor() -> None:
    realtime = _runtime(max_history=2)
    for index in range(3):
        realtime.publish(
            principal=_principal(tenant_id="tenant-1"),
            resource_type="Goal",
            resource_id=f"goal-{index}",
            event_type="updated",
            payload={"index": index},
            now=NOW,
        )

    batch = realtime.subscribe(
        principal=_principal(tenant_id="tenant-2"),
        resource_type="Goal",
        after_sequence=0,
        now=NOW,
    )
    assert batch.events == ()
    assert batch.latest_sequence == 0
    assert batch.has_more is False


def test_default_deny_is_inherited_for_publish_and_subscribe() -> None:
    realtime = _runtime()
    with pytest.raises(IdentityError, match="deny by default"):
        realtime.publish(
            principal=_principal(role="Unknown"),
            resource_type="Goal",
            resource_id="goal-1",
            event_type="created",
            payload={},
            now=NOW,
        )
    with pytest.raises(IdentityError, match="deny by default"):
        realtime.subscribe(
            principal=_principal(role="Unknown"),
            resource_type="Goal",
            now=NOW,
        )


def test_stale_cursor_fails_closed_after_history_eviction() -> None:
    realtime = _runtime(max_history=2)
    for index in range(3):
        realtime.publish(
            principal=_principal(),
            resource_type="Goal",
            resource_id=f"goal-{index}",
            event_type="updated",
            payload={"index": index},
            now=NOW,
        )
    with pytest.raises(WebAppRealtimeRuntimeError) as exc:
        realtime.subscribe(
            principal=_principal(),
            resource_type="Goal",
            after_sequence=0,
            now=NOW,
        )
    assert exc.value.code == "STALE_CURSOR"
    assert exc.value.status_code == 409


def test_batch_limit_reports_more_without_dropping_reconnect_cursor_truth() -> None:
    realtime = _runtime(max_batch=2)
    for index in range(3):
        realtime.publish(
            principal=_principal(),
            resource_type="Goal",
            resource_id=f"goal-{index}",
            event_type="created",
            payload={"index": index},
            now=NOW,
        )
    batch = realtime.subscribe(
        principal=_principal(), resource_type="Goal", limit=2, now=NOW
    )
    assert [event.sequence for event in batch.events] == [1, 2]
    assert batch.latest_sequence == 3
    assert batch.has_more is True


def test_invalid_payload_cursor_and_resource_version_fail_closed() -> None:
    realtime = _runtime()
    with pytest.raises(WebAppRealtimeRuntimeError) as payload:
        realtime.publish(
            principal=_principal(),
            resource_type="Goal",
            resource_id="goal-1",
            event_type="created",
            payload={"bad": object()},
            now=NOW,
        )
    assert payload.value.code == "INVALID_PAYLOAD"

    with pytest.raises(WebAppRealtimeRuntimeError) as version:
        realtime.publish(
            principal=_principal(),
            resource_type="Goal",
            resource_id="goal-1",
            event_type="created",
            payload={},
            now=NOW,
            resource_version=0,
        )
    assert version.value.code == "INVALID_RESOURCE_VERSION"

    with pytest.raises(WebAppRealtimeRuntimeError) as cursor:
        realtime.subscribe(
            principal=_principal(), resource_type="Goal", after_sequence=-1, now=NOW
        )
    assert cursor.value.code == "INVALID_CURSOR"
