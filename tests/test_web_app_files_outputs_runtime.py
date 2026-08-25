from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from services.identity import AuthorizationEngine, IdentityError, IdentityKind, Principal
from services.web_app_auth_contract import (
    WebAppActionPermissionContract,
    WebAppAuthContract,
    WebAppPermissionRequirement,
    WebAppRolePermissionContract,
    compile_authorization_rules,
)
from services.web_app_files_outputs_runtime import (
    WebAppFilesOutputsError,
    WebAppFilesOutputsRuntime,
)
from src.core.audit_engine import AuditEngine

NOW = datetime(2026, 8, 25, 15, 30, tzinfo=timezone.utc)


class MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, *, object_key: str, content: bytes) -> None:
        self.objects[object_key] = content

    def get(self, *, object_key: str) -> bytes:
        return self.objects[object_key]

    def delete(self, *, object_key: str) -> None:
        self.objects.pop(object_key, None)


def _contract() -> WebAppAuthContract:
    permissions = tuple(
        WebAppPermissionRequirement(
            permission=f"resource.output.{operation}",
            scope="resource",
            resource_type="output",
            privileged=operation == "delete",
        )
        for operation in ("read", "create", "delete")
    )
    names = tuple(item.permission for item in permissions)
    return WebAppAuthContract(
        schema_version="ilaios.web-app-auth-contract.v1",
        app_id="app-1",
        project_id="project-1",
        spec_sha256="a" * 64,
        identity_chain=("User", "Tenant", "Project", "Role", "Permission", "ResourceScope"),
        roles=(WebAppRolePermissionContract(role="Owner", permissions=names),),
        permissions=permissions,
        routes=(),
        actions=tuple(
            WebAppActionPermissionContract(action_id=f"action:{name}", permission=name)
            for name in names
        ),
        authentication_required=True,
        default_deny=True,
        server_authoritative=True,
        ui_visibility_is_authorization=False,
        authentication_authority="services.identity.AuthenticationBoundary",
        authorization_authority="services.identity.AuthorizationEngine",
        session_authority="services.identity.SessionRegistry",
    )


def _principal(*, tenant_id: str = "tenant-1", roles: frozenset[str] | None = None) -> Principal:
    return Principal(
        principal_id="user-1",
        tenant_id=tenant_id,
        kind=IdentityKind.HUMAN,
        roles=roles if roles is not None else frozenset({"Owner"}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )


def _runtime() -> tuple[WebAppFilesOutputsRuntime, MemoryStorage]:
    contract = _contract()
    storage = MemoryStorage()
    runtime = WebAppFilesOutputsRuntime(
        sqlite3.connect(":memory:"),
        contract,
        AuthorizationEngine(compile_authorization_rules(contract)),
        AuditEngine(),
        storage,
    )
    return runtime, storage


def test_store_download_and_versioning_bind_exact_hash() -> None:
    runtime, _storage = _runtime()
    principal = _principal()

    first = runtime.store(
        principal=principal,
        output_id="report-1",
        filename="report.txt",
        mime_type="text/plain",
        content=b"first",
        now=NOW,
    )
    second = runtime.store(
        principal=principal,
        output_id="report-1",
        filename="report.txt",
        mime_type="text/plain",
        content=b"second",
        now=NOW + timedelta(seconds=1),
    )

    assert first.version == 1
    assert second.version == 2
    assert first.sha256 != second.sha256
    record, content = runtime.download(
        principal=principal, output_id="report-1", version=2, now=NOW
    )
    assert record.sha256 == second.sha256
    assert content == b"second"
    assert tuple(item.version for item in runtime.list_versions(
        principal=principal, output_id="report-1", now=NOW
    )) == (2, 1)


def test_cross_tenant_download_fails_closed() -> None:
    runtime, _storage = _runtime()
    runtime.store(
        principal=_principal(),
        output_id="report-1",
        filename="report.pdf",
        mime_type="application/pdf",
        content=b"pdf",
        now=NOW,
    )

    with pytest.raises(WebAppFilesOutputsError) as exc:
        runtime.download(
            principal=_principal(tenant_id="tenant-2"),
            output_id="report-1",
            version=1,
            now=NOW,
        )
    assert exc.value.code == "NOT_FOUND"


def test_default_deny_role_cannot_download() -> None:
    runtime, _storage = _runtime()
    owner = _principal()
    runtime.store(
        principal=owner,
        output_id="report-1",
        filename="report.json",
        mime_type="application/json",
        content=b"{}",
        now=NOW,
    )

    with pytest.raises(IdentityError, match="deny by default"):
        runtime.download(
            principal=_principal(roles=frozenset({"Viewer"})),
            output_id="report-1",
            version=1,
            now=NOW,
        )


def test_mime_filename_and_storage_integrity_fail_closed() -> None:
    runtime, storage = _runtime()
    principal = _principal()

    with pytest.raises(WebAppFilesOutputsError, match="MIME"):
        runtime.store(
            principal=principal,
            output_id="bad-mime",
            filename="payload.html",
            mime_type="text/html",
            content=b"<script>x</script>",
            now=NOW,
        )

    with pytest.raises(WebAppFilesOutputsError) as traversal:
        runtime.store(
            principal=principal,
            output_id="bad-name",
            filename="../secret.txt",
            mime_type="text/plain",
            content=b"x",
            now=NOW,
        )
    assert traversal.value.code == "INVALID_FILENAME"

    record = runtime.store(
        principal=principal,
        output_id="tamper",
        filename="safe.txt",
        mime_type="text/plain",
        content=b"trusted",
        now=NOW,
    )
    storage.objects[record.object_key] = b"tampered"
    with pytest.raises(WebAppFilesOutputsError) as integrity:
        runtime.download(principal=principal, output_id="tamper", version=1, now=NOW)
    assert integrity.value.code == "OUTPUT_INTEGRITY_FAILURE"


def test_retention_blocks_delete_until_expiry() -> None:
    runtime, storage = _runtime()
    principal = _principal()
    record = runtime.store(
        principal=principal,
        output_id="retained",
        filename="archive.zip",
        mime_type="application/zip",
        content=b"archive",
        now=NOW,
        retain_until=NOW + timedelta(hours=1),
    )

    with pytest.raises(WebAppFilesOutputsError) as retained:
        runtime.delete(principal=principal, output_id="retained", version=1, now=NOW)
    assert retained.value.code == "RETENTION_ACTIVE"
    assert record.object_key in storage.objects

    runtime.delete(
        principal=principal,
        output_id="retained",
        version=1,
        now=NOW + timedelta(hours=2),
    )
    assert record.object_key not in storage.objects
