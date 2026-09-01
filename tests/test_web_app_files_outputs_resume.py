from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.identity import AuthorizationEngine, IdentityKind, Principal
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
from src.core.audit_engine import AuditEngine, AuditRecord

NOW = datetime(2026, 8, 25, 19, 30, tzinfo=timezone.utc)


class MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.delete_calls = 0

    def put(self, *, object_key: str, content: bytes) -> None:
        self.objects[object_key] = content

    def get(self, *, object_key: str) -> bytes:
        return self.objects[object_key]

    def delete(self, *, object_key: str) -> None:
        self.delete_calls += 1
        self.objects.pop(object_key, None)


class FailDeleteAuditOnce(AuditEngine):
    def __init__(self) -> None:
        super().__init__()
        self.failed = False

    def record(
        self,
        component: str,
        action: str,
        status: str,
        details: Mapping[str, str] | None = None,
        *,
        timestamp: datetime | None = None,
    ) -> AuditRecord:
        if action == "delete" and not self.failed:
            self.failed = True
            raise RuntimeError("injected audit failure")
        return super().record(component, action, status, details, timestamp=timestamp)


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


def _principal() -> Principal:
    return Principal(
        principal_id="user-1",
        tenant_id="tenant-1",
        kind=IdentityKind.HUMAN,
        roles=frozenset({"Owner"}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )


def _runtime(
    *, audit: AuditEngine | None = None
) -> tuple[WebAppFilesOutputsRuntime, sqlite3.Connection, MemoryStorage, AuditEngine]:
    contract = _contract()
    connection = sqlite3.connect(":memory:")
    storage = MemoryStorage()
    selected_audit = audit or AuditEngine()
    runtime = WebAppFilesOutputsRuntime(
        connection,
        contract,
        AuthorizationEngine(compile_authorization_rules(contract)),
        selected_audit,
        storage,
    )
    return runtime, connection, storage, selected_audit


def _runtime_with_connection(
    connection: sqlite3.Connection,
    storage: MemoryStorage,
    audit: AuditEngine,
) -> WebAppFilesOutputsRuntime:
    contract = _contract()
    return WebAppFilesOutputsRuntime(
        connection,
        contract,
        AuthorizationEngine(compile_authorization_rules(contract)),
        audit,
        storage,
    )


def test_delete_restores_bytes_when_metadata_transaction_fails() -> None:
    runtime, connection, storage, _audit = _runtime()
    principal = _principal()
    record = runtime.store(
        principal=principal,
        output_id="compensate",
        filename="safe.txt",
        mime_type="text/plain",
        content=b"durable-bytes",
        now=NOW,
    )
    connection.execute(
        """CREATE TRIGGER fail_output_delete BEFORE DELETE ON web_app_outputs
           BEGIN SELECT RAISE(ABORT, 'injected delete failure'); END"""
    )
    connection.commit()

    with pytest.raises(sqlite3.IntegrityError, match="injected delete failure"):
        runtime.delete(principal=principal, output_id="compensate", version=1, now=NOW)

    assert storage.objects[record.object_key] == b"durable-bytes"
    restored, content = runtime.download(
        principal=principal, output_id="compensate", version=1, now=NOW
    )
    assert restored.sha256 == record.sha256
    assert content == b"durable-bytes"


def test_delete_retry_finishes_pending_audit_without_duplicate_storage_mutation() -> None:
    audit = FailDeleteAuditOnce()
    runtime, _connection, storage, _selected_audit = _runtime(audit=audit)
    principal = _principal()
    record = runtime.store(
        principal=principal,
        output_id="audit-retry",
        filename="safe.txt",
        mime_type="text/plain",
        content=b"delete-once",
        now=NOW,
    )

    with pytest.raises(WebAppFilesOutputsError) as pending:
        runtime.delete(principal=principal, output_id="audit-retry", version=1, now=NOW)
    assert pending.value.code == "AUDIT_PENDING"
    assert record.object_key not in storage.objects
    assert storage.delete_calls == 1

    runtime.delete(principal=principal, output_id="audit-retry", version=1, now=NOW)

    assert storage.delete_calls == 1
    delete_records = audit.get_records(
        component="web_app_files_outputs_runtime", action="delete", status="success"
    )
    assert len(delete_records) == 1
    assert delete_records[0].details["output_id"] == "audit-retry"
    assert "operation_id" in delete_records[0].details


def test_delete_retry_resumes_after_process_restart_without_second_storage_delete(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "web-app-files-outputs.sqlite3"
    storage = MemoryStorage()
    principal = _principal()

    first_connection = sqlite3.connect(database_path)
    first_audit = FailDeleteAuditOnce()
    first_runtime = _runtime_with_connection(first_connection, storage, first_audit)
    record = first_runtime.store(
        principal=principal,
        output_id="restart-audit-retry",
        filename="safe.txt",
        mime_type="text/plain",
        content=b"delete-once-across-restart",
        now=NOW,
    )

    with pytest.raises(WebAppFilesOutputsError) as pending:
        first_runtime.delete(
            principal=principal,
            output_id="restart-audit-retry",
            version=1,
            now=NOW,
        )
    assert pending.value.code == "AUDIT_PENDING"
    assert record.object_key not in storage.objects
    assert storage.delete_calls == 1
    first_connection.close()

    restarted_connection = sqlite3.connect(database_path)
    restarted_audit = AuditEngine()
    restarted_runtime = _runtime_with_connection(
        restarted_connection,
        storage,
        restarted_audit,
    )
    restarted_runtime.delete(
        principal=principal,
        output_id="restart-audit-retry",
        version=1,
        now=NOW,
    )

    assert storage.delete_calls == 1
    delete_records = restarted_audit.get_records(
        component="web_app_files_outputs_runtime", action="delete", status="success"
    )
    assert len(delete_records) == 1
    assert delete_records[0].details["output_id"] == "restart-audit-retry"
    assert "operation_id" in delete_records[0].details
    restarted_connection.close()
