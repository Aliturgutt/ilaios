from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier, Lock

from services.identity import AuthorizationEngine, IdentityKind, Principal
from services.web_app_auth_contract import (
    WebAppActionPermissionContract,
    WebAppAuthContract,
    WebAppPermissionRequirement,
    WebAppRolePermissionContract,
    compile_authorization_rules,
)
from services.web_app_files_outputs_runtime import WebAppFilesOutputsRuntime
from src.core.audit_engine import AuditEngine

NOW = datetime(2026, 8, 25, 17, 30, tzinfo=timezone.utc)


class ConcurrentMemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self._lock = Lock()

    def put(self, *, object_key: str, content: bytes) -> None:
        with self._lock:
            self.objects[object_key] = content

    def get(self, *, object_key: str) -> bytes:
        with self._lock:
            return self.objects[object_key]

    def delete(self, *, object_key: str) -> None:
        with self._lock:
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


def _principal() -> Principal:
    return Principal(
        principal_id="user-1",
        tenant_id="tenant-1",
        kind=IdentityKind.HUMAN,
        roles=frozenset({"Owner"}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )


def _runtime(db_path: Path, storage: ConcurrentMemoryStorage) -> WebAppFilesOutputsRuntime:
    contract = _contract()
    return WebAppFilesOutputsRuntime(
        sqlite3.connect(db_path, timeout=10),
        contract,
        AuthorizationEngine(compile_authorization_rules(contract)),
        AuditEngine(),
        storage,
    )


def test_concurrent_stores_reserve_distinct_versions_and_object_keys(tmp_path: Path) -> None:
    db_path = tmp_path / "outputs.sqlite3"
    storage = ConcurrentMemoryStorage()

    # Initialize schema before the concurrent writers enter the allocator.
    seed = _runtime(db_path, storage)
    del seed

    barrier = Barrier(2)

    def write(content: bytes) -> tuple[int, str]:
        runtime = _runtime(db_path, storage)
        barrier.wait()
        record = runtime.store(
            principal=_principal(),
            output_id="concurrent-output",
            filename="report.txt",
            mime_type="text/plain",
            content=content,
            now=NOW,
        )
        return record.version, record.object_key

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(write, (b"first", b"second")))

    versions = {version for version, _object_key in results}
    object_keys = {object_key for _version, object_key in results}
    assert versions == {1, 2}
    assert len(object_keys) == 2
    assert object_keys == set(storage.objects)

    verifier = _runtime(db_path, storage)
    records = verifier.list_versions(
        principal=_principal(), output_id="concurrent-output", now=NOW
    )
    assert tuple(record.version for record in records) == (2, 1)
    assert all(record.object_key in storage.objects for record in records)
